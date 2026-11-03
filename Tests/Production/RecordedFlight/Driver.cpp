// Licensed under the MIT License
// Observe the original application and route declared inputs through its window.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include "../../../Src/Orbiter/Production/PlaybackObservation.h"
#include <cstdlib>
#include <cmath>
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
    std::ofstream state,inputs;
    HWND window = nullptr;
    int previousFma = -1;
    unsigned frames = 0,totalFrames=60,stopPlaybackAt=0;
    std::ofstream playbackTrace;
    int left = 1;
    bool observeFocus = false;
    int functionCommand = -1;
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
        if (action.event == "left_down") {
            mouse(x, y, WM_LBUTTONDOWN);
        } else if (action.event == "left_up") {
            x = lastX; y = lastY; mouse(x, y, WM_LBUTTONUP);
        } else if (action.event == "move") {
            mouse(x, y, 0);
        } else if (action.event == "focus_dialog") {
            require(observeFocus && oapiSimulateBufferedKey(OAPI_KEY_F3), "Original F3 dispatch failed");
        } else if (action.event == "options_dialog") {
            require(observeFocus && oapiSimulateBufferedKey(OAPI_KEY_F6), "Original F6 dispatch failed");
        } else if (action.event == "function_dialog") {
            DWORD control=OAPI_KEY_LCONTROL;
            require(observeFocus && oapiSimulateBufferedKey(OAPI_KEY_F4,&control,1), "Original Ctrl-F4 dispatch failed");
        } else {
            require(false, "Unknown UI reference action");
        }
        inputs << frames << ',' << action.event << ',' << x << ',' << y << ',' << hex(action.text.c_str()) << '\n';
        inputs.flush();
    }
    void snapshot() {
        if(playbackTrace.is_open()) {
            orbiter::production::playback_observation::Row(playbackTrace,frames);
            return;
        }
        auto* vessel = oapiGetFocusInterface();
        require(vessel!=nullptr,"Original focus missing");
        VECTOR3 p{}, v{}, w{}; MATRIX3 r{};
        vessel->GetGlobalPos(p); vessel->GetGlobalVel(v); vessel->GetAngularVel(w); vessel->GetRotationMatrix(r);
        state << frames << ',' << oapiGetSimTime() << ',' << oapiGetSimMJD()
              << ',' << vessel->GetName() << ',' << vessel->GetClassName() << ',' << oapiCockpitMode() << ',' << oapiGetHUDMode()
              << ',' << oapiGetMFDMode(0) << ',' << oapiGetMFDMode(1);
        for (double value : {p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,w.x,w.y,w.z,vessel->GetMass(),vessel->GetFuelMass()}) state << ',' << value;
        state << ',' << vessel->GetMeshCount() << ',' << vessel->GetThrusterCount() << '\n';
        state.flush();
    }
