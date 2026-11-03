// Licensed under the MIT License
// Recorded SDK inputs and read-only observations of the original Windows app.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "Vessel.h" // exact internal header from the preserved runtime commit
#include "ApplicationObservation.h"
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <filesystem>
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
    std::string target,profile;
    unsigned frames=0,total=0;int cockpit=0,left=0,right=0,hud=0;
    bool started=false,initialized=false;
    std::ofstream air,controller,horizon;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("cockpit-failure.txt")<<e.what()<<'\n';std::exit(42);}}
    void recordLibraries() {
        std::ofstream loaded("lua-loaded.txt");
        for(const auto* name:{"LuaInline.dll","LuaInterpreter.dll","lua.dll"}) {
            auto library=GetModuleHandleA(name);
            wchar_t path[32768];
            auto count=library ? GetModuleFileNameW(library,path,32768) : 0;
            require(count>0 && count<32768 && std::filesystem::equivalent(path,std::filesystem::current_path()/name),
                    "Original app-local Lua module missing");
            loaded<<name<<'\n';
        }
    }
    void sampleController() {
        if (target!="DG" || frames<31 || frames>46) return;
        // The original script stores these intermediates in globals. Observe
        // them after the worker has yielded, without running an extra chunk.
        auto* L=oapiGetLua(script);
        static auto module=GetModuleHandleA("lua.dll");
        static auto field=reinterpret_cast<decltype(&lua_getfield)>(GetProcAddress(module,"lua_getfield"));
        static auto numeric=reinterpret_cast<decltype(&lua_type)>(GetProcAddress(module,"lua_type"));
        static auto number=reinterpret_cast<decltype(&lua_tonumber)>(GetProcAddress(module,"lua_tonumber"));
        static auto pop=reinterpret_cast<decltype(&lua_settop)>(GetProcAddress(module,"lua_settop"));
        require(L && field && numeric && number && pop,"Original Lua observation functions unavailable");
        controller<<frames;
        for(const auto* name:{"alt","sl","dslope","delev","elev","dbnk","rate","dail","ail","thrott","dthrott","xz"}) {
            field(L,LUA_GLOBALSINDEX,name);
            require(numeric(L,-1)==LUA_TNUMBER,"Missing original AAP intermediate");
            controller<<','<<number(L,-1);pop(L,-2);
        }
        field(L,LUA_GLOBALSINDEX,"as");
        require(numeric(L,-1)==LUA_TTABLE,"Missing original AAP horizon airspeed vector");
        for (const auto* component:{"x","y","z"}) {
            field(L,-1,component);
            require(numeric(L,-1)==LUA_TNUMBER,"Missing original AAP horizon airspeed component");
            controller<<','<<number(L,-1);pop(L,-2);
        }
        pop(L,-2);
        controller<<'\n';controller.flush();
    }
    void sampleHorizon(unsigned tick) {
        auto *v=oapiGetFocusInterface();
        VECTOR3 global{},local{},horizontal{};
        require(v && v->GetAirspeedVector(FRAME_GLOBAL,global) && v->GetAirspeedVector(FRAME_REFLOCAL,local) &&
                v->GetAirspeedVector(FRAME_HORIZON,horizontal),"Missing original horizon velocity");
        double lng,lat,rad;
        OBJHANDLE ref=v->GetEquPos(lng,lat,rad);
        require(ref!=nullptr,"Missing original surface reference");
        MATRIX3 rot;
        oapiGetRotationMatrix(ref,&rot);
        // Reconstruct the latitude input independently using public SDK coordinates.
        VECTOR3 globalPosition{},planetLocal{};
        v->GetGlobalPos(globalPosition);
        oapiGlobalToLocal(ref,&globalPosition,&planetLocal);
        const double asinInput=planetLocal.y/rad;
        const auto* surface=static_cast<const Vessel*>(v->GetHandle())->GetSurfParam();
        require(surface && static_cast<const void*>(surface->ref)==static_cast<const void*>(ref) &&
                surface->lng==lng && surface->lat==lat && surface->rad==rad,
                "Original surface parameters do not match their public SDK values");
        const double surfaceAsinInput=surface->ploc.y/surface->rad;
        horizon<<tick;
        for(double value:{global.x,global.y,global.z,local.x,local.y,local.z,horizontal.x,horizontal.y,horizontal.z,
                          lng,lat,rad,rot.m11,rot.m12,rot.m13,rot.m21,rot.m22,rot.m23,rot.m31,rot.m32,rot.m33,
                          planetLocal.x,planetLocal.y,planetLocal.z,asinInput,std::asin(asinInput),
                          surface->ploc.x,surface->ploc.y,surface->ploc.z,surfaceAsinInput,
                          std::asin(surfaceAsinInput),surface->slat,surface->clat})
            horizon<<','<<value;
        horizon<<'\n';
    }
    void snapshot(){
        auto* v=oapiGetFocusInterface();require(v && target==v->GetName(),"Cockpit focus differs from required real vessel");
        VECTOR3 p{},velocity{},omega{};MATRIX3 rotation{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(rotation);
        state<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<v->GetName()<<','<<v->GetClassName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1);
        for(double value:{p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,rotation.m11,rotation.m12,rotation.m13,rotation.m21,rotation.m22,rotation.m23,rotation.m31,rotation.m32,rotation.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass()})state<<','<<value;
        state<<','<<v->GetMeshCount()<<','<<v->GetThrusterCount()<<'\n';state.flush();
        air<<frames<<','<<v->GetAtmDensity()<<','<<v->GetDynPressure()<<','<<v->GetAirspeed()<<'\n';air.flush();
        controls<<frames<<','<<v->GetControlSurfaceLevel(AIRCTRL_ELEVATOR)<<','<<v->GetControlSurfaceLevel(AIRCTRL_AILERON)<<','<<v->GetThrusterGroupLevel(THGROUP_MAIN)<<'\n';controls.flush();
        sampleController();
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("cockpit-case.txt");require(bool(input>>target>>total>>cockpit>>left>>right>>hud>>profile),"Invalid cockpit fixture controls");
        require(total==60 && cockpit>=1 && cockpit<=3 && left>=1 && left<=10 && right>=1 && right<=10,"Unsupported cockpit control schedule");
        for(auto* stream:{&state,&events,&controls,&air,&controller,&horizon}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);}
        horizon.open("lua-horizon.csv");horizon<<std::setprecision(17)<<"tick,global_x,global_y,global_z,ref_x,ref_y,ref_z,horizon_x,horizon_y,horizon_z,lng,lat,rad,m11,m12,m13,m21,m22,m23,m31,m32,m33,position_local_x,position_local_y,position_local_z,reconstructed_asin_input,reconstructed_latitude,actual_local_x,actual_local_y,actual_local_z,actual_asin_input,probe_asin_of_actual_input,actual_slat,actual_clat\n";
        controller.open("lua-controller.csv");controller<<std::setprecision(17)<<"tick,alt,sl,dslope,delev,elev,dbnk,rate,dail,ail,thrott,dthrott,xz,as_x,as_y,as_z\n";
        std::ofstream("math-host.txt")<<"fma3_enabled="<<_get_FMA3_enable()<<'\n';
        air.open("lua-air.csv");air<<std::setprecision(17)<<"tick,density,dynamic_pressure,airspeed\n";
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
#include "ScriptSchedule.inc"

    });}
    void core(const char* phase,const char* object,double seconds,double mjd,int running){guarded([&]{
        events<<frames<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<','<<running<<'\n';
        if (target=="DG" && object && target==object && frames>=30 && frames<46 && std::string(phase)=="vessel.post.after")
            sampleHorizon(frames+1);
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
