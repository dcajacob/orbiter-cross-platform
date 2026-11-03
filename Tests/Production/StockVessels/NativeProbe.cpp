// Licensed under the MIT License
// Read-only SDK observations at the existing production session boundaries.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Observation.h"
#include <chrono>
#include <dlfcn.h>
#include <thread>

namespace {
std::ofstream state,docks;
unsigned frames=0;
bool initialized=false;
}
void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    stock_vessels::require(original!=nullptr,"Original stock UpdateWorld missing");
    // Match the original reference observer's instrument refresh pacing.
    // Fixed simulation ticks and the original call's arguments remain intact.
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    if(!initialized) {
        stock_vessels::headers(state,docks);stock_vessels::snapshot(state,docks,0);initialized=true;
    }
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    stock_vessels::require(original!=nullptr,"Original stock EndTimeStep missing");
    original(services,time,running,active,force);
    stock_vessels::snapshot(state,docks,++frames);
}