public:
    explicit Driver(HINSTANCE instance) : Module(instance) {
        guarded([&] {
            if(std::getenv("ORBITER_TEST_OBSERVER_SSE2")) {
                previousFma=_get_FMA3_enable();
                _set_FMA3_enable(0);
                require(_get_FMA3_enable()==0,"Original SSE2 diagnostic profile was not selected");
            }
            std::ofstream("math-profile.txt")<<(_get_FMA3_enable()?"fma3":"sse2")<<'\n';
            observeFocus = bool(std::ifstream("focus-bars.enabled"));
            if(std::ifstream("function-probe.enabled")) {
                static char label[]="SDK function",description[]="Public SDK callback";
                functionCommand=oapiRegisterCustomCmd(label,description,[](void*) {
                    std::ofstream("custom-function-events.txt",std::ios::app)<<"invoked\n";
                },nullptr);
                std::ofstream("custom-function-events.txt")<<"registered\n";
            }
            std::ifstream config("ui-case.txt");
            unsigned count = 0;
            std::ifstream playbackConfig("playback.enabled");
            if(playbackConfig) {
                require(bool(playbackConfig>>totalFrames>>stopPlaybackAt) && totalFrames>0,"Invalid playback observation");
                playbackTrace.exceptions(std::ios::badbit|std::ios::failbit);
                playbackTrace.imbue(std::locale::classic());playbackTrace.open("playback-state.csv");
                playbackTrace<<std::setprecision(17);orbiter::production::playback_observation::Header(playbackTrace);
            }
            if(!playbackTrace.is_open())require(bool(config >> left >> count) && count > 0 && count < 32, "Invalid UI schedule");
            for (unsigned i = 0; i < count; ++i) {
                Action action{};
                require(bool(config >> action.tick >> action.event >> action.x >> action.y >> action.text), "Incomplete UI schedule");
                if (action.text == "-") action.text.clear();
                actions.push_back(action);
            }
            for (auto* stream : {&state,&inputs}) {
                stream->imbue(std::locale::classic());
                stream->exceptions(std::ios::badbit | std::ios::failbit);
            }
            state.open("cockpit-state.csv"); inputs.open("ui-inputs.csv");
            state << std::setprecision(17);
            state << "tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters\n";
            inputs << "tick,event,x,y,text_hex\n";
            setter = reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr), "OrbiterTestSetObserver"));
            require(setter && setter(1, observe, 51982.5), "Original observation ABI missing");
            std::srand(0);
        });
    }
    ~Driver() override {
        if(functionCommand>=0)guarded([&] {
            require(oapiUnregisterCustomCmd(functionCommand),"Original custom function teardown failed");
            std::ofstream("custom-function-events.txt",std::ios::app)<<"unregistered\n";
        });
        if (setter) setter(1, nullptr, std::numeric_limits<double>::quiet_NaN());
        if(previousFma>=0)_set_FMA3_enable(previousFma);
    }
    void clbkSimulationStart(RenderMode mode) override {
        guarded([&] { require(mode != RENDER_NONE, "Original renderer required"); started = true; });
    }
    void clbkPreStep(double, double, double) override {
        guarded([&] {
            Sleep(120);
            if(playbackTrace.is_open()) {
                if(!initialized) {require(oapiGetFocusInterface()->Playback(),"Stock vessel did not enter playback");initialized=true;snapshot();}
                if(stopPlaybackAt && frames==stopPlaybackAt) {
                    DWORD ctrl=OAPI_KEY_LCONTROL;
                    require(oapiSimulateBufferedKey(OAPI_KEY_C,&ctrl,1),"Original stop playback failed");
                }
                return;
            }
            if (!initialized) {
                window = FindWindowA("Orbiter Render Window", nullptr);
                DWORD process = 0;
                require(window && GetWindowThreadProcessId(window, &process) && process == GetCurrentProcessId(), "Owned original render window missing");
                require(oapiCameraInternal() && oapiCockpitMode() == (observeFocus ? 2 : 1), "Required original cockpit missing");
                if (observeFocus) {
                    char earthName[]="Earth";
                    auto earth=oapiGetGbodyByName(earthName);
                    require(earth!=nullptr,"Original Earth missing");
                    std::ofstream("earth-obliquity.txt")<<std::setprecision(17)<<oapiGetPlanetObliquity(earth)<<'\n';
                }
                oapiOpenMFD(left, 0); oapiOpenMFD(2, 1); oapiSetHUDMode(1);
                mouse(640, 360, 0);
                initialized = true; snapshot();
            }
            for (const auto& action : actions) if (action.tick == frames) act(action);
        });
    }
    void core(const char* phase,int running) {
        guarded([&] {
            if (started && std::string(phase) == "app.frame.end") {
                require(initialized && running, "Unexpected UI reference frame state");
                ++frames; snapshot();
            }
        });
    }
    void clbkSimulationEnd() override {
        guarded([&] { require(frames == totalFrames, "Incomplete UI reference"); started = false; std::ofstream("cockpit-complete.txt") << frames << '\n'; });
    }
};
void observe(const char* phase,const char*,double,double,int running) {
    if (driver) driver->core(phase,running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { driver = new Driver(instance); oapiRegisterModule(driver); }
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
