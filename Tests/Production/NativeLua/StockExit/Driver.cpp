// Licensed under the MIT License
// Observes the untouched script and full scene in the preserved application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "../../StockVessels/Observation.h"
#include <tlhelp32.h>
#include <cstdlib>
#include <filesystem>
#include <limits>

namespace {
using SetObserver = int(*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver *driver = nullptr;
void observe(const char *, const char *, double, double, int);

void modules()
{
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId());
    stock_vessels::require(snapshot != INVALID_HANDLE_VALUE, "Cannot inspect original Lua exit DLLs");
    MODULEENTRY32W module{}; module.dwSize = sizeof(module);
    if (!Module32FirstW(snapshot, &module)) {
        CloseHandle(snapshot);
        throw std::runtime_error("Empty original Lua exit DLL list");
    }
    std::ofstream output("renderer-modules.txt");
    do { output << std::filesystem::path(module.szExePath).generic_u8string() << '\n'; }
    while (Module32NextW(snapshot, &module));
    CloseHandle(snapshot);
}

class Driver final : public oapi::Module {
    SetObserver setter = nullptr;
    std::ofstream state, docks, phases;
    unsigned frames = 0;
    int previousFma = -1;
    bool started = false, initialized = false;
    template<class F> void guarded(F action) {
        try { action(); }
        catch (const std::exception& error) {
            std::ofstream("stock-exit-failure.txt") << error.what() << '\n';
            std::exit(42);
        }
    }
public:
    explicit Driver(HINSTANCE instance) : Module(instance) { guarded([&] {
        if (std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
            previousFma = _get_FMA3_enable(); _set_FMA3_enable(0);
            stock_vessels::require(_get_FMA3_enable() == 0, "Original SSE2 profile was not selected");
        }
        std::ofstream("math-profile.txt") << (_get_FMA3_enable() ? "fma3" : "sse2") << '\n';
        stock_vessels::headers(state, docks);
        stock_vessels::open(phases, "stock-exit-phases.csv", "completed_frames,phase");
        setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
        stock_vessels::require(setter && setter(1, observe, 51982.5), "Preserved observer ABI missing");
        std::srand(0);
    }); }
    ~Driver() override {
        if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN());
        if (previousFma >= 0) _set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode) override { guarded([&] {
        stock_vessels::require(mode != RENDER_NONE, "Original graphics required"); started = true;
    }); }
    void clbkPreStep(double, double, double) override { guarded([&] {
        Sleep(120);
        if (!initialized) {
            modules(); stock_vessels::snapshot(state, docks, 0); initialized = true;
        }
    }); }
    void core(const char *phase, int running) { guarded([&] {
        if (started && std::string(phase) == "app.frame.end") {
            stock_vessels::require(initialized && running && frames < 60, "Unexpected original exit frame state");
            stock_vessels::snapshot(state, docks, ++frames);
            phases << frames << ',' << phase << '\n'; phases.flush();
        }
    }); }
    void clbkSimulationEnd() override {
        std::ofstream("stock-exit-normal-end.txt") << frames << '\n'; started = false;
    }
};
void observe(const char *phase, const char *, double, double, int running) {
    if (driver) driver->core(phase, running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
