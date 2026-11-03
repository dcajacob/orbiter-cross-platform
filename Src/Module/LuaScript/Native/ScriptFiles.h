// Licensed under the MIT License
#pragma once
#include <stdexcept>
#include <string>
extern "C" {
#include <lua/lua.h>
}
namespace orbiter::production { class ResourceResolver; }

namespace orbiter::script {
void InstallFileAccess(lua_State*, const production::ResourceResolver&);

// Direct SDK file loads (startup and vessel initialization) must keep using
// the original file loader even if a script later replaces global dofile.
inline int RunStockFile(lua_State* L, const char* name)
{
    lua_getfield(L, LUA_REGISTRYINDEX, "orbiter.native.stock.dofile");
    lua_pushstring(L, name);
    return lua_pcall(L, 1, LUA_MULTRET, 0);
}

inline void RequireStockFile(lua_State* L, const char* name)
{
    if (RunStockFile(L, name) == 0) return;
    const char* detail = lua_tostring(L, -1);
    std::string message = std::string("Failed to execute ") + name + ": " +
                          (detail ? detail : "non-string Lua error");
    lua_pop(L, 1);
    throw std::runtime_error(message);
}
}
