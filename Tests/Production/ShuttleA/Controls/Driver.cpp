// Licensed under the MIT License
// Public SDK inputs and observations in the preserved Windows application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "Observation.h"
#include <tlhelp32.h>
#include <cstdlib>
#include <filesystem>
#include <limits>
#include <vector>

namespace {
using namespace shuttle_a_controls;
using SetObserver = int(*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver* driver = nullptr;
void observe(const char*, const char*, double, double, int);
void modules() {
    // Short persistence runs finish before the renderer's tick-50 inventory.
    struct Snapshot {
        HANDLE handle = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32, GetCurrentProcessId());
        ~Snapshot() { if (handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
    } snapshot;
    require(snapshot.handle != INVALID_HANDLE_VALUE, "Cannot inspect original controls DLLs");
    MODULEENTRY32W module{}; module.dwSize = sizeof(module);
    require(Module32FirstW(snapshot.handle, &module) != 0, "Original controls DLL list is empty");
    std::ofstream output("renderer-modules.txt");
    output.exceptions(std::ios::badbit|std::ios::failbit);
    do { output << std::filesystem::path(module.szExePath).generic_u8string() << '\n'; }
    while (Module32NextW(snapshot.handle, &module));
}
class Driver final : public oapi::Module {
    struct Key { unsigned tick; DWORD code; bool control; };
    SetObserver setter = nullptr;
    std::ofstream state, docks, cockpit, animations, attachments, inputs;
    std::vector<Key> keys;
    unsigned frames = 0, total = 0;
    int previousFma = -1;
    bool started = false, initialized = false;
    template<class F> void guarded(F action) {
        try { action(); }
        catch (const std::exception& error) {
            std::ofstream("shuttle-a-failure.txt") << error.what() << '\n';
            std::exit(42);
        }
    }
public:
    explicit Driver(HINSTANCE instance) : Module(instance) { guarded([&] {
        if (std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
            previousFma = _get_FMA3_enable(); _set_FMA3_enable(0);
            require(_get_FMA3_enable() == 0, "Original SSE2 profile was not selected");
        }
        std::ofstream("math-profile.txt") << (_get_FMA3_enable() ? "fma3" : "sse2") << '\n';
        unsigned count = 0;
        std::ifstream config("shuttle-a-controls.txt");
        require(bool(config >> total >> count) && total > 0 && total <= 240 && count <= 16,
                "Invalid Shuttle-A controls schedule");
        for (unsigned i = 0; i < count; ++i) {
            Key key{};
            require(bool(config >> key.tick >> key.code >> key.control) && key.tick < total &&
                    key.code > 0 && key.code < 256, "Invalid Shuttle-A key input");
            keys.push_back(key);
        }
        headers(state, docks, cockpit, animations, attachments);
        stock_vessels::open(inputs, "shuttle-a-inputs.csv", "tick,key,control");
        setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
        require(setter && setter(1, observe, 51982.5), "Preserved observation ABI missing");
        std::srand(0);
    }); }
    ~Driver() override {
        if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN());
        if (previousFma >= 0) _set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode) override { guarded([&] {
        require(mode != RENDER_NONE, "Original graphics client required"); started = true;
    }); }
    void clbkPreStep(double, double, double) override { guarded([&] {
        Sleep(120); // Same instrument-refresh pacing as accepted stock captures.
        if (!initialized) { modules(); snapshot(state,docks,cockpit,animations,attachments,0); initialized = true; }
        for (const auto& key : keys) if (key.tick == frames) {
            DWORD control = OAPI_KEY_LCONTROL;
            require(oapiSimulateBufferedKey(key.code, key.control ? &control : nullptr,
                                           key.control ? 1 : 0), "Original key dispatch failed");
            inputs << frames << ',' << key.code << ',' << key.control << '\n'; inputs.flush();
        }
    }); }
    void core(const char* phase, int running) { guarded([&] {
        if (started && std::string(phase) == "app.frame.end") {
            require(initialized && running && frames < total, "Unexpected original controls frame state");
            snapshot(state,docks,cockpit,animations,attachments,++frames);
            if (frames == total)
                require(oapiSaveScenario("ShuttleAControlsResult", "Original Shuttle-A controls result"),
                        "Original controls save failed");
        }
    }); }
    void clbkSimulationEnd() override { guarded([&] {
        require(frames == total, "Incomplete original controls run"); started = false;
        std::ofstream("shuttle-a-complete.txt") << frames << '\n';
    }); }
};
void observe(const char* phase, const char*, double, double, int running) {
    if (driver) driver->core(phase, running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
