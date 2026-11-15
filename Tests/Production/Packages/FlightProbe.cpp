// Licensed under the MIT License
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"

#include <cstring>
#include <fstream>
#include <limits>
#include <string_view>

namespace {
using SetObserver = int (*)(unsigned, OrbiterTestObserver, double);
SetObserver setObserver = nullptr;
unsigned frames = 0;
bool started = false;
bool closeRequested = false;

void observe(const char* phase, const char*, double, double, int)
{
    if (!started || std::strcmp(phase, "app.frame.end") != 0) return;
    if (++frames != 48) return;
    HWND window = FindWindowA("Orbiter Render Window", nullptr);
    DWORD process = 0;
    auto* focus = oapiGetFocusInterface();
    std::ofstream result("launchpad-flight.txt");
    if (!window || !GetWindowThreadProcessId(window, &process) || process != GetCurrentProcessId() || !focus)
        return;
    result << "pid=" << process << "\nfocus=" << focus->GetName()
           << "\nclass=" << focus->GetClassName() << '\n';
    for (DWORD index = 0; index < oapiGetVesselCount(); ++index) {
        const auto vessel = oapiGetVesselInterface(oapiGetVesselByIndex(index));
        result << "vessel=" << vessel->GetName() << ':' << vessel->GetClassName() << '\n';
    }
    closeRequested = PostMessageW(window, WM_CLOSE, 0, 0) != FALSE;
    result << "close-requested=" << closeRequested << '\n';
}

class FlightProbe final : public oapi::Module {
public:
    explicit FlightProbe(HINSTANCE instance) : Module(instance) {}
    void clbkSimulationStart(RenderMode mode) override { started = mode != RENDER_NONE && setObserver; }
    void clbkSimulationEnd() override {
        if (started && closeRequested)
            std::ofstream("launchpad-flight-end.txt") << frames << '\n';
        started = false;
    }
};
FlightProbe* driver = nullptr;
}

DLLCLBK void InitModule(HINSTANCE instance)
{
    const auto symbol = GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver");
    const auto setter = reinterpret_cast<SetObserver>(symbol);
    if (setter && setter(1, observe, 51982.5)) setObserver = setter;
    driver = new FlightProbe(instance);
    oapiRegisterModule(driver);
}

DLLCLBK void ExitModule(HINSTANCE)
{
    if (setObserver) setObserver(1, nullptr, std::numeric_limits<double>::quiet_NaN());
    delete driver;
}
