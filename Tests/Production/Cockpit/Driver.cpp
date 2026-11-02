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
    std::ofstream state,events;
    std::string target;
    unsigned frames=0,total=0;int cockpit=0,left=0,right=0,hud=0;
    bool started=false;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("cockpit-failure.txt")<<e.what()<<'\n';std::exit(42);}}
    void snapshot(){
        auto* v=oapiGetFocusInterface();require(v && target==v->GetName(),"Cockpit focus differs from required real vessel");
        VECTOR3 p{},velocity{},omega{};MATRIX3 rotation{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(rotation);
        state<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<v->GetName()<<','<<v->GetClassName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1);
        for(double value:{p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,rotation.m11,rotation.m12,rotation.m13,rotation.m21,rotation.m22,rotation.m23,rotation.m31,rotation.m32,rotation.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass()})state<<','<<value;
        state<<','<<v->GetMeshCount()<<','<<v->GetThrusterCount()<<'\n';state.flush();
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("cockpit-case.txt");require(bool(input>>target>>total>>cockpit>>left>>right>>hud),"Invalid cockpit fixture controls");
        require(total==60 && cockpit>=1 && cockpit<=3 && left>=1 && left<=10 && right>=1 && right<=10,"Unsupported cockpit control schedule");
        for(auto* stream:{&state,&events}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);}
        state.open("cockpit-state.csv");events.open("cockpit-events.csv");state<<std::setprecision(17);events<<std::setprecision(17);
        state<<"tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters\n";
        events<<"tick,seconds,mjd,phase,object,running\n";
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));require(setter && setter(1,observe,51982.5),"Original observation ABI missing");std::srand(0);
    });}
    ~Driver()override{if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());}
    void clbkSimulationStart(RenderMode mode)override{guarded([&]{
        require(mode!=RENDER_NONE,"Real graphics client required");auto* v=oapiGetFocusInterface();require(v && v->GetThrusterCount()>0 && v->GetMeshCount()>0,"Actual stock vessel required");
        oapiOpenMFD(left,0);oapiOpenMFD(right,1);oapiSetHUDMode(hud);started=true;snapshot();
    });}
    void clbkPreStep(double,double,double)override{guarded([&]{
        // The stock MFD scheduler limits real-time refresh to 10Hz. Pace these
        // software-rendered fixtures above that bound without altering clocks,
        // calculations, integrators or the original instrumentation scheduler.
        Sleep(120);
        if(frames==10){oapiSetHUDMode(hud%3+1);}
        if(frames==30){oapiSetHUDMode(hud);}
    });}
    void core(const char* phase,const char* object,double seconds,double mjd,int running){guarded([&]{
        events<<frames<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<','<<running<<'\n';
        if(started && std::string(phase)=="app.frame.end"){
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
