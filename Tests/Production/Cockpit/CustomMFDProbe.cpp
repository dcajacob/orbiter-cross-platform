// Licensed under the MIT License
// Exercise the public user-mode ABI on the real native Pane and Sketchpad.
#include "MFDAPI.h"
#include "Production/NativeGraphics.h"
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace {
int mode;
void event(const char* name)
{
    std::ofstream(orbiter::production::GetNativeRenderContext().evidence / "custom-mfd-events.txt",
                  std::ios::app) << name << '\n';
}
class ProbeMFD final : public MFD2 {
public:
    using MFD2::MFD2;
    ~ProbeMFD() override { event("destroy"); }
    char* ButtonLabel(int button) override {
        static char label[] = "TST";
        return button == 0 ? label : nullptr;
    }
    bool ConsumeButton(int button, int input) override {
        if (button != 0 || input != PANEL_MOUSE_LBDOWN) return false;
        event("button"); InvalidateDisplay(); return true;
    }
    bool ConsumeKeyBuffered(oapi::UInt32 key) override {
        if (key != 0x14) return false; // stock T scan code
        event("key"); return true;
    }
    bool Update(oapi::Sketchpad* pad) override {
        Title(pad, "Module SDK draw");
        pad->SetFont(GetDefaultFont(0));
        pad->SetPen(GetDefaultPen(0));
        pad->SetTextColor(GetDefaultColour(0));
        if (!pad->Text(12, 35, "MFD2", 4)) throw std::runtime_error("MFD2 Sketchpad draw failed");
        event("draw"); return true;
    }
    void RecallStatus() override { event("recall"); }
    void StoreStatus() const override { event("store"); }
    void WriteStatus(FILEHANDLE file) const override {
        *static_cast<std::ostream*>(file) << "  PROBE saved\n";
        event("save");
    }
};

oapi::CockpitMessageResult message(oapi::UInt msg, oapi::UInt display, oapi::CockpitUnsignedParam wp, oapi::CockpitSignedParam lp)
{
    if (display != 0) throw std::runtime_error("Custom mode opened on the wrong display");
    if (msg == OAPI_MSG_MFD_OPENEDEX) {
        auto* dimensions = reinterpret_cast<const MFDMODEOPENSPEC*>(wp);
        if (!dimensions->w || !dimensions->h) throw std::runtime_error("Missing custom display dimensions");
        event("open_extended");
    } else if (msg == OAPI_MSG_MFD_OPENED) {
        // Exercise Orbiter's compatible packed-dimension open fallback.
        event("open_packed");
        return reinterpret_cast<oapi::CockpitMessageResult>(
            new ProbeMFD(wp & 0xffff, (wp >> 16) & 0xffff, reinterpret_cast<VESSEL*>(lp)));
    } else if (msg == OAPI_MSG_MFD_CLOSED) {
        event("close");
        if (!oapiUnregisterMFDMode(mode)) throw std::runtime_error("Custom mode not registered at close");
    }
    return 0;
}
}

void OpenCustomMFDProbe()
{
    static char name[] = "SDK Probe";
    MFDMODESPECEX spec{name, 0, nullptr, message};
    mode = oapiRegisterMFDMode(spec);
    MFDMODESPECEX* registered = nullptr;
    if (oapiGetMFDModeSpecEx(name, &registered) != mode || !registered || registered->msgproc != message)
        throw std::runtime_error("MFD registration failed");
    oapiOpenMFD(mode, 0);
    auto* label = oapiMFDButtonLabel(0, 0);
    if (oapiGetMFDMode(0) != mode || !label || std::strcmp(label, "TST") ||
        !oapiProcessMFDButton(0, 0, PANEL_MOUSE_LBDOWN) || !oapiSendMFDKey(0, 0x14))
        throw std::runtime_error("Custom MFD did not receive its SDK input");
}
