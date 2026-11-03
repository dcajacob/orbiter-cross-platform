// Licensed under the MIT License
// Read-only observations; original session calls and live arguments are retained.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "../../StockVessels/Observation.h"
#include <chrono>
#include <cstdlib>
#include <dlfcn.h>
#include <thread>

namespace {
struct ProcessPreload { ProcessPreload() { unsetenv("LD_PRELOAD"); } } processPreload;
std::ofstream state, docks, phases;
unsigned frames = 0;
bool initialized = false;
}
void orbiter::production::Session::UpdateWorld(SessionServices& services, const TimeData& time,
    const bool& running, const bool& playback, bool& updating, const bool& force)
{
    static auto original = reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    stock_vessels::require(original != nullptr, "Original UpdateWorld missing");
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    if (!initialized) {
        stock_vessels::headers(state, docks);
        stock_vessels::open(phases, "stock-exit-phases.csv", "completed_frames,phase");
        stock_vessels::snapshot(state, docks, 0);
        std::ifstream maps("/proc/self/maps");
        std::ofstream loaded("renderer-modules.txt"); loaded << maps.rdbuf();
        initialized = true;
    }
    original(services, time, running, playback, updating, force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services, TimeData& time,
    bool running, const bool& active, bool& force)
{
    static auto original = reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    stock_vessels::require(original != nullptr, "Original EndTimeStep missing");
    original(services, time, running, active, force);
    stock_vessels::snapshot(state, docks, ++frames);
    phases << frames << ",app.frame.end\n"; phases.flush();
}
