// Licensed under the MIT License. SDK-only observations of the frozen original.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <map>
#include <stdexcept>
#include <string>
namespace {
using SetObserver=int(*)(unsigned,OrbiterTestObserver,double);
class Driver;Driver* driver=nullptr;
void observe(const char*,const char*,double,double,int);
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
class Driver final:public oapi::Module {
    SetObserver setter=nullptr;std::ofstream hud,vessels;std::string target,math;
    std::map<std::string,std::string> expected;unsigned frames=0;int cockpit=0,initialHud=0,previousFma=-1;
    bool started=false,initialized=false;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("named-failure.txt")<<e.what()<<'\n';std::exit(42);}}
    void snapshot(){
        auto* focus=oapiGetFocusInterface();require(focus && target==focus->GetName(),"Actual full-scene focus differs");
        require(oapiGetVesselCount()==8,"Original complete eight-object graph required");
        hud<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<focus->GetName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1)<<','<<oapiGetVesselCount()<<'\n';hud.flush();
        std::map<std::string,std::string> actual;
        for(unsigned i=0;i<oapiGetVesselCount();++i){
            auto* v=oapiGetVesselInterface(oapiGetVesselByIndex(i));require(v,"Actual stock vessel interface missing");
            actual.emplace(v->GetName(),v->GetClassName());VECTOR3 p{},velocity{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);
            vessels<<frames<<','<<v->GetName()<<','<<v->GetClassName()<<','<<p.x<<','<<p.y<<','<<p.z<<','<<velocity.x<<','<<velocity.y<<','<<velocity.z<<','<<v->GetMass()<<','<<v->GetFuelMass()<<'\n';
        }
        require(actual==expected,"An original complete-scene class/object was dropped or replaced");vessels.flush();
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("named-case.txt");require(bool(input>>target>>cockpit>>initialHud>>math),"Invalid complete-scene diagnostic input");
        require(math=="automatic" || math=="sse2","Unknown original arithmetic selection");
        previousFma=_get_FMA3_enable();if(math=="sse2")_set_FMA3_enable(0);
        if(math=="sse2")require(_get_FMA3_enable()==0,"Original actual SSE2 CRT selection failed");
        std::ofstream("named-math.txt")<<(_get_FMA3_enable()?"fma3":"sse2")<<'\n';
        std::ifstream names("named-vessels.txt");std::string name,kind;while(names>>name>>kind)require(expected.emplace(name,kind).second,"Duplicate required stock object");require(expected.size()==8,"Complete original roster missing");
        for(auto* stream:{&hud,&vessels}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);*stream<<std::setprecision(17);}
        hud.open("named-hud-state.csv");hud<<"tick,seconds,mjd,object,cockpit,hud,left_mfd,right_mfd,vessels\n";
        vessels.open("named-vessel-state.csv");vessels<<"tick,object,class,x,y,z,vx,vy,vz,mass,fuel\n";
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));require(setter && setter(1,observe,std::numeric_limits<double>::quiet_NaN()),"Original observation ABI missing");std::srand(0);
    });}
    ~Driver()override{if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());if(previousFma>=0)_set_FMA3_enable(previousFma);}
    void clbkSimulationStart(RenderMode mode)override{guarded([&]{require(mode!=RENDER_NONE,"Original real graphics required");started=true;});}
    void clbkPreStep(double,double,double)override{guarded([&]{
        Sleep(120); // Same actual instrument refresh pacing as the accepted original.
        if(!initialized){require(oapiCameraInternal() && oapiCockpitMode()==cockpit && oapiGetHUDMode()==initialHud,"Derived complete-scene cockpit failed to initialize");initialized=true;snapshot();}
    });}
    void core(const char* phase,int running){guarded([&]{if(started && std::string(phase)=="app.frame.end"){require(initialized && running,"Unexpected complete-scene frame state");++frames;snapshot();}});}
    void clbkSimulationEnd()override{guarded([&]{require(frames==60,"Incomplete complete-scene run");started=false;std::ofstream("named-complete.txt")<<frames<<'\n';});}
};
void observe(const char* phase,const char*,double,double,int running){if(driver)driver->core(phase,running);}
}
DLLCLBK void InitModule(HINSTANCE instance){driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE){delete driver;driver=nullptr;}
