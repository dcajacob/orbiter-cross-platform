// Licensed under the MIT License
// Extra read-only observer: forward the real native session end before reading.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "TimeData.h"
#include "TouchdownObservation.h"
#include "InternalObservation.h"
#include "SurfaceObservation.h"
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <locale>
namespace {
unsigned tick=0;
std::ofstream& trace() {
    static std::ofstream out=[] {
        std::ofstream result("touchdown-math.csv",std::ios::binary);
        result.imbue(std::locale::classic());result<<std::setprecision(17);
        reload_touchdown::Header(result);return result;
    }();
    return out;
}
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    if(!original)throw std::runtime_error("Actual original session end missing");
    original(services,time,running,active,force);
    reload_touchdown::Rows(trace(),++tick,time.SimT0);
    static std::ofstream internal=[] {
        std::ofstream result("internal-state.csv",std::ios::binary);
        result.imbue(std::locale::classic());result<<std::setprecision(17);
        reload_internal::Header(result);return result;
    }();
    reload_internal::Rows(internal,tick,time.SimT0);
    static std::ofstream surface=[] {
        std::ofstream result("surface-math.csv",std::ios::binary);
        result.imbue(std::locale::classic());result<<std::setprecision(17);
        reload_surface::Header(result);return result;
    }();
    reload_surface::Rows(surface,tick,time.SimT0);
}
