// Licensed under the MIT License
#include "ScriptExit.h"
#include "lauxlib.h"
#include "lstate.h"

static void cancel_instruction(lua_State *state, lua_Debug *debug)
{
    (void)debug;
    // Process termination must bypass xpcall's Lua error handler, including
    // handlers entered recursively while a hook is already running.
    state->errfunc = 0;
    luaL_error(state, "Lua thread terminated by oapi.exit");
}

void orbiter_native_lua_cancel(lua_State *state, int cancel)
{
    GCObject *object;
    // All coroutine states are on this pinned Lua runtime's rootgc list.
    // Installing hooks allocates nothing and leaves that list unchanged.
    // Cancel every state so pcall, xpcall and nested coroutine.resume cannot
    // resume script instructions after a process exit request.
    for (object = G(state)->rootgc; object; object = object->gch.next) {
        if (object->gch.tt == LUA_TTHREAD) {
            lua_sethook(gco2th(object), cancel ? cancel_instruction : NULL,
                        cancel ? LUA_MASKCOUNT | LUA_MASKCALL | LUA_MASKRET : 0, 1);
        }
    }
    if (cancel) state->errfunc = 0;
}
