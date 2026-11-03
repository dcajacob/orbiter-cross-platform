// Licensed under the MIT License. The native host dispatches to the stock list
// and opc* routines, in the same order as the Windows module manager.
#include "Production/NativeScript.h"
#include "Production/NativeAbi.h"
#include <cstdio>

namespace {
orbiter::production::NativeScriptApi scriptApi = {
    sizeof(orbiter::production::NativeScriptApi),
    opcNewInterpreter, opcDelInterpreter, opcRunInterpreter,
    opcExecScriptCmd, opcAsyncScriptCmd, opcGetLua,
    [](double simt, double simdt, double mjd) { g_IList->clbkPostStep(simt, simdt, mjd); },
    [](OBJHANDLE vessel) { g_IList->clbkDeleteVessel(vessel); },
    [] { g_IList->clbkSimulationEnd(); }
};

int ORBITER_NATIVE_CALL InitializeLuaInline(const OrbiterNativeHost *host, void **instance,
                                            char *error, std::uint32_t capacity) noexcept
{
    try {
        if (!host || host->struct_size != sizeof(*host) || !host->context || !instance || g_IList)
            throw std::runtime_error("Invalid or repeated LuaInline initialization");
        g_IList = new InterpreterList();
        *instance = &scriptApi;
        return 0;
    } catch (const std::exception &e) {
        std::snprintf(error, capacity, "%s", e.what());
        return 1;
    } catch (...) {
        std::snprintf(error, capacity, "LuaInline initialization failed");
        return 1;
    }
}

void ORBITER_NATIVE_CALL ShutdownLuaInline(void *) noexcept
{
    delete g_IList;
    g_IList = nullptr;
}

const OrbiterNativeModuleDescriptor luaModule = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_PLUGIN, "Stock LuaInline",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
    InitializeLuaInline, ShutdownLuaInline
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &luaModule : nullptr;
}
