// Licensed under the MIT License
#include "ScriptFiles.h"
#include "Production/ResourceResolver.h"
extern "C" {
#include <lua/lauxlib.h>
#include <lua/lualib.h>
}
#include <cstdio>
#include <memory>

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    orbiter::production::ResourceResolver resources(argv[1]);
    std::unique_ptr<lua_State, decltype(&lua_close)> state(luaL_newstate(), lua_close);
    auto* L = state.get();
    luaL_openlibs(L);
    orbiter::script::InstallFileAccess(L, resources);
    const char* test = R"lua(
        assert(type(assert(loadfile('./script/OAPI_INIT.lua'))) == 'function')
        assert(type(assert(loadfile([[.\SCRIPT\dG\AAP.LUA]]))) == 'function')
        local a, b = dofile([[.\SCRIPT\dG\RETURNS.LUA]])
        assert(a == 'first' and b == 2)
        local chunk, err = loadfile('Script/dg/missing.lua')
        assert(not chunk and type(err) == 'string')
        local ok = pcall(dofile, 'Script/../outside.lua')
        assert(not ok)
        assert(loadfile('user.lua'))()
        assert(user_script_loaded == true)
        dofile = function() error('modified global') end
    )lua";
    if (luaL_dostring(L,test) || orbiter::script::RunStockFile(L,"Script\\STRICT.lua") ||
        luaL_dostring(L,"assert(type(strictmode_add_global) == 'function')")) {
        std::fprintf(stderr,"%s\n",lua_tostring(L,-1));
        return 1;
    }
}
