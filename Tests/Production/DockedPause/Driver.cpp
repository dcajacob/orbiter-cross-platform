// Licensed under the MIT License. Separate public-SDK serialization diagnostic.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <tlhelp32.h>
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
    SetObserver setter=nullptr;std::ofstream clock,vessels,events;
    std::map<std::string,std::string> expected;std::string phase,math;
    unsigned frames=0,target=0;int cockpit=0,previousFma=-1;
    double elapsed=0.0,savedSeconds=0.0,savedMjd=0.0;
    bool started=false,initial=false,saved=false;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("pause-failure.txt")<<e.what()<<std::endl;std::exit(42);}}
    void snapshot(int running){
        auto* focus=oapiGetFocusInterface();require(focus && std::string(focus->GetName())=="GL-02","Original docked focus changed");
        require(oapiGetVesselCount()==6,"Complete original six-object scene required");
        clock<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<running<<','<<oapiGetPause()<<','<<focus->GetName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<'\n';clock.flush();
        std::map<std::string,std::string> actual;
        for(unsigned i=0;i<oapiGetVesselCount();++i){
            auto* v=oapiGetVesselInterface(oapiGetVesselByIndex(i));require(v,"Original stock interface missing");actual.emplace(v->GetName(),v->GetClassName());
            VECTOR3 p{},velocity{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);
            vessels<<frames<<','<<v->GetName()<<','<<v->GetClassName()<<','<<v->Version()<<','<<p.x<<','<<p.y<<','<<p.z<<','<<velocity.x<<','<<velocity.y<<','<<velocity.z<<','<<v->GetMass()<<','<<v->GetFuelMass()<<'\n';
        }
        require(actual==expected,"Original docked scene lost or replaced an object");vessels.flush();
    }
    void loaded_modules(){
        HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,GetCurrentProcessId());
        require(snapshot!=INVALID_HANDLE_VALUE,"Cannot inspect actual paused-process DLL paths");
        try {
            std::ofstream modules("pause-loaded-modules.txt");modules.exceptions(std::ios::badbit|std::ios::failbit);
            MODULEENTRY32W module{};module.dwSize=sizeof(module);
            require(Module32FirstW(snapshot,&module)!=FALSE,"Actual paused-process module snapshot is empty");
            do { modules<<std::filesystem::path(module.szExePath).generic_u8string()<<'\n'; }
            while(Module32NextW(snapshot,&module));
        }catch(...){CloseHandle(snapshot);throw;}
        CloseHandle(snapshot);
    }
    void save(){
        require(oapiGetPause(),"Serialization occurred while running");savedSeconds=oapiGetSimTime();savedMjd=oapiGetSimMJD();
        require(oapiSaveScenario("PausedResult","Original paused docked state"),"Original public SDK save failed");loaded_modules();saved=true;
        std::ofstream marker("pause-saved-clock.csv");marker.imbue(std::locale::classic());marker<<std::setprecision(17)<<"seconds,mjd\n"<<savedSeconds<<','<<savedMjd<<'\n';
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("pause-case.txt");require(bool(input>>phase>>target>>cockpit>>math),"Invalid paused diagnostic input");
        require((phase=="writer" || phase=="reload") && target>6 && target<3600 && (cockpit==2 || cockpit==3),"Unknown paused diagnostic mode");
        require(math=="automatic" || math=="sse2","Unknown CRT profile");previousFma=_get_FMA3_enable();if(math=="sse2")_set_FMA3_enable(0);
        require(math!="sse2" || _get_FMA3_enable()==0,"Original actual SSE2 selection failed");std::ofstream("pause-math.txt")<<(_get_FMA3_enable()?"fma3":"sse2")<<'\n';
        std::ifstream names("pause-vessels.txt");std::string name,kind;while(names>>name>>kind)require(expected.emplace(name,kind).second,"Duplicate required original object");require(expected.size()==6,"Original six-object roster missing");
        for(auto* stream:{&clock,&vessels,&events}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);*stream<<std::setprecision(17);}
        clock.open("pause-clock.csv");clock<<"frame,seconds,mjd,running,paused,object,cockpit,hud\n";
        vessels.open("pause-vessels.csv");vessels<<"frame,object,class,api_version,x,y,z,vx,vy,vz,mass,fuel\n";
        events.open("pause-events.csv");events<<"frame,phase,seconds,mjd,running\n";
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));require(setter && setter(1,observe,std::numeric_limits<double>::quiet_NaN()),"Original observation ABI missing");std::srand(0);
    });}
    ~Driver()override{if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());if(previousFma>=0)_set_FMA3_enable(previousFma);}
    void clbkSimulationStart(RenderMode mode)override{guarded([&]{require(mode!=RENDER_NONE,"Original real renderer required");started=true;if(phase=="reload")oapiSetPause(true);});}
    void clbkPreStep(double,double,double)override{guarded([&]{require(phase=="writer","Paused original reload performed a physics step");if(!initial){require(oapiCameraInternal() && oapiCockpitMode()==cockpit && oapiGetHUDMode()==3,"Original docked cockpit did not initialize");initial=true;snapshot(1);}});}
    void core(const char* event,double seconds,double mjd,int running){guarded([&]{
        if(!started)return;events<<frames<<','<<event<<','<<seconds<<','<<mjd<<','<<running<<'\n';
        if(phase=="reload" && std::string(event).find("vessel.pre.")==0)require(false,"Paused reload updated a stock vessel");
        if(std::string(event)!="app.frame.end")return;
        ++frames;
        if(phase=="writer"){
            require((running!=0)==(frames<=target),"Original writer pause boundary differs");if(running)elapsed+=1.0/60.0;
            require(oapiGetSimTime()==elapsed,"Original exact fixed-step writer clock differs");
            if(frames<=3)require(oapiSimulateBufferedKey(OAPI_KEY_F8),"Original F8 key dispatch failed");
            if(frames==4 || frames==5)require(oapiSimulateBufferedKey(OAPI_KEY_H),"Original H key dispatch failed");
            if(frames>=6)require(oapiCockpitMode()==cockpit && oapiGetHUDMode()==2,"Original buffered cockpit/HUD keys were not processed");
            if(frames==target)oapiSetPause(true);
            if(frames==target+1)save();
        }else{
            require(!running && oapiGetPause() && oapiGetSimTime()==0.0,"Original reload advanced before paused serialization");
            if(frames==1)save();
        }
        if(saved)require(oapiGetSimTime()==savedSeconds && oapiGetSimMJD()==savedMjd,"Paused original clock advanced");snapshot(running);
    });}
    void clbkSimulationEnd()override{guarded([&]{require(saved && frames==(phase=="writer"?target+8:8),"Original paused diagnostic incomplete");started=false;std::ofstream("pause-complete.txt")<<frames<<'\n';});}
};
void observe(const char* event,const char*,double seconds,double mjd,int running){if(driver)driver->core(event,seconds,mjd,running);}
}
DLLCLBK void InitModule(HINSTANCE instance){driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE){delete driver;driver=nullptr;}
