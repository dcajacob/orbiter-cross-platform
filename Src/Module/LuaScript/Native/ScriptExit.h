// Licensed under the MIT License
#pragma once
typedef struct lua_State lua_State;

#ifdef __cplusplus
extern "C" {
#endif
// Used only while aborting a native process, after an explicit oapi.exit.
void orbiter_native_lua_cancel(lua_State *state, int cancel);
#ifdef __cplusplus
}
#endif
