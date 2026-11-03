// Licensed under the MIT License
#pragma once
#include "NativeModule.h"
#include "NativeVesselAPI.h"
#include "ResourceResolver.h"
#include <memory>

struct lua_State;
namespace orbiter::production {
// LuaInline owns the interpreter list. The host holds the module until all
// vessels and the scenario have released their interpreters.
struct NativeScriptApi {
    std::size_t size;
    INTERPRETERHANDLE (*create)();
    int (*destroy)(INTERPRETERHANDLE);
    INTERPRETERHANDLE (*run)(const char*);
    bool (*execute)(INTERPRETERHANDLE, const char*);
    bool (*queue)(INTERPRETERHANDLE, const char*);
    lua_State *(*state)(INTERPRETERHANDLE);
    void (*postStep)(double, double, double);
    void (*deleteVessel)(OBJHANDLE);
    void (*end)();
};

class NativeScriptHost {
public:
    explicit NativeScriptHost(const ResourceResolver &modules): modules(modules) {}
    NativeScriptApi& Load();
    void PostStep(double simt, double simdt, double mjd);
    void DeleteVessel(OBJHANDLE vessel);
    void End();
private:
    const ResourceResolver &modules;
    std::unique_ptr<NativeModule> library;
    NativeScriptApi *api = nullptr;
};
}
