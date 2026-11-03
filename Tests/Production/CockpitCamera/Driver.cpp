// Licensed under the MIT License
// Observe the exact preserved Windows application through its public SDK.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "Observation.h"
#include <cstdlib>
#include <limits>
#include <string>

namespace {
using namespace camera_fixture;
using SetObserver=int(*)(unsigned,OrbiterTestObserver,double);
class Driver;
Driver* driver=nullptr;
void observe(const char*,const char*,double,double,int);
class Driver final:public oapi::Module {
    SetObserver setter=nullptr;
    std::ofstream camera,state;
    unsigned frames=0;
    int previousFma=-1;
    bool started=false,initialized=false;
    template<class F>void guarded(F action) {
        try {action();}
        catch(const std::exception& error) {
            std::ofstream("cockpit-failure.txt")<<error.what()<<'\n';std::exit(42);
        }
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance) {guarded([&] {
        if(std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
            previousFma=_get_FMA3_enable();_set_FMA3_enable(0);
            require(_get_FMA3_enable()==0,"Original camera SSE2 profile was not selected");
        }
        std::ofstream("math-profile.txt")<<(_get_FMA3_enable()?"fma3":"sse2")<<'\n';
        CameraHeader(camera);StateHeader(state);
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));
        require(setter && setter(1,observe,51982.5),"Preserved camera observation ABI missing");
        std::srand(0);
    });}
    ~Driver()override {
        if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());
        if(previousFma>=0)_set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode)override {
        guarded([&] {require(mode!=RENDER_NONE,"Original camera graphics required");started=true;});
    }
    void clbkPreStep(double,double,double)override {guarded([&] {
        Sleep(120); // Original MFD wall-clock refresh bound, as in cockpit captures.
        if(!initialized) {
            require(oapiCameraInternal() && oapiCockpitMode()==3,"Original VC did not initialize");
            Apply();initialized=true;State(state,0);
        }
    });}
    void core(const char* phase,int running) {guarded([&] {
        if(started && std::string(phase)=="app.frame.end") {
            require(initialized && running,"Unexpected original camera frame state");
            ++frames;Camera(camera,frames);State(state,frames);
        }
    });}
    void clbkSimulationEnd()override {guarded([&] {
        require(frames==60,"Incomplete original headlook capture");started=false;
        std::ofstream("cockpit-complete.txt")<<frames<<'\n';
    });}
};
void observe(const char* phase,const char*,double,double,int running) {
    if(driver)driver->core(phase,running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) {driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE) {delete driver;driver=nullptr;}
