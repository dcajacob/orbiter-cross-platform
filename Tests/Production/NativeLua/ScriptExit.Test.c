// Licensed under the MIT License
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "ScriptExit.h"
#include <stdio.h>
#include <stdlib.h>

static int finalizers = 0;

static void require(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "%s\n", message);
        exit(1);
    }
}

static int request_exit(lua_State *state)
{
    orbiter_native_lua_cancel(state, 1);
    return luaL_error(state, "Lua thread terminated by oapi.exit");
}

static int finalized(lua_State *state)
{
    (void)state;
    ++finalizers;
    return 0;
}

int main(void)
{
    const char *cases[] = {
        "request_exit(); after = 1",
        "pcall(request_exit); after = 1",
        "xpcall(request_exit, function() after = 1 end); after = 2",
        "coroutine.resume(coroutine.create(function() request_exit(); after = 1 end)); after = 2",
        "coroutine.wrap(function() request_exit(); after = 1 end)(); after = 2",
        "local child = coroutine.create(function() request_exit(); after = 1 end); "
            "local parent = coroutine.create(function() pcall(coroutine.resume, child); after = 2 end); "
            "pcall(coroutine.resume, parent); after = 3",
        "local function f(n) if n == 0 then request_exit() else pcall(f, n-1) end; after = 1 end; pcall(f, 20); after = 2",
        "local child = coroutine.create(function() request_exit() end); "
            "xpcall(function() coroutine.resume(child) end, function() after = 1 end); after = 2",
        "pcall(function() pcall(request_exit); while true do after = 1 end end); after = 2"
    };
    unsigned i;
    lua_State *unrelated = luaL_newstate();
    require(unrelated != NULL, "Cannot allocate unrelated VM");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        printf("Cancellation case %u: %s\n", i + 1, cases[i]);
        fflush(stdout);
        lua_State *state = luaL_newstate();
        require(state != NULL, "Cannot allocate VM");
        luaL_openlibs(state);
        lua_pushcfunction(state, request_exit);
        lua_setglobal(state, "request_exit");
        lua_newuserdata(state, 1);
        lua_newtable(state);
        lua_pushcfunction(state, finalized);
        lua_setfield(state, -2, "__gc");
        lua_setmetatable(state, -2);
        lua_setglobal(state, "resource");
        require(luaL_dostring(state, "local ok = pcall(error, 'ordinary error'); assert(not ok); before = 1") == 0,
                "Ordinary protected calls changed before cancellation");
        require(luaL_loadstring(state, cases[i]) == 0, "Cannot compile cancellation case");
        require(lua_pcall(state, 0, 0, 0) != 0, "Process cancellation was caught by Lua");
        lua_getglobal(state, "after");
        require(lua_isnil(state, -1), "Lua executed instructions after process exit");
        lua_pop(state, 1);
        require(luaL_dostring(unrelated, "value = 17") == 0, "Cancellation escaped into an unrelated VM");
        orbiter_native_lua_cancel(state, 0);
        lua_close(state);
        require(finalizers == (int)i + 1, "Native resource finalization was skipped");
    }
    lua_close(unrelated);
    printf("Nine real Lua cancellation cases passed; protected calls and nested coroutines stop before following instructions; native finalizers run\n");
    return 0;
}
