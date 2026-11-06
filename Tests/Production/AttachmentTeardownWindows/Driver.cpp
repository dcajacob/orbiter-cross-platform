// Licensed under the MIT License. Current Windows normal-cleanup lifetime gate.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <commctrl.h>
#include <tlhelp32.h>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _DEBUG
#include <crtdbg.h>
#endif

namespace {
constexpr UINT NextWorld = WM_APP + 71, Finish = WM_APP + 72;
constexpr int LaunchButton = 1000, ScenarioTree = 1090;
using SetObserver = int(*)(unsigned, OrbiterTestObserver, double);
class Driver;
Driver* driver = nullptr;
void observe(const char*, const char*, double, double, int);
LRESULT CALLBACK controlProcedure(HWND, UINT, WPARAM, LPARAM);
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

class Driver final : public oapi::Module {
    HINSTANCE instance;
    HWND control = nullptr;
    SetObserver setter = nullptr;
    unsigned requested = 0, targetFrames = 0, worlds = 0, completed = 0, frames = 0;
    int previousFma = -1;
    bool started = false;
    std::string scene, math;
    std::ofstream states, events;
    static BOOL CALLBACK findLaunchpad(HWND window, LPARAM data) {
        auto* found = reinterpret_cast<std::vector<HWND>*>(data);
        HWND button = GetDlgItem(window, LaunchButton);
        if (button) {
            char label[128]{}; GetWindowTextA(button, label, sizeof label);
            if (std::string(label) == "&Launch Orbiter") found->push_back(window);
        }
        return TRUE;
    }
    static BOOL CALLBACK findTree(HWND window, LPARAM data) {
        if (GetDlgCtrlID(window) == ScenarioTree) {
            char name[64]{}; GetClassNameA(window, name, sizeof name);
            if (std::string(name) == "SysTreeView32") *reinterpret_cast<HWND*>(data) = window;
        }
        return TRUE;
    }
    HWND launchpad() {
        std::vector<HWND> found;
        require(EnumThreadWindows(GetCurrentThreadId(), findLaunchpad, reinterpret_cast<LPARAM>(&found)) != FALSE,
                "Cannot enumerate this process's launchpad");
        require(found.size() == 1, "Exactly one actual launchpad is required");
        return found.front();
    }
    void selectOriginal(HWND pad) {
        HWND tree = nullptr; EnumChildWindows(pad, findTree, reinterpret_cast<LPARAM>(&tree));
        require(tree != nullptr, "Actual scenario tree missing");
        std::string remaining = scene;
        require(remaining.size() > 4 && remaining.substr(remaining.size()-4) == ".scn", "Original scenario suffix differs");
        remaining.resize(remaining.size()-4);
        HTREEITEM parent = nullptr, selected = nullptr;
        while (!remaining.empty()) {
            auto slash = remaining.find('/');
            std::string part = remaining.substr(0, slash);
            HTREEITEM item = reinterpret_cast<HTREEITEM>(SendMessageA(tree, TVM_GETNEXTITEM,
                parent ? TVGN_CHILD : TVGN_ROOT, reinterpret_cast<LPARAM>(parent)));
            selected = nullptr;
            while (item) {
                char label[256]{}; TVITEMA value{};
                value.mask = TVIF_TEXT; value.hItem = item; value.pszText = label; value.cchTextMax = sizeof label;
                require(SendMessageA(tree, TVM_GETITEMA, 0, reinterpret_cast<LPARAM>(&value)) != FALSE, "Cannot inspect actual scenario item");
                if (part == label) { selected = item; break; }
                item = reinterpret_cast<HTREEITEM>(SendMessageA(tree, TVM_GETNEXTITEM, TVGN_NEXT, reinterpret_cast<LPARAM>(item)));
            }
            require(selected != nullptr, "Original scenario not present in the actual launchpad tree");
            parent = selected;
            if (slash == std::string::npos) remaining.clear(); else remaining.erase(0, slash+1);
        }
        require(SendMessageA(tree, TVM_SELECTITEM, TVGN_CARET, reinterpret_cast<LPARAM>(selected)) != FALSE,
                "Original scenario selection failed");
        events << worlds << ',' << frames << ",selected-original," << scene << '\n'; events.flush();
    }
    static unsigned linked(VESSEL* vessel, OBJHANDLE other, bool parent) {
        unsigned count = 0;
        for (unsigned i = 0; i < vessel->AttachmentCount(parent); ++i)
            if (vessel->GetAttachmentStatus(vessel->GetAttachmentHandle(parent, i)) == other) ++count;
        return count;
    }
    static unsigned docked(VESSEL* vessel, OBJHANDLE other) {
        unsigned count = 0;
        for (unsigned i = 0; i < vessel->DockCount(); ++i)
            if (vessel->GetDockStatus(vessel->GetDockHandle(i)) == other) ++count;
        return count;
    }
    void snapshot() {
        require(oapiGetPause() && oapiGetSimTime() == 0.0, "Paused world advanced its physics clock");
        require(oapiGetVesselCount() == 3, "Complete original three-vessel world required");
        OBJHANDLE iss = oapiGetVesselByName("ISS"), shuttle = oapiGetVesselByName("STS-101"), payload = oapiGetVesselByName("Leonardo");
        require(iss && shuttle && payload, "Original attachment roster differs");
        auto* iv = oapiGetVesselInterface(iss); auto* sv = oapiGetVesselInterface(shuttle); auto* pv = oapiGetVesselInterface(payload);
        require(iv && sv && pv, "Original public vessel interface missing");
        require(docked(iv, shuttle) == 1 && docked(sv, iss) == 1, "Original reciprocal ISS docking lost");
        require(linked(sv, payload, false) == 1 && linked(pv, shuttle, true) == 1, "Original reciprocal payload attachments lost");
        const std::map<std::string, std::string> expected{{"ISS","ProjectAlpha_ISS"},{"STS-101","Atlantis"},{"Leonardo","Leonardo_mplm"}};
        std::map<std::string, std::string> actual;
        for (unsigned i = 0; i < oapiGetVesselCount(); ++i) {
            auto* v = oapiGetVesselInterface(oapiGetVesselByIndex(i)); require(v, "Missing vessel interface");
            actual.emplace(v->GetName(), v->GetClassName()); VECTOR3 p{}, velocity{};
            v->GetGlobalPos(p); v->GetGlobalVel(velocity);
            for (double value : {p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,v->GetMass(),v->GetFuelMass(),oapiGetSimMJD()})
                require(std::isfinite(value), "Nonfinite paused vessel state");
            states << worlds << ',' << frames << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD() << ','
                   << v->GetName() << ',' << v->GetClassName() << ',' << p.x << ',' << p.y << ',' << p.z << ','
                   << velocity.x << ',' << velocity.y << ',' << velocity.z << ',' << v->GetMass() << ',' << v->GetFuelMass()
                   << ",1,1,1,1\n";
        }
        require(actual == expected, "A complete original vessel class was replaced"); states.flush();
    }
    void loadedModules() {
        HANDLE list = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId());
        require(list != INVALID_HANDLE_VALUE, "Cannot inspect actual lifetime-process modules");
        std::ofstream output("attachment-loaded-modules-world-" + std::to_string(worlds) + ".txt");
        MODULEENTRY32W item{}; item.dwSize = sizeof item;
        require(Module32FirstW(list, &item) != FALSE, "Actual lifetime module snapshot is empty");
        do { output << std::filesystem::path(item.szExePath).generic_u8string() << '\n'; }
        while (Module32NextW(list, &item));
        CloseHandle(list);
    }
    void heap() {
        require(HeapValidate(GetProcessHeap(), 0, nullptr) != FALSE, "Windows process heap corruption");
#ifdef _DEBUG
        require(_CrtCheckMemory() != FALSE, "Debug CRT heap corruption");
#endif
    }
public:
    template<class F> void guarded(F action) {
        try { action(); } catch (const std::exception& error) {
            std::ofstream("attachment-failure.txt") << error.what() << std::endl; std::exit(42);
        }
    }
    explicit Driver(HINSTANCE handle) : Module(handle), instance(handle) { guarded([&] {
        std::ifstream input("attachment-case.txt");
        require(bool(input >> requested >> targetFrames >> math), "Invalid lifetime request");
        input.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); std::getline(input, scene);
        if (!scene.empty() && scene.back() == '\r') scene.pop_back();
        require(requested >= 1 && requested <= 20 && targetFrames == 60, "Unsupported world/frame scope");
        require(scene == "Space Shuttle Atlantis/Atlantis ISS Resupply.scn", "Unchanged original entry point required");
        require(math == "automatic" || math == "sse2", "Unknown CRT profile");
        previousFma = _get_FMA3_enable(); if (math == "sse2") _set_FMA3_enable(0);
        require(math != "sse2" || !_get_FMA3_enable(), "Actual SSE2 selection failed");
        std::ofstream("attachment-math.txt") << (_get_FMA3_enable() ? "fma3" : "sse2") << '\n';
        for (auto* stream : {&states, &events}) { stream->imbue(std::locale::classic()); stream->exceptions(std::ios::badbit|std::ios::failbit); *stream << std::setprecision(17); }
        states.open("attachment-vessels.csv");
        states << "world,frame,seconds,mjd,object,class,x,y,z,vx,vy,vz,mass,fuel,paused,iss_dock,shuttle_child,payload_parent\n";
        events.open("attachment-events.csv"); events << "world,frame,event,detail\n";
        setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
        require(setter && setter(1, observe, std::numeric_limits<double>::quiet_NaN()), "Current observation ABI missing");
        WNDCLASSA type{}; type.lpfnWndProc = controlProcedure; type.hInstance = instance; type.lpszClassName = "OrbiterAttachedLifetimeControl";
        require(RegisterClassA(&type) != 0, "Cannot create private lifetime command class");
        control = CreateWindowExA(0, type.lpszClassName, "", 0, 0, 0, 0, 0, HWND_MESSAGE, nullptr, instance, nullptr);
        require(control != nullptr, "Cannot create lifetime command window"); heap();
    }); }
    ~Driver() override {
        if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN());
        if (control) DestroyWindow(control);
        UnregisterClassA("OrbiterAttachedLifetimeControl", instance);
        if (previousFma >= 0) _set_FMA3_enable(previousFma);
        std::ofstream("attachment-driver-unloaded.txt") << completed << '\n';
    }
    void clbkSimulationStart(RenderMode mode) override { guarded([&] {
        require(!started && worlds == completed && worlds < requested && mode != RENDER_NONE, "Unexpected actual world start");
        ++worlds; frames = 0; started = true; heap();
        require(oapiGetSimTime() == 0.0, "Actual original world did not start at time zero");
        oapiSetPause(true); // Before the first BeginTimeStep; StartPaused remains FALSE.
        events << worlds << ",0,start-pause-request,0\n"; events.flush();
    }); }
    void clbkPreStep(double, double, double) override { guarded([] { require(false, "Paused lifetime world performed a physics pre-step"); }); }
    void core(const char* phase, int running) { guarded([&] {
        if (!started) return;
        std::string event = phase;
        require(event.find("vessel.pre.") != 0 && event != "world.finalise.before", "Paused lifetime world updated a physical vessel");
        if (event == "app.frame.end") {
            require(!running && frames < targetFrames, "Actual paused frame sequence differs"); ++frames; snapshot(); if (frames == targetFrames) loadedModules();
        }
    }); }
    void clbkSimulationEnd() override { guarded([&] {
        // Orbiter::CloseSession's normal branch resets the world and destroys
        // its renderer before delivering this callback. --scenariox is forbidden.
        require(started && frames == targetFrames && worlds == completed + 1, "Normal world teardown ended early");
        started = false; heap(); ++completed;
        auto folder = std::filesystem::path("attachment-world-" + std::to_string(completed));
        require(std::filesystem::create_directory(folder), "Fresh per-world lifetime evidence required");
        for (const char* name : {"graphics-lifecycle.json","renderer-info.json","visual-events.csv","Orbiter.cfg"})
            std::filesystem::copy_file(name, folder / name);
        events << worlds << ',' << frames << ",normal-world-cleanup-complete," << completed << '\n'; events.flush();
        std::ofstream("attachment-completed-worlds.txt") << completed << '\n';
        require(PostMessageA(control, completed < requested ? NextWorld : Finish, 0, 0) != FALSE, "Cannot dispatch next lifecycle command");
    }); }
    void command(UINT message) { guarded([&] {
        require(!started && worlds == completed, "Launchpad command reentered incomplete cleanup");
        HWND pad = launchpad();
        if (message == NextWorld) {
            selectOriginal(pad);
            SendMessageA(pad, WM_COMMAND, MAKEWPARAM(LaunchButton, BN_CLICKED), 0);
        } else {
            require(completed == requested, "Lifetime completion is incomplete");
            require(PostMessageA(pad, WM_CLOSE, 0, 0) != FALSE, "Actual launchpad close failed");
        }
    }); }
};
void observe(const char* event, const char*, double, double, int running) { if (driver) driver->core(event, running); }
LRESULT CALLBACK controlProcedure(HWND window, UINT message, WPARAM w, LPARAM l) {
    if (driver && (message == NextWorld || message == Finish)) { driver->command(message); return 0; }
    return DefWindowProcA(window, message, w, l);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
