// Licensed under the MIT License
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "XRSound.h"
#include "ScnEditor/resource.h"
#include "imgui.h"
#include "imgui_internal.h"

#include <CommCtrl.h>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {
using SetObserver = int (*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver* driver = nullptr;
void observe(const char*, const char*, double, double, int);

void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

HWND owned_window(const char* kind, const char* title)
{
    HWND window = FindWindowA(kind, title);
    DWORD pid = 0;
    return window && GetWindowThreadProcessId(window, &pid) && pid == GetCurrentProcessId() ? window : nullptr;
}

ImGuiWindow* find_gui(std::string_view title)
{
    for (auto* candidate : GImGui->Windows)
        if (candidate->Active && !candidate->Hidden && std::string_view(candidate->Name).find(title) != std::string_view::npos)
            return candidate;
    return nullptr;
}

HWND visible_page(HWND editor, int control)
{
    for (HWND page = GetWindow(editor, GW_CHILD); page; page = GetWindow(page, GW_HWNDNEXT))
        if (IsWindowVisible(page) && GetDlgItem(page, control)) return page;
    throw std::runtime_error("Expected scenario editor page is missing");
}

void press(HWND page, int id)
{
    auto item = GetDlgItem(page, id);
    require(item && IsWindowEnabled(item), "Expected scenario editor button is unavailable");
    SendMessageW(item, BM_CLICK, 0, 0);
}

void text(HWND page, int id, const char* value)
{
    auto item = GetDlgItem(page, id);
    require(item && SetWindowTextA(item, value), "Cannot populate scenario editor field");
}

HTREEITEM tree_item(HWND tree, HTREEITEM item, std::string_view name)
{
    for (; item; item = TreeView_GetNextSibling(tree, item)) {
        char label[256]{};
        TVITEMA value{};
        value.mask = TVIF_TEXT;
        value.hItem = item;
        value.pszText = label;
        value.cchTextMax = sizeof(label);
        require(SendMessageA(tree, TVM_GETITEMA, 0, reinterpret_cast<LPARAM>(&value)), "Cannot read vessel type tree");
        if (name == label) return item;
        if (auto child = tree_item(tree, TreeView_GetChild(tree, item), name)) return child;
    }
    return nullptr;
}

int vessel_row(HWND list, std::string_view name)
{
    const auto count = SendMessageW(list, LB_GETCOUNT, 0, 0);
    for (int i = 0; i < count; ++i) {
        char row[256]{};
        require(SendMessageA(list, LB_GETTEXTLEN, i, 0) < sizeof(row), "Unexpected vessel list text");
        SendMessageA(list, LB_GETTEXT, i, reinterpret_cast<LPARAM>(row));
        std::string_view value(row);
        if (value.substr(0, value.find('\t')) == name) return i;
    }
    return LB_ERR;
}

class Driver final : public oapi::Module {
    static constexpr int MainSound = XRSound::MainEngines;
    static constexpr int RcsSound = XRSound::RCSSustain;
    char vesselName[32] = "Phase7-ShuttlePB";
    char earthName[6] = "Earth";
    SetObserver setter = nullptr;
    std::ofstream events;
    std::string mode;
    HWND render = nullptr;
    unsigned frame = 0;
    bool started = false;
    bool evidence = false;
    bool held = false;
    double pause_time = 0;
    static constexpr double FixedStep = .0625;
    int x = 0, y = 0;
    std::unique_ptr<XRSound> sounds;

    template<class F> void guarded(F action) {
        try { action(); }
        catch (const std::exception& error) {
            std::ofstream("phase7-failure.txt") << mode << " frame " << frame << ": " << error.what() << '\n';
            std::exit(42);
        }
    }

    void record(const char* name) {
        events << frame << ',' << name << ',' << oapiGetPause() << ',' << oapiGetSimTime() << '\n';
        events.flush();
    }

    void mouse(UINT message) {
        POINT cursor{x, y};
        RECT client{};
        require(GetClientRect(render, &client) && x >= 0 && y >= 0 && x < client.right && y < client.bottom
                && ClientToScreen(render, &cursor) && SetCursorPos(cursor.x, cursor.y), "Cannot target rendered control");
        SendMessageW(render, WM_MOUSEMOVE, message == WM_LBUTTONDOWN ? MK_LBUTTON : 0, MAKELPARAM(x,y));
        if (message) SendMessageW(render, message, message == WM_LBUTTONDOWN ? MK_LBUTTON : 0, MAKELPARAM(x,y));
    }

    void click(ImGuiWindow* panel, int dx, int dy) {
        require(panel != nullptr, "Expected in-flight dialog is not visible");
        x = static_cast<int>(panel->Pos.x) + dx;
        y = static_cast<int>(panel->Pos.y) + dy;
        mouse(WM_LBUTTONDOWN);
        held = true;
    }

    void options() {
        if (frame == 6) {
            require(oapiSimulateBufferedKey(OAPI_KEY_F6), "Cannot deliver Options shortcut");
            record("options-key");
        }
        if (frame == 12 || frame == 18 || frame == 24 || frame == 30 || frame == 36) {
            auto panel = find_gui("Orbiter: Options");
            const int dx = frame == 30 ? 40 : frame == 36 ? 276 : 480;
            const int dy = frame == 18 ? 82 : frame == 24 ? 202 : 58;
            click(panel, dx, dy);
            record("options-click");
        }
        if (frame == 42) {
            require(find_gui("Orbiter: Options") != nullptr, "Options vanished prematurely");
            evidence = true;
        }
    }

    void save_editor(HWND editor, const char* filename) {
        press(visible_page(editor, IDC_SAVE), IDC_SAVE);
        auto page = visible_page(editor, IDOK);
        text(page, IDC_EDIT1, filename);
        press(page, IDOK);
        require(visible_page(editor, IDC_LIST1) != nullptr, "Editor did not complete save");
        record(filename);
    }

    void check_position(const char* event) {
        auto handle = oapiGetVesselByName(vesselName);
        require(handle != nullptr, "Edited vessel missing from the actual world");
        auto* vessel = oapiGetVesselInterface(handle);
        require(std::string_view(vessel->GetClassName()) == "ShuttlePB", "Edited vessel class differs");
        VECTOR3 r{}, v{};
        auto earth = oapiGetGbodyByName(earthName);
        require(earth != nullptr, "Earth reference missing");
        vessel->GetRelativePos(earth,r);
        vessel->GetRelativeVel(earth,v);
        require(std::abs(r.x-6801234.0) <= .01 && std::abs(r.y-200.0) <= .01 && std::abs(r.z-300.0) <= .01
             && std::abs(v.x-3.0) <= 1e-5 && std::abs(v.y+20.0) <= 1e-5 && std::abs(v.z-7600.0) <= 1e-5,
                "Edited position/velocity differs from the requested state");
        record(event);
    }

    void editor() {
        if (frame >= 6)
            require(oapiGetPause() && oapiGetSimTime()==FixedStep, "Editor advanced beyond the one Windows startup step");
        if (mode == "editor-removed") {
            if (frame == 10) {
                require(!oapiGetVesselByName(vesselName), "Deleted vessel reappeared after reload");
                record("deletion-reloaded");
                evidence = true;
            }
            return;
        }
        if (frame == 6) {
            DWORD ctrl[]{OAPI_KEY_LCONTROL};
            require(oapiSimulateBufferedKey(OAPI_KEY_F4,ctrl,1), "Cannot deliver Custom Functions shortcut");
        }
        if (frame == 14) {
            // ScnEditor is the only custom function in the isolated profile.
            auto panel = find_gui("Orbiter: Custom functions");
            require(panel != nullptr, "Custom Functions dialog did not open");
            // The cursor ends one item spacing after the single 20px command button.
            const int command_y = static_cast<int>(panel->DC.CursorPos.y - panel->Pos.y - GImGui->Style.ItemSpacing.y - 10);
            click(panel, 90, command_y);
            record("custom-function-click");
        }
        if (frame == 22) {
            auto window = owned_window("#32770","Scenario Editor");
            require(window != nullptr, "Classic scenario editor did not open");
            if (mode == "editor-first") {
                require(!oapiGetVesselByName(vesselName), "Test vessel already exists");
                press(visible_page(window,IDC_VESSELNEW),IDC_VESSELNEW);
                auto page = visible_page(window, IDC_VESSELTP);
                auto tree = GetDlgItem(page, IDC_VESSELTP);
                auto item = tree_item(tree, TreeView_GetRoot(tree), "ShuttlePB");
                require(item && TreeView_SelectItem(tree,item), "Cannot select stock ShuttlePB type");
                text(page, IDC_NAME, vesselName);
                SendMessageW(GetDlgItem(page,IDC_CAMERA),BM_SETCHECK,BST_UNCHECKED,0);
                press(page,IDC_CREATE);
                require(oapiGetVesselByName(vesselName) != nullptr, "Scenario editor did not create the vessel");
                record("created");
                press(visible_page(window,IDC_STATEVEC),IDC_STATEVEC);
                page = visible_page(window,IDC_FRM);
                text(page,IDC_REF,"Earth");
                text(page,IDC_EDIT1,"6801234"); text(page,IDC_EDIT2,"200"); text(page,IDC_EDIT3,"300");
                text(page,IDC_EDIT4,"3"); text(page,IDC_EDIT5,"-20"); text(page,IDC_EDIT6,"7600");
                press(page,IDC_APPLY);
                press(page,IDC_BACK);
                press(visible_page(window,IDC_STATEVEC),IDC_BACK);
            } else {
                auto page = visible_page(window,IDC_VESSELDEL);
                auto list = GetDlgItem(page,IDC_LIST1);
                int row = vessel_row(list, vesselName);
                require(row != LB_ERR && SendMessageW(list, LB_SETCURSEL, row, 0) == row, "Cannot select edited vessel");
                press(page,IDC_VESSELDEL);
                record("delete-click");
            }
        }
        if (frame == 34) {
            auto window = owned_window("#32770","Scenario Editor");
            require(window != nullptr, "Scenario editor disappeared");
            if (mode == "editor-first") {
                check_position("position-verified");
                save_editor(window,"Phase7Edited");
            } else {
                require(!oapiGetVesselByName(vesselName), "Scenario editor did not delete the vessel");
                save_editor(window,"Phase7Removed");
            }
            press(visible_page(window,IDC_LIST1),IDCANCEL);
            evidence = true;
        }
    }

    void audio() {
        auto* ship = oapiGetFocusInterface();
        require(ship && std::string_view(ship->GetName()) == "GL-01", "Unexpected XRSound focus vessel");
        if (frame == 12) {
            require(oapiCameraInternal(), "XRSound fixture must start in the cockpit");
            sounds.reset(XRSound::CreateInstance(ship));
            require(sounds && sounds->IsPresent(), "XRSound vessel interface unavailable");
            require(!sounds->IsWavPlaying(MainSound) && !sounds->IsWavPlaying(RcsSound), "Thrust audio started at idle");
            ship->SetThrusterGroupLevel(THGROUP_MAIN,1.0);
            record("main-on");
        }
        if (frame == 28) {
            require(sounds->IsWavPlaying(MainSound), "Default main engine sound did not play");
            pause_time=oapiGetSimTime();
            oapiSetPause(true);
            record("pause-requested");
        }
        if (frame == 34) {
            require(oapiGetPause() && oapiGetSimTime()==pause_time, "Simulation did not remain paused");
            record("sim-paused");
            oapiSetPause(false);
        }
        if (frame == 48) {
            require(!oapiGetPause() && sounds->IsWavPlaying(MainSound), "Engine voice did not resume");
            record("main-resumed");
            ship->SetThrusterGroupLevel(THGROUP_MAIN,0.0);
            ship->SetThrusterGroupLevel(THGROUP_ATT_PITCHUP,1.0);
        }
        if (frame == 64) {
            require(!sounds->IsWavPlaying(MainSound) && sounds->IsWavPlaying(RcsSound), "RCS voice failed or engine voice stuck");
            record("rcs-playing");
            ship->SetThrusterGroupLevel(THGROUP_ATT_PITCHUP,0.0);
        }
        if (frame == 83) {
            require(!sounds->IsWavPlaying(MainSound) && !sounds->IsWavPlaying(RcsSound), "Thrust voice stuck after return to idle");
            record("thrust-idle");
            if (mode == "audio-first")
                require(oapiSaveScenario("Phase7Audio", "Windows XRSound reload check"), "Cannot save XRSound test scenario");
            evidence = true;
        }
    }

public:
    explicit Driver(HINSTANCE instance) : Module(instance) {
        guarded([&] {
            std::ifstream input("phase7-mode.txt");
            require(bool(input >> mode), "Missing Phase 7 test profile");
            events.open("phase7-events.csv");
            events << std::setprecision(17) << "frame,event,paused,seconds\n";
            setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));
            require(setter && setter(1,observe,51982.5), "Orbiter observer ABI unavailable");
        });
    }
    ~Driver() override {
        if (setter) setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());
    }
    void clbkSimulationStart(RenderMode mode) override {
        guarded([&] {
            require(mode != RENDER_NONE, "Rendered Windows session required");
            if (this->mode == "editor-reload") {
                require(oapiGetSimTime() == 0, "Reload must be checked before the paused-start initialization step");
                check_position("position-restored-before-startup-step");
            }
            started = true;
        });
    }
    void clbkSimulationEnd() override {
        guarded([&] {
            require(evidence, "Phase 7 test ended before observing its goal");
            sounds.reset();
            std::ofstream("phase7-complete.txt") << mode << ' ' << frame << '\n';
            started=false;
        });
    }
    void after_frame(bool running) {
        guarded([&] {
            if (!started) return;
            // Windows initializes the world with one step before requesting start paused.
            if (!frame && mode.find("audio-")!=0 && running) {
                require(oapiGetSimTime()==FixedStep, "Unexpected first Windows initialization step");
                return;
            }
            ++frame;
            if (frame==1) {
                IMGUI_CHECKVERSION();
                render = owned_window("Orbiter Render Window",nullptr);
                require(render && GImGui, "Owned Windows render context unavailable");
            }
            if (held) {
                mouse(WM_LBUTTONUP);
                held=false;
                return;
            }
            if (mode.find("options-")==0) options();
            else if (mode.find("editor-")==0) editor();
            else if (mode.find("audio-")==0) audio();
            else require(false, "Unknown Phase 7 test profile");
        });
    }
};

void observe(const char* phase, const char*, double, double, int running)
{
    if (driver && std::string_view(phase)=="app.frame.end") driver->after_frame(running != 0);
}
}

DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
