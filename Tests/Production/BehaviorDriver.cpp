// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Controls and observation only: every force, contact, constraint, animation,
// autopilot and scenario operation below goes through the production SDK.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using SetObserver = int (*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver *driver = nullptr;
void observe(const char *, const char *, double, double, int);
OBJHANDLE vessel(const char *name) { return oapiGetVesselByName(const_cast<char *>(name)); }
std::string nameOf(OBJHANDLE h) {
    if (!h) return "";
    char name[256]{}; oapiGetObjectName(h, name, sizeof(name)); return name;
}
void require(bool condition, const char *message) {
    if (!condition) throw std::runtime_error(message);
}
class Driver final : public oapi::Module {
public:
    explicit Driver(HINSTANCE instance) : Module(instance) {
        std::ifstream config("behavior-case.txt");
        require(bool(config >> id >> totalFrames >> dt >> epoch), "invalid behavior-case.txt");
        require(totalFrames > 0 && dt > 0 && std::isfinite(dt) && std::isfinite(epoch), "invalid behavior timing");
        const std::vector<std::string> supported = {"rcs", "autopilot", "atmosphere", "landed", "contact",
            "docked", "dock_approach", "attachments", "clock", "lifetime", "dg_animations", "dg_persistence", "dg_reload", "callbacks"};
        require(std::find(supported.begin(),supported.end(),id) != supported.end(), "unsupported behavior case");
        open(events,"behavior-events.csv"); open(states,"behavior-state.csv");
        open(propellant,"behavior-propellant.csv"); open(animations,"behavior-animations.csv");
        events << "frame,tick,seconds,mjd,phase,object,detail\n";
        states << "tick,frame,seconds,mjd,object,class,rx,ry,rz,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,altitude_agl,altitude_mean,airspeed,density,dynamic_pressure,lift,drag,ground,dock,focus,navmask,attached\n";
        propellant << "tick,object,index,mass,capacity\n";
        animations << "tick,object,index,state\n";
        setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));
        require(setter && setter(1,observe,epoch), "production observation ABI v1 is required");
        std::srand(0);
    }
    ~Driver() override {
        if (setter) setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());
    }
    void clbkSimulationStart(RenderMode mode) override {
        guarded([&] {
            started = true;
            target = vessel(id.compare(0,3,"dg_") == 0 || id == "atmosphere" || id == "landed" || id == "contact" ? "DG" : "PB");
            require(target != nullptr,"required real stock vessel is missing");
            VESSEL *v = oapiGetVesselInterface(target);
            require(v->GetThrusterCount() > 0 && v->GetPropellantCount() > 0,"stock vessel module did not initialize");
            require(v->GetMeshCount() > 0,"stock vessel mesh did not initialize");
            if (id == "atmosphere" || id == "contact") {
                VESSELSTATUS2 status{};status.version=2;v->GetStatusEx(&status);
                VECTOR3 p{},ev{},ep{};oapiGetGlobalPos(status.rbody,&ep);v->GetGlobalPos(p);
                status.rpos=p-ep;
                const double radius=length(status.rpos);
                status.rpos*=1+(id == "atmosphere" ? 1500.0 : 8.0)/radius;
                MATRIX3 r{};v->GetRotationMatrix(r);
                // The landed VESSELSTATUS2 encodes a planet-local attitude and
                // altitude in vrot.x. Free flight requires global attitude and
                // actual angular velocity; use the production SDK conversion.
                v->GetGlobalOrientation(status.arot);v->GetAngularVel(status.vrot);
                if (id == "atmosphere") status.rvel+=mul(r,_V(0,0,200));
                else status.rvel-=status.rpos*(.5/length(status.rpos));
                status.status=0;status.flag=0;v->DefSetStateEx(&status);
                event("input.airborne",nameOf(target),id == "atmosphere" ? "1500:200" : "8:-0.5");
            }
            event("module.start",nameOf(target),std::to_string(int(mode)));
            snapshot();
        });
    }
    void clbkPreStep(double, double step, double) override {
        guarded([&] {
            require(started && std::isfinite(step) && step > 0,"invalid production step");
            event("module.pre","","");
            VESSEL *v = oapiGetVesselInterface(target);
            if (id == "rcs") {
                const THGROUP_TYPE groups[] = {THGROUP_ATT_PITCHUP,THGROUP_ATT_PITCHDOWN,THGROUP_ATT_YAWLEFT,
                    THGROUP_ATT_YAWRIGHT,THGROUP_ATT_BANKLEFT,THGROUP_ATT_BANKRIGHT,THGROUP_ATT_UP,THGROUP_ATT_DOWN,
                    THGROUP_ATT_LEFT,THGROUP_ATT_RIGHT,THGROUP_ATT_FORWARD,THGROUP_ATT_BACK};
                // Groups share physical thrusters. Clear them before applying
                // the selected group so a later zero cannot erase its command.
                for (auto group:groups) v->SetThrusterGroupLevel(group,0);
                if (tick/40 < 12 && tick%40 < 8) v->SetThrusterGroupLevel(groups[tick/40],.2);
                event("input.rcs",nameOf(target),std::to_string(tick/40)+":"+std::to_string(tick%40 < 8 ? .2 : 0));
            } else if (id == "autopilot") {
                const int modes[] = {NAVMODE_KILLROT,NAVMODE_PROGRADE,NAVMODE_RETROGRADE,NAVMODE_NORMAL,NAVMODE_ANTINORMAL};
                if (tick%80 == 0 && tick/80 < 5) {
                    for (int mode:modes) v->DeactivateNavmode(mode);
                    v->ActivateNavmode(modes[tick/80]);
                    event("input.navmode",nameOf(target),std::to_string(modes[tick/80]));
                }
            } else if (id == "atmosphere") {
                if (tick == 0) { v->ActivateNavmode(NAVMODE_HLEVEL); event("input.navmode",nameOf(target),"hlevel"); }
                v->SetThrusterGroupLevel(THGROUP_MAIN,.15);
            } else if (id == "lifetime") {
                if (tick == 10) createChild();
                if (tick == 11) { oapiSetFocusObject(child); event("input.focus","Child",""); }
                if (tick == 20) { oapiSetFocusObject(target); event("input.focus",nameOf(target),""); }
                if (tick == 30) { require(oapiDeleteVessel(child,target),"vessel deletion failed"); event("input.delete","Child",""); child=nullptr; }
            } else if (id == "attachments") {
                if (tick == 1) {
                    createChild();
                    parentAttachment=v->CreateAttachment(false,_V(0,0,5),_V(0,0,1),_V(0,1,0),"parent");
                    childAttachment=oapiGetVesselInterface(child)->CreateAttachment(true,_V(0,0,-5),_V(0,0,-1),_V(0,1,0),"child");
                    require(parentAttachment && childAttachment,"attachment creation failed");
                }
                if (tick == 10) { require(v->AttachChild(child,parentAttachment,childAttachment),"AttachChild failed"); event("input.attach",nameOf(target),"Child"); }
                if (tick == 30) { require(v->DetachChild(parentAttachment,.2),"DetachChild failed"); event("input.detach",nameOf(target),"Child"); }
            } else if (id == "docked") {
                if (tick == 10) { require(v->Undock(0),"stock undocking failed"); event("input.undock",nameOf(target),"0"); }
            } else if (id == "clock") {
                if (tick == 20) { oapiSetTimeAcceleration(10); event("input.warp","","10"); }
                if (tick == 40) { oapiSetTimeAcceleration(1); event("input.warp","","1"); }
            } else if (id == "dg_animations" || id == "dg_persistence") {
                if (tick == 10) key(v,OAPI_KEY_G);
                if (tick == 20) key(v,OAPI_KEY_K);
            }
        });
    }
    void clbkPostStep(double, double, double) override { guarded([&] { event("module.post","",""); }); }
    void clbkPause(bool pause) override { guarded([&] { event("module.pause","",pause ? "1" : "0"); }); }
    void clbkTimeAccChanged(double warp,double old) override { guarded([&] { event("module.warp","",number(old)+":"+number(warp)); }); }
    void clbkFocusChanged(OBJHANDLE now,OBJHANDLE old) override { guarded([&] { event("module.focus",nameOf(now),nameOf(old)); }); }
    void clbkNewVessel(OBJHANDLE h) override { guarded([&] { event("module.create",nameOf(h),""); }); }
    void clbkDeleteVessel(OBJHANDLE h) override { guarded([&] { event("module.delete",nameOf(h),""); }); }
    void clbkSimulationEnd() override {
        guarded([&] {
            event("module.end","","");
            require(frame == totalFrames,"incomplete production frame sequence");
            started=false; ended=true;
            states.close(); events.close(); propellant.close(); animations.close();
            require(!states.fail() && !events.fail() && !propellant.fail() && !animations.fail(),"behavior trace close failure");
        });
    }
    void core(const char *phase,const char *object,double simt,double mjd,int running) {
        guarded([&] {
            if (ended) return;
            events << frame << ',' << tick << ',' << simt << ',' << mjd << ',' << phase << ',' << object << ',' << running << '\n';
            if (started && std::string(phase) == "app.frame.end") {
                ++frame;
                if (running) { ++tick; snapshot(); }
                if (id == "dg_persistence" && running && tick == 40) {
                    // Save only after state finalization and EndStep, so the
                    // stock serializer's MJD1 and its state vectors agree.
                    require(oapiSaveScenario("BehaviorSnapshot","Windows production persistence checkpoint"),"save checkpoint failed");
                    event("input.save",nameOf(target),"BehaviorSnapshot");
                }
                if (id == "clock") {
                    if (running && tick == 60 && !pauseRequested) { pauseRequested=true; oapiSetPause(true); event("input.pause","","1"); }
                    if (!running && ++pausedFrames == 3) { oapiSetPause(false); event("input.pause","","0"); }
                }
                states.flush(); propellant.flush(); animations.flush(); events.flush();
            }
            require(bool(events) && bool(states) && bool(propellant) && bool(animations),"behavior trace write failure");
        });
    }
