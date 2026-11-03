// Licensed under the MIT License
// Observations at the existing session boundaries; no propagation or input edits.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Observation.h"
#include <chrono>
#include <cstdlib>
#include <dlfcn.h>
#include <set>
#include <thread>

namespace {
struct ProcessOnlyPreload {
    ProcessOnlyPreload() {
        // These libraries are already mapped in the observed application.
        // GTK's separately sandboxed image helpers must not inherit this
        // application-specific probe or its explicit sanitizer preload.
        unsetenv("LD_PRELOAD");
    }
} processOnlyPreload;
std::ofstream state, docks, cockpit, animations, attachments;
unsigned frames = 0;
bool initialized = false;
void modules() {
    std::ifstream mappings("/proc/self/maps");
    std::string line;
    std::set<std::string> paths;
    while (std::getline(mappings, line)) {
        auto slash = line.find('/');
        if (slash != std::string::npos) paths.insert(line.substr(slash));
    }
    shuttle_a_controls::require(!paths.empty(), "Native controls module mappings are empty");
    std::ofstream output("renderer-modules.txt");
    output.exceptions(std::ios::badbit|std::ios::failbit);
    for (const auto& path : paths) output << path << '\n';
}
}
void orbiter::production::Session::UpdateWorld(SessionServices& services, const TimeData& time,
    const bool& running, const bool& playback, bool& updating, const bool& force) {
    static auto original = reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    shuttle_a_controls::require(original != nullptr, "Original UpdateWorld missing");
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    if (!initialized) {
        modules();
        shuttle_a_controls::headers(state,docks,cockpit,animations,attachments);
        shuttle_a_controls::snapshot(state,docks,cockpit,animations,attachments,0); initialized = true;
    }
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services, TimeData& time,
    bool running, const bool& active, bool& force) {
    static auto original = reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    shuttle_a_controls::require(original != nullptr, "Original EndTimeStep missing");
    original(services,time,running,active,force);
    shuttle_a_controls::snapshot(state,docks,cockpit,animations,attachments,++frames);
}
