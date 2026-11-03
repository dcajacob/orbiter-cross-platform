// Licensed under the MIT License
// Passive SDK observations; retain every original call and live argument.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "../StockVessels/Observation.h"
#include <chrono>
#include <cstdlib>
#include <dlfcn.h>
#include <thread>

namespace {
struct Preload { Preload() { unsetenv("LD_PRELOAD"); } } preload;
std::ofstream state,docks;
bool initialized=false;
unsigned frames=0;
}
void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    stock_vessels::require(original!=nullptr,"Original legacy UpdateWorld missing");
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    if(!initialized) {
        stock_vessels::headers(state,docks);stock_vessels::snapshot(state,docks,0);
        std::ifstream maps("/proc/self/maps");std::ofstream loaded("renderer-modules.txt");loaded<<maps.rdbuf();
        initialized=true;
    }
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    stock_vessels::require(original!=nullptr,"Original legacy EndTimeStep missing");
    original(services,time,running,active,force);
    stock_vessels::snapshot(state,docks,++frames);
}
