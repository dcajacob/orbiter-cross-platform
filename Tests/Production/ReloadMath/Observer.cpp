// Licensed under the MIT License
// Diagnostic-only observer; no controls or simulator state setters.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "../../../Src/Orbiter/Production/MathObservation.h"
#include "TouchdownObservation.h"
#include "SurfaceObservation.h"
#ifdef ORBITER_RELOAD_INTERNAL_OBSERVATION
#include "InternalObservation.h"
#endif
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
#include <string>
namespace {
class Observer final : public oapi::Module {
    std::ofstream trace;
    std::ofstream touchdown;
    std::ofstream surface;
#ifdef ORBITER_RELOAD_INTERNAL_OBSERVATION
    std::ofstream internal;
#endif
    unsigned tick = 0;
    std::string target;
public:
    explicit Observer(HINSTANCE instance) : Module(instance), trace("reload-math.csv", std::ios::binary) {
        const char* selected = std::getenv("ORBITER_PHASE6_MATH_VESSEL");
        target = selected ? selected : "Atlantis";
        if (target.empty() || target.size() > 255) std::exit(1);
        trace.imbue(std::locale::classic());
        trace << std::setprecision(17);
        orbiter::production::math_observation::Header(trace);
        touchdown.open("touchdown-math.csv",std::ios::binary);
        touchdown.imbue(std::locale::classic());touchdown<<std::setprecision(17);
        reload_touchdown::Header(touchdown);
        surface.open("surface-math.csv",std::ios::binary);surface.imbue(std::locale::classic());
        surface<<std::setprecision(17);reload_surface::Header(surface);
#ifdef ORBITER_RELOAD_INTERNAL_OBSERVATION
        internal.open("internal-state.csv",std::ios::binary);internal.imbue(std::locale::classic());
        internal<<std::setprecision(17);reload_internal::Header(internal);
#endif
    }
    void clbkPreStep(double seconds, double, double) override {
        auto* vessel = oapiGetVesselInterface(oapiGetVesselByName(const_cast<char*>(target.c_str())));
        auto earth = oapiGetObjectByName(const_cast<char*>("Earth"));
        VECTOR3 position{}; MATRIX3 rotation{}, obliquity{};
        if (!vessel || !earth) std::exit(1);
        oapiGetGlobalPos(earth, &position);
        oapiGetRotationMatrix(earth, &rotation);
        oapiGetPlanetObliquityMatrix(earth, &obliquity);
        orbiter::production::math_observation::Row(trace, tick, seconds, *vessel,
            position, rotation, obliquity, oapiGetPlanetCurrentRotation(earth));
        reload_touchdown::Rows(touchdown,tick,seconds);
        reload_surface::Rows(surface,tick,seconds);
#ifdef ORBITER_RELOAD_INTERNAL_OBSERVATION
        reload_internal::Rows(internal,tick,seconds);
#endif
        ++tick;
        if (!trace || !touchdown) std::exit(1);
    }
};
Observer* observer = nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) { observer = new Observer(instance); oapiRegisterModule(observer); }
DLLCLBK void ExitModule(HINSTANCE) { delete observer; observer = nullptr; }
