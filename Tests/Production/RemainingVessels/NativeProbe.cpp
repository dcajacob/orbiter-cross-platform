// Licensed under the MIT License
// Read-only observations at the original session boundaries; every argument is forwarded.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "../StockVessels/Observation.h"
#include "../RemainingStock/Details.h"
#include <chrono>
#include <cstdlib>
#include <dlfcn.h>
#include <thread>
#ifdef ORBITER_NATIVE_INSTRUMENT_CONTROL
#include "../NativeInstrumentTarget/Control.h"
#endif

namespace {
struct Preload {Preload(){unsetenv("LD_PRELOAD");}} preload;
std::ofstream state,docks;
remaining_stock::Details details;
unsigned frames=0;
bool initialized=false;
struct Complete {
    ~Complete(){if(initialized)std::ofstream("stock-vessel-complete.txt")<<frames<<'\n';}
} complete;
}
void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    stock_vessels::require(original!=nullptr,"Original remaining-stock UpdateWorld missing");
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    if(!initialized) {
#ifdef ORBITER_NATIVE_INSTRUMENT_CONTROL
        native_instrument_target::run();
#endif
        stock_vessels::headers(state,docks);details.open();
        stock_vessels::snapshot(state,docks,0);details.snapshot(0);
        std::ifstream maps("/proc/self/maps");std::ofstream loaded("observer-loaded-maps.txt");loaded<<maps.rdbuf();
        initialized=true;
    }
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    stock_vessels::require(original!=nullptr,"Original remaining-stock EndTimeStep missing");
    original(services,time,running,active,force);
    stock_vessels::snapshot(state,docks,++frames);details.snapshot(frames);
}
