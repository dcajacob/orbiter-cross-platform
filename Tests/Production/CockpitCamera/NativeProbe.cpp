// Licensed under the MIT License
// Test-only interposition: apply the same public SDK inputs and call each
// original production session phase exactly once, with its unchanged flags.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Observation.h"
#include <dlfcn.h>

namespace {
std::ofstream camera;
unsigned frames=0;
bool initialized=false;
}
void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    camera_fixture::require(original!=nullptr,"Original camera UpdateWorld missing");
    if(!initialized) {
        camera_fixture::Apply();camera_fixture::CameraHeader(camera);
        initialized=true;
    }
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    camera_fixture::require(original!=nullptr,"Original camera EndTimeStep missing");
    original(services,time,running,active,force);
    camera_fixture::Camera(camera,++frames);
}
