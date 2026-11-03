// Licensed under the MIT License
// Test-only dispatches at the same native boundary used by the Lua schedule
// observer. The original Session methods are called exactly once unless exit
// terminates that call. The scene and its full vessel graph are unchanged.
#include "Production/Session.h"
#include "Production/NativeScript.h"
#include "Interpreter.h"
#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <stdexcept>
#include <string>

namespace {
struct ProcessPreload {
    ProcessPreload() { unsetenv("LD_PRELOAD"); }
} processPreload;
unsigned frame = 0;
INTERPRETERHANDLE script = nullptr, inner = nullptr;

void event(const char *name)
{
    std::ofstream file("exit-dispatch.csv", std::ios::app);
    file << frame << ',' << name << '\n';
}

int nested(lua_State *)
{
    auto *state = oapiGetLua(inner);
    if (luaL_loadstring(state, "oapi.exit(0); error('inner Lua continued after exit')") != 0)
        throw std::runtime_error("Cannot load inner exit chunk");
    Interpreter::LuaCall(state, 0, 0);
    event("nested.native.return");
    return 0;
}

void dispatch()
{
    std::ifstream input("exit-mode.txt");
    std::string mode; input >> mode;
    if (mode == "stock") return;
    script = oapiCreateInterpreter();
    {
        std::ifstream maps("/proc/self/maps");
        std::ofstream loaded("exit-loaded.txt");
        loaded << maps.rdbuf();
    }
    event("exit.dispatch");
    if (mode == "async") {
        oapiAsyncScriptCmd(script, "run_global('exit.lua')");
    } else if (mode == "sync") {
        oapiExecScriptCmd(script, "run_global('exit.lua')");
        event("sync.after.exit");
    } else if (mode == "direct" || mode == "cross-vm") {
        auto *state = oapiGetLua(script);
        if (mode == "cross-vm") {
            inner = oapiCreateInterpreter();
            lua_pushcfunction(state, nested);
            lua_setglobal(state, "nested_native_exit");
        }
        if (luaL_loadfile(state, "exit.lua") != 0)
            throw std::runtime_error("Cannot load exit script");
        Interpreter::LuaCall(state, 0, 0);
        event("direct.after.exit");
    } else throw std::runtime_error("Unknown exit dispatch mode");
}
}

void orbiter::production::Session::UpdateWorld(SessionServices& services, const TimeData& time,
    const bool& running, const bool& playback, bool& updating, const bool& force)
{
    static auto original = reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    if (!original) throw std::runtime_error("Original UpdateWorld missing");
    event("update.enter");
    if (frame == 4) dispatch();
    original(services, time, running, playback, updating, force);
    event("update.return");
}

void orbiter::production::Session::EndTimeStep(SessionServices& services, TimeData& time,
    bool running, const bool& active, bool& force)
{
    static auto original = reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    if (!original) throw std::runtime_error("Original EndTimeStep missing");
    event("end.enter");
    original(services, time, running, active, force);
    event("end.return");
    ++frame;
}
