// Licensed under the MIT License
// Additional observations in the unchanged preserved Windows application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "../StockVessels/Observation.h"
#include "Details.h"
#include <cstdlib>
#include <limits>

namespace {
using namespace stock_vessels;
using SetObserver=int(*)(unsigned,OrbiterTestObserver,double);
class Driver;
Driver* driver=nullptr;
void observe(const char*,const char*,double,double,int);
class Driver final:public oapi::Module {
    SetObserver setter=nullptr;
    std::ofstream state,docks;
    remaining_stock::Details details;
    unsigned frames=0;
    int previousFma=-1;
    bool started=false,initialized=false;
    template<class F>void guarded(F action) {
        try {action();}
        catch(const std::exception& error) {
            std::ofstream("stock-vessel-failure.txt")<<error.what()<<'\n';std::exit(42);
        }
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance) {guarded([&] {
        if(std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
            previousFma=_get_FMA3_enable();_set_FMA3_enable(0);
            require(_get_FMA3_enable()==0,"Original stock observer SSE2 profile was not selected");
        }
        std::ofstream("math-profile.txt")<<(_get_FMA3_enable()?"fma3":"sse2")<<'\n';
        headers(state,docks);details.open();
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));
        require(setter && setter(1,observe,51982.5),"Preserved stock observation ABI missing");
        std::srand(0);
    });}
    ~Driver()override {
        if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());
        if(previousFma>=0)_set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode)override {
        guarded([&] {require(mode!=RENDER_NONE,"Original stock graphics required");started=true;});
    }
    void clbkPreStep(double,double,double)override {guarded([&] {
        Sleep(120); // Same wall-clock instrument refresh bound as accepted cockpit captures.
        if(!initialized) {snapshot(state,docks,0);details.snapshot(0);initialized=true;}
    });}
    void core(const char* phase,int running) {guarded([&] {
        if(started && std::string(phase)=="app.frame.end") {
            require(initialized && running,"Unexpected original stock frame state");
            snapshot(state,docks,++frames);details.snapshot(frames);
        }
    });}
    void clbkSimulationEnd()override {guarded([&] {
        require(frames==60,"Incomplete original stock observation");started=false;
        std::ofstream("stock-vessel-complete.txt")<<frames<<'\n';
    });}
};
void observe(const char* phase,const char*,double,double,int running) {
    if(driver)driver->core(phase,running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) {driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE) {delete driver;driver=nullptr;}
