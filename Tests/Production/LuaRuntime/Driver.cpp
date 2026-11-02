// Licensed under the MIT License
// Recorded SDK inputs and read-only observations of the original Windows app.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
namespace {
using SetObserver=int(*)(unsigned,OrbiterTestObserver,double);
class Driver;
Driver* driver=nullptr;
void observe(const char*,const char*,double,double,int);
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
class Driver final:public oapi::Module {
    SetObserver setter=nullptr;
    std::ofstream state,events,controls;
    INTERPRETERHANDLE script=nullptr,secondary=nullptr;
    std::string target;
    unsigned frames=0,total=0;int cockpit=0,left=0,right=0,hud=0;
    bool started=false,initialized=false;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("cockpit-failure.txt")<<e.what()<<'\n';std::exit(42);}}
    void snapshot(){
        auto* v=oapiGetFocusInterface();require(v && target==v->GetName(),"Cockpit focus differs from required real vessel");
        VECTOR3 p{},velocity{},omega{};MATRIX3 rotation{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(rotation);
        state<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<v->GetName()<<','<<v->GetClassName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1);
        for(double value:{p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,rotation.m11,rotation.m12,rotation.m13,rotation.m21,rotation.m22,rotation.m23,rotation.m31,rotation.m32,rotation.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass()})state<<','<<value;
        state<<','<<v->GetMeshCount()<<','<<v->GetThrusterCount()<<'\n';state.flush();
        controls<<frames<<','<<v->GetControlSurfaceLevel(AIRCTRL_ELEVATOR)<<','<<v->GetControlSurfaceLevel(AIRCTRL_AILERON)<<','<<v->GetThrusterGroupLevel(THGROUP_MAIN)<<'\n';controls.flush();
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("cockpit-case.txt");require(bool(input>>target>>total>>cockpit>>left>>right>>hud),"Invalid cockpit fixture controls");
        require(total==60 && cockpit>=1 && cockpit<=3 && left>=1 && left<=10 && right>=1 && right<=10,"Unsupported cockpit control schedule");
        for(auto* stream:{&state,&events,&controls}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);}
        controls.open("lua-controls.csv");controls<<std::setprecision(17)<<"tick,elevator,aileron,main\n";
        state.open("cockpit-state.csv");events.open("cockpit-events.csv");state<<std::setprecision(17);events<<std::setprecision(17);
        state<<"tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters\n";
        events<<"tick,seconds,mjd,phase,object,running\n";
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));require(setter && setter(1,observe,51982.5),"Original observation ABI missing");std::srand(0);
    });}
    ~Driver()override{if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());}
    void clbkSimulationStart(RenderMode mode)override{guarded([&]{
        require(mode!=RENDER_NONE,"Real graphics client required");auto* v=oapiGetFocusInterface();require(v && v->GetThrusterCount()>0 && v->GetMeshCount()>0,"Actual stock vessel required");
        started=true;
    });}
    void clbkPreStep(double,double,double)override{guarded([&]{
        // The stock MFD scheduler limits real-time refresh to 10Hz. Pace these
        // software-rendered fixtures above that bound without altering clocks,
        // calculations, integrators or the original instrumentation scheduler.
        Sleep(120);
        // Original Orbiter initializes Pane after clbkSimulationStart. The
        // first pre-step is the first SDK control point with a complete panel.
        if(!initialized){
            require(oapiCameraInternal() && oapiCockpitMode()==cockpit,"Scenario cockpit failed to initialize");
            oapiOpenMFD(left,0);oapiOpenMFD(right,1);oapiSetHUDMode(hud);initialized=true;snapshot();
        }
        if(frames==0) {
            script=oapiCreateInterpreter();require(script!=nullptr,"Original Lua interpreter creation failed");
            require(oapiGetLua(script)!=nullptr,"Original Lua state missing");
            const char* setup=R"lua(
                audit_count=0
                function audit(event)
                    local file=assert(io.open('lua-events.csv','a'))
                    file:write(string.format('%s,%.17g,%.17g\n',event,oapi.get_simtime(),oapi.get_simstep()))
                    file:close()
                    audit_count=audit_count+1
                end
                audit('sync_initial')
            )lua";
            std::ofstream("lua-events.csv")<<"event,seconds,step\n";
            require(oapiExecScriptCmd(script,setup),"Synchronous original Lua setup failed");
            if(target=="DG") {
                require(oapiExecScriptCmd(script,"run('dg/aap'); setvessel(vessel.get_interface('DG')); assert(v~=nil); audit('aap_loaded')"),"Original DG AAP script failed");
            }
        }
        if(frames==10) {
            require(oapiAsyncScriptCmd(script,"audit('async_one')"),"First original asynchronous command failed");
            require(oapiAsyncScriptCmd(script,"audit('async_two')"),"Second original asynchronous command failed");
            require(oapiExecScriptCmd(script,"audit('sync_override')"),"Original synchronous override failed");
        }
        if(frames==20) {
            require(oapiAsyncScriptCmd(script,"for i=1,4 do audit('yield_'..i); proc.skip() end; audit('yield_done')"),"Original yielding command failed");
        }
        if(frames==30) {
            secondary=oapiCreateInterpreter();require(secondary!=nullptr,"Second original interpreter missing");
            require(oapiExecScriptCmd(secondary,"assert(audit_count==nil); local f=assert(io.open('lua-isolation.txt','w')); f:write('isolated'); f:close()"),"Original interpreter isolation failed");
            if(target=="DG")require(oapiAsyncScriptCmd(script,"aap.alt(20000); aap.spd(100); aap.bank(5); audit('aap_started')"),"Original AAP activation failed");
        }
        if(frames==45) {
            require(oapiDelInterpreter(secondary)==0,"Original secondary interpreter deletion failed");secondary=nullptr;
            if(target=="DG")require(oapiAsyncScriptCmd(script,"aap.alt(); aap.spd(); aap.bank(); audit('aap_stopped')"),"Original AAP stop failed");
        }
        if(frames==54)require(oapiExecScriptCmd(script,"audit('complete')"),"Original Lua completion failed");
        if(frames==55) {require(oapiDelInterpreter(script)==0,"Original interpreter deletion failed");script=nullptr;}

    });}
    void core(const char* phase,const char* object,double seconds,double mjd,int running){guarded([&]{
        events<<frames<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<','<<running<<'\n';
        if(started && std::string(phase)=="app.frame.end"){
            require(initialized,"Original frame completed before cockpit setup");
            require(running!=0,"Unexpected paused reference frame");++frames;snapshot();
            require(oapiCameraInternal() && oapiCockpitMode()==cockpit,"Original requested cockpit did not initialize");
            require(oapiGetMFDMode(0)==left && oapiGetMFDMode(1)==right,"Original stock instruments did not initialize");
        }
    });}
    void clbkSimulationEnd()override{guarded([&]{require(frames==total,"Incomplete cockpit reference run");started=false;events.flush();state.flush();std::ofstream("cockpit-complete.txt")<<frames<<'\n';});}
};
void observe(const char* phase,const char* object,double seconds,double mjd,int running){if(driver)driver->core(phase,object,seconds,mjd,running);}
}
DLLCLBK void InitModule(HINSTANCE instance){driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE){delete driver;driver=nullptr;}
