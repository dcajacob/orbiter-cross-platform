// Licensed under the MIT License
// Observe real callback inputs, then forward every argument to the original body.
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <stdexcept>

namespace {
// Keep this process-only observer out of sandboxed GTK image-loader children.
struct ProcessPreload { ProcessPreload() { unsetenv("LD_PRELOAD"); } } processPreload;
}

extern "C" void ObserveTankPostStep(VESSEL2*, double, double, double)
    asm("_ZN13Atlantis_Tank12clbkPostStepEddd");

extern "C" void ObserveTankPostStep(VESSEL2* tank, double simt, double simdt, double mjd)
{
    using Callback = void (*)(VESSEL2*, double, double, double);
    // Keep the implementation in its real RTLD_LOCAL module scope. Preloading
    // it globally would interpose unrelated stock modules' g_Param globals.
    static auto original = [] {
        const char* path = std::getenv("ORBITER_ATLANTIS_PROBE_LIBRARY");
        void* library = path ? dlopen(path, RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD) : nullptr;
        if (!library) throw std::runtime_error("Actual local Atlantis implementation missing");
        auto callback = reinterpret_cast<Callback>(dlsym(library,
            "_ZN13Atlantis_Tank12clbkPostStepEddd"));
        dlclose(library);
        if (!callback || callback == ObserveTankPostStep)
            throw std::runtime_error("Actual Atlantis tank post-step callback missing");
        return callback;
    }();
    static std::ofstream observations;
    if (!observations.is_open()) {
        observations.open("tank-post-step.csv");
        observations.exceptions(std::ios::badbit | std::ios::failbit);
        observations << std::setprecision(17) << "seconds,object,altitude_mean,orbiter\n";
    }
    const auto orbiter = tank->GetDockStatus(tank->GetDockHandle(0));
    observations << simt << ',' << tank->GetName() << ',' << tank->GetAltitude() << ','
                 << (orbiter ? oapiGetVesselInterface(orbiter)->GetName() : "") << '\n';
    observations.flush();
    original(tank, simt, simdt, mjd);
}
