// Licensed under the MIT License
// SDK inputs and read-only observations of the preserved original application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using SetObserver = int(*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver* driver = nullptr;
void observe(const char*, const char*, double, double, int);
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }

class Driver final : public oapi::Module {
    struct Key { unsigned tick; DWORD code; bool control; };
    SetObserver setter = nullptr;
    std::vector<Key> keys;
    std::ofstream state, animations, inputs;
    unsigned frames = 0, total = 0;
    int cockpit = 0, previousFma = -1;
    bool started = false, initialized = false;

    template<class F> void guarded(F action) {
        try { action(); }
        catch (const std::exception& e) {
            std::ofstream("cockpit-failure.txt") << e.what() << '\n';
            std::exit(42);
        }
    }
    void snapshot() {
        auto* vessel = oapiGetFocusInterface();
        require(vessel && std::string(vessel->GetName()) == "DG", "Original DG focus missing");
        require(oapiCameraInternal() && oapiCockpitMode() == cockpit, "Original DG cockpit missing");
        VECTOR3 p{}, v{}, w{}; MATRIX3 r{};
        vessel->GetGlobalPos(p); vessel->GetGlobalVel(v); vessel->GetAngularVel(w); vessel->GetRotationMatrix(r);
        state << frames << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD()
              << ",DG," << vessel->GetClassName() << ',' << oapiCockpitMode() << ',' << oapiGetHUDMode()
              << ',' << oapiGetMFDMode(0) << ',' << oapiGetMFDMode(1);
        for (double value : {p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,w.x,w.y,w.z,vessel->GetMass(),vessel->GetFuelMass()}) state << ',' << value;
        state << ',' << vessel->GetMeshCount() << ',' << vessel->GetThrusterCount() << '\n';
        // Actual stock mechanism animation handles in shared construction order.
        for (unsigned index : {4u,7u,11u,12u,13u,16u,17u}) {
            const double value = vessel->GetAnimation(index);
            require(std::isfinite(value) && value >= 0 && value <= 1, "Original mechanism animation missing");
            animations << frames << ",DG," << index << ',' << value << '\n';
        }
        state.flush(); animations.flush();
    }
public:
    explicit Driver(HINSTANCE instance) : Module(instance) {
        guarded([&] {
            if (std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
                previousFma = _get_FMA3_enable(); _set_FMA3_enable(0);
                require(_get_FMA3_enable() == 0, "Original SSE2 profile not selected");
            }
            std::ofstream("math-profile.txt") << (_get_FMA3_enable() ? "fma3" : "sse2") << '\n';
            unsigned count = 0;
            std::ifstream config("systems-case.txt");
            require(bool(config >> total >> cockpit >> count) && total > 0 && total <= 240 &&
                    cockpit >= 2 && cockpit <= 3 && count <= 8, "Invalid systems schedule");
            for (unsigned i = 0; i < count; ++i) {
                Key key{};
                require(bool(config >> key.tick >> key.code >> key.control) && key.tick < total &&
                        key.code > 0 && key.code < 256, "Invalid systems key input");
                keys.push_back(key);
            }
            for (auto* stream : {&state,&animations,&inputs}) {
                stream->imbue(std::locale::classic());
                stream->exceptions(std::ios::badbit | std::ios::failbit);
            }
            state.open("cockpit-state.csv"); animations.open("flight-animations.csv"); inputs.open("system-inputs.csv");
            state << std::setprecision(17); animations << std::setprecision(17);
            state << "tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters\n";
            animations << "tick,object,index,state\n"; inputs << "tick,key,control\n";
            setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
            require(setter && setter(1, observe, 51982.5), "Original observation ABI missing");
            std::srand(0);
        });
    }
    ~Driver() override {
        if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN());
        if (previousFma >= 0) _set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode) override {
        guarded([&] { require(mode != RENDER_NONE, "Original graphics client required"); started = true; });
    }
    void clbkPreStep(double, double, double) override {
        guarded([&] {
            if (!initialized) { initialized = true; snapshot(); }
            for (const auto& key : keys) if (key.tick == frames) {
                DWORD control = OAPI_KEY_LCONTROL;
                require(oapiSimulateBufferedKey(key.code, key.control ? &control : nullptr,
                                               key.control ? 1 : 0), "Original buffered key dispatch failed");
                inputs << frames << ',' << key.code << ',' << key.control << '\n'; inputs.flush();
            }
        });
    }
    void core(const char* phase, int running) {
        guarded([&] {
            if (started && std::string(phase) == "app.frame.end") {
                require(initialized && running, "Unexpected original systems frame state");
                ++frames; snapshot();
                if (frames == total)
                    require(oapiSaveScenario("SystemsResult", "Original DG systems result"), "Original systems save failed");
            }
        });
    }
    void clbkSimulationEnd() override {
        guarded([&] {
            require(frames == total, "Incomplete original systems run"); started = false;
            std::ofstream("cockpit-complete.txt") << frames << '\n';
        });
    }
};
void observe(const char* phase, const char*, double, double, int running) {
    if (driver) driver->core(phase, running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
