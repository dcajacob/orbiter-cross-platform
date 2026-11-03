// Licensed under the MIT License
#include "ScriptFiles.h"
#include "Production/ResourceResolver.h"
#include "Production/Text.h"
#include <cstring>

namespace orbiter::script {
namespace {
bool stockScript(const char* path)
{
    while (path[0]=='.' && (path[1]=='/' || path[1]=='\\')) path+=2;
    return production::ComparePrefix(path,"Script",6)==0 && (path[6]=='/' || path[6]=='\\');
}

int runFileFunction(lua_State* L)
{
    if (lua_type(L,1)==LUA_TSTRING && stockScript(lua_tostring(L,1))) {
        bool failed=false;
        try {
            auto* files=static_cast<const production::ResourceResolver*>(lua_touserdata(L,lua_upvalueindex(2)));
            const auto resolved=files->Resolve(lua_tostring(L,1)).string();
            lua_pushlstring(L,resolved.data(),resolved.size());
            lua_replace(L,1);
        } catch (const std::exception& error) {
            lua_pushstring(L,error.what());
            failed=true;
        }
        if (failed) {
            // loadfile returns (nil, message), whereas dofile raises its error.
            if (!lua_toboolean(L,lua_upvalueindex(3))) return lua_error(L);
            lua_pushnil(L);
            lua_insert(L,-2);
            return 2;
        }
    }
    const int arguments=lua_gettop(L);
    lua_pushvalue(L,lua_upvalueindex(1));
    lua_insert(L,1);
    lua_call(L,arguments,LUA_MULTRET);
    return lua_gettop(L);
}
}

void InstallFileAccess(lua_State* L, const production::ResourceResolver& files)
{
    for (const char* name: {"dofile","loadfile"}) {
        lua_getglobal(L,name);
        lua_pushlightuserdata(L,const_cast<production::ResourceResolver*>(&files));
        const bool loadOnly=std::strcmp(name,"loadfile")==0;
        lua_pushboolean(L,loadOnly);
        lua_pushcclosure(L,runFileFunction,3);
        if (!loadOnly) {
            lua_pushvalue(L,-1);
            lua_setfield(L,LUA_REGISTRYINDEX,"orbiter.native.stock.dofile");
        }
        lua_setglobal(L,name);
    }
}
}
