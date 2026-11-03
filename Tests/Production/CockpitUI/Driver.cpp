// Licensed under the MIT License
// Observe the original application and route declared inputs through its window.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "imgui.h"
#include "imgui_internal.h"
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
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
std::string hex(const char* value) {
    static const char digits[] = "0123456789abcdef";
    std::string result;
    for (auto p = reinterpret_cast<const unsigned char*>(value); *p; ++p) {
        result += digits[*p >> 4]; result += digits[*p & 15];
    }
    return result;
}
class Driver final : public oapi::Module {
    struct Action { unsigned tick; std::string event; int x, y; std::string text; };
    SetObserver setter = nullptr;
    std::vector<Action> actions;
    std::ofstream state, events, inputs, ui, callbacks;
    HWND window = nullptr;
    unsigned frames = 0;
    int left = 1;
    bool initialized = false;
    bool started = false;
    int lastX = 0, lastY = 0;

    template<class F> void guarded(F action) {
        try { action(); }
        catch (const std::exception& e) {
            std::ofstream("cockpit-failure.txt") << e.what() << '\n';
            std::exit(42);
        }
    }
    static bool enter(void*, char* value, void* data) {
        auto* self = static_cast<Driver*>(data);
        self->callbacks << self->frames << ",enter," << hex(value) << '\n';
        self->callbacks.flush();
        return true;
    }
    static bool cancel(void*, char* value, void* data) {
        auto* self = static_cast<Driver*>(data);
        self->callbacks << self->frames << ",cancel," << hex(value) << '\n';
        self->callbacks.flush();
        return true;
    }
    ImGuiWindow* popup() {
        ImGuiWindow* found = nullptr;
        for (auto* candidate : GImGui->Windows) {
            if (candidate->Active && !candidate->Hidden && (candidate->Flags & ImGuiWindowFlags_Popup)) {
                require(!found, "Expected exactly one visible original popup");
                found = candidate;
            }
        }
        require(found != nullptr, "Required original popup is not visible");
        return found;
    }
    void mouse(int x, int y, UINT message) {
        require(x >= 0 && x < 1280 && y >= 0 && y < 720, "UI input lies outside the viewport");
        POINT point{x, y};
        require(ClientToScreen(window, &point) && SetCursorPos(point.x, point.y), "Cannot position original window cursor");
        SendMessageW(window, WM_MOUSEMOVE, 0, MAKELPARAM(x, y));
        if (message) SendMessageW(window, message, message == WM_LBUTTONDOWN ? MK_LBUTTON : 0, MAKELPARAM(x, y));
        lastX = x; lastY = y;
    }
    void act(const Action& action) {
        int x = action.x, y = action.y;
        if (action.event == "popup_down") {
            auto* actual = popup();
            x += int(actual->Pos.x); y += int(actual->Pos.y);
            mouse(x, y, WM_LBUTTONDOWN);
        } else if (action.event == "left_down") {
            mouse(x, y, WM_LBUTTONDOWN);
        } else if (action.event == "left_up") {
            x = lastX; y = lastY; mouse(x, y, WM_LBUTTONUP);
        } else if (action.event == "move") {
            mouse(x, y, 0);
        } else if (action.event == "text") {
            for (unsigned char c : action.text) SendMessageW(window, WM_CHAR, c, 1);
        } else if (action.event == "key_down" || action.event == "key_up") {
            const UINT scan = MapVirtualKeyW(x, MAPVK_VK_TO_VSC);
            LPARAM flags = 1 | (scan << 16);
            if (action.event == "key_up") flags |= LPARAM(3) << 30;
            SendMessageW(window, action.event == "key_down" ? WM_KEYDOWN : WM_KEYUP, x, flags);
        } else if (action.event == "open_input") {
            oapiOpenInputBoxEx("Reference input cancellation", enter, cancel, nullptr, 20, this);
        } else {
            require(false, "Unknown UI reference action");
        }
        inputs << frames << ',' << action.event << ',' << x << ',' << y << ',' << hex(action.text.c_str()) << '\n';
        inputs.flush();
    }
    void snapshot() {
        auto* vessel = oapiGetFocusInterface();
        require(vessel && std::string(vessel->GetName()) == "PB", "Original reference focus changed");
        VECTOR3 p{}, v{}, w{}; MATRIX3 r{};
        vessel->GetGlobalPos(p); vessel->GetGlobalVel(v); vessel->GetAngularVel(w); vessel->GetRotationMatrix(r);
        state << frames << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD()
              << ",PB," << vessel->GetClassName() << ',' << oapiCockpitMode() << ',' << oapiGetHUDMode()
              << ',' << oapiGetMFDMode(0) << ',' << oapiGetMFDMode(1);
        for (double value : {p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,w.x,w.y,w.z,vessel->GetMass(),vessel->GetFuelMass()}) state << ',' << value;
        state << ',' << vessel->GetMeshCount() << ',' << vessel->GetThrusterCount() << '\n';
        state.flush();
        auto& io = ImGui::GetIO();
        unsigned count = 0;
        for (auto* candidate : GImGui->Windows) {
            if (!candidate->Active || candidate->Hidden || !(candidate->Flags & ImGuiWindowFlags_Popup)) continue;
            ++count;
            ui << frames << ',' << hex(candidate->Name) << ',' << candidate->Pos.x << ',' << candidate->Pos.y
               << ',' << candidate->Size.x << ',' << candidate->Size.y << ',' << io.WantCaptureMouse << ',' << io.WantCaptureKeyboard << '\n';
        }
        if (!count) ui << frames << ",,0,0,0,0," << io.WantCaptureMouse << ',' << io.WantCaptureKeyboard << '\n';
        ui.flush();
    }
public:
    explicit Driver(HINSTANCE instance) : Module(instance) {
        guarded([&] {
            std::ifstream config("ui-case.txt");
            unsigned count = 0;
            require(bool(config >> left >> count) && count > 0 && count < 32, "Invalid UI schedule");
            for (unsigned i = 0; i < count; ++i) {
                Action action{};
                require(bool(config >> action.tick >> action.event >> action.x >> action.y >> action.text), "Incomplete UI schedule");
                if (action.text == "-") action.text.clear();
                actions.push_back(action);
            }
            for (auto* stream : {&state,&events,&inputs,&ui,&callbacks}) {
                stream->imbue(std::locale::classic());
                stream->exceptions(std::ios::badbit | std::ios::failbit);
            }
            state.open("cockpit-state.csv"); events.open("cockpit-events.csv"); inputs.open("ui-inputs.csv");
            ui.open("ui-state.csv"); callbacks.open("ui-callbacks.csv");
            state << std::setprecision(17); events << std::setprecision(17); ui << std::setprecision(17);
            state << "tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters\n";
            events << "tick,seconds,mjd,phase,object,running\n";
            inputs << "tick,event,x,y,text_hex\n";
            ui << "tick,popup_hex,x,y,width,height,capture_mouse,capture_keyboard\n";
            callbacks << "tick,event,text_hex\n";
            setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
            require(setter && setter(1, observe, 51982.5), "Original observation ABI missing");
            std::srand(0);
        });
    }
    ~Driver() override { if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN()); }
    void clbkSimulationStart(RenderMode mode) override {
        guarded([&] { require(mode != RENDER_NONE, "Original renderer required"); started = true; });
    }
    void clbkPreStep(double, double, double) override {
        guarded([&] {
            Sleep(120);
            if (!initialized) {
                IMGUI_CHECKVERSION();
                window = FindWindowA("Orbiter Render Window", nullptr);
                DWORD process = 0;
                require(window && GetWindowThreadProcessId(window, &process) && process == GetCurrentProcessId(), "Owned original render window missing");
                require(oapiCameraInternal() && oapiCockpitMode() == 1, "Original glass cockpit missing");
                oapiOpenMFD(left, 0); oapiOpenMFD(2, 1); oapiSetHUDMode(1);
                mouse(640, 360, 0);
                initialized = true; snapshot();
            }
            for (const auto& action : actions) if (action.tick == frames) act(action);
        });
    }
    void core(const char* phase, const char* object, double seconds, double mjd, int running) {
        guarded([&] {
            events << frames << ',' << seconds << ',' << mjd << ',' << phase << ',' << object << ',' << running << '\n';
            if (started && std::string(phase) == "app.frame.end") {
                require(initialized && running, "Unexpected UI reference frame state");
                ++frames; snapshot();
                if (frames == 50) require(oapiSaveScenario("UIResult", "Original UI reference result"), "Cannot save original instrument result");
            }
        });
    }
    void clbkSimulationEnd() override {
        guarded([&] { require(frames == 60, "Incomplete UI reference"); started = false; events.flush(); std::ofstream("cockpit-complete.txt") << frames << '\n'; });
    }
};
void observe(const char* phase, const char* object, double seconds, double mjd, int running) {
    if (driver) driver->core(phase, object, seconds, mjd, running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