private:
    std::string id;
    unsigned totalFrames=0,frame=0,tick=0,pausedFrames=0;
    double dt=0,epoch=0;
    bool started=false,ended=false,pauseRequested=false;
    OBJHANDLE target=nullptr,child=nullptr;
    ATTACHMENTHANDLE parentAttachment=nullptr,childAttachment=nullptr;
    SetObserver setter=nullptr;
    std::ofstream events,states,propellant,animations;
    static void open(std::ofstream &file,const char *path) {
        file.open(path,std::ios::binary); file.imbue(std::locale::classic()); file << std::setprecision(17);
        require(bool(file),"cannot open behavior output");
    }
    static std::string number(double value) {
        std::ostringstream stream; stream.imbue(std::locale::classic());stream << std::setprecision(17) << value;return stream.str();
    }
    template<class F> void guarded(F f) {
        try { f(); } catch (const std::exception &error) { oapiWriteLog(const_cast<char *>(error.what())); std::exit(1); }
    }
    void event(const std::string &phase,const std::string &object,const std::string &detail) {
        events << frame << ',' << tick << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD() << ',' << phase << ',' << object << ',' << detail << '\n';
    }
    void key(VESSEL *v,DWORD code) {
        char keys[256]{};v->SendBufferedKey(code,true,keys);event("input.key",nameOf(target),std::to_string(code));
    }
    void createChild() {
        VESSELSTATUS2 status{};status.version=2;oapiGetVesselInterface(target)->GetStatusEx(&status);
        status.rpos.x+=100;status.flag=0;
        child=oapiCreateVesselEx("Child","ShuttlePB",&status);
        require(child && oapiGetVesselInterface(child)->GetThrusterCount()==16,"source-built child module missing");
        event("input.create","Child","ShuttlePB");
    }
    void snapshot() {
        OBJHANDLE earth=oapiGetObjectByName(const_cast<char *>("Earth"));
        require(earth != nullptr,"production Earth is missing");
        VECTOR3 ep{},ev{};oapiGetGlobalPos(earth,&ep);oapiGetGlobalVel(earth,&ev);
        std::vector<VESSEL *> list;
        for (DWORD i=0;i<oapiGetVesselCount();++i) list.push_back(oapiGetVesselInterface(oapiGetVesselByIndex(i)));
        std::sort(list.begin(),list.end(),[](VESSEL *a,VESSEL *b) { return std::string(a->GetName()) < b->GetName(); });
        for (VESSEL *v:list) {
            VECTOR3 p{},velocity{},omega{};MATRIX3 r{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(r);
            const double values[]={p.x-ep.x,p.y-ep.y,p.z-ep.z,velocity.x-ev.x,velocity.y-ev.y,velocity.z-ev.z,
                r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass(),
                v->GetAltitude(ALTMODE_GROUND),v->GetAltitude(),v->GetAirspeed(),v->GetAtmDensity(),v->GetDynPressure(),v->GetLift(),v->GetDrag()};
            states << tick << ',' << frame << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD() << ',' << v->GetName() << ',' << v->GetClassName();
            for (double value:values) { require(std::isfinite(value),"nonfinite production behavior state");states << ',' << value; }
            unsigned navmask=0;for (int mode=1;mode<=7;++mode) if(v->GetNavmodeState(mode)) navmask|=1u<<mode;
            states << ',' << int(v->GroundContact()) << ',' << nameOf(v->DockCount() ? v->GetDockStatus(v->GetDockHandle(0)) : nullptr)
                   << ',' << nameOf(oapiGetFocusObject()) << ',' << navmask << ',';
            for (bool parent : {false,true}) for (DWORD i=0;i<v->AttachmentCount(parent);++i) {
                OBJHANDLE attached=v->GetAttachmentStatus(v->GetAttachmentHandle(parent,i));
                if (attached) states << nameOf(attached) << ';';
            }
            states << '\n';
            for (DWORD i=0;i<v->GetPropellantCount();++i) {
                auto h=v->GetPropellantHandleByIndex(i);
                propellant << tick << ',' << v->GetName() << ',' << i << ',' << v->GetPropellantMass(h) << ',' << v->GetPropellantMaxMass(h) << '\n';
            }
            for (unsigned i=0;i<256;++i) {
                double state=v->GetAnimation(i);if(state < 0) break;
                require(std::isfinite(state),"nonfinite stock animation");animations << tick << ',' << v->GetName() << ',' << i << ',' << state << '\n';
            }
        }
    }
};
void observe(const char *phase,const char *object,double simt,double mjd,int running) {
    if (driver) driver->core(phase,object,simt,mjd,running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) {
    try { driver=new Driver(instance);oapiRegisterModule(driver); }
    catch(const std::exception &e) { oapiWriteLog(const_cast<char *>(e.what()));std::exit(1); }
}
DLLCLBK void ExitModule(HINSTANCE) { delete driver;driver=nullptr; }
