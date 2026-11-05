// Licensed under the MIT License. Keep the original MFD, interpreter repository,
// registration and callbacks; only the platform bootstrap is adapted here.
#include "Production/NativeLuaMfd.h"
#include "Production/NativeAbi.h"
#include "Production/ModuleBootstrap.h"
#include <cstdio>
#include <stdexcept>

namespace {
orbiter::production::NativeLuaMfdApi terminalApi = {
    sizeof(orbiter::production::NativeLuaMfdApi), opcPostStep,
    [](OBJHANDLE vessel) { g_IList->DeleteInterpreters(vessel); },
    [] { g_IList->DeleteList(); }
};

int ORBITER_NATIVE_CALL InitializeLuaMfd(const OrbiterNativeHost *host, void **instance,
                                        char *error, std::uint32_t capacity) noexcept
{
    if (!host || host->struct_size != sizeof(*host) || !host->context || !instance || g_IList) {
        std::snprintf(error, capacity, "Invalid or repeated LuaMFD initialization");
        return 1;
    }
    try {
        InitModule();
        *instance = &terminalApi;
        return 0;
    } catch (const std::exception &e) {
        if (g_MFDmode) { oapiUnregisterMFDMode(g_MFDmode); g_MFDmode = 0; }
        delete g_IList; g_IList = nullptr;
        std::snprintf(error, capacity, "%s", e.what());
        return 1;
    } catch (...) {
        if (g_MFDmode) { oapiUnregisterMFDMode(g_MFDmode); g_MFDmode = 0; }
        delete g_IList; g_IList = nullptr;
        std::snprintf(error, capacity, "LuaMFD initialization failed");
        return 1;
    }
}

void ORBITER_NATIVE_CALL ShutdownLuaMfd(void *) noexcept
{
    ExitModule();
    g_IList = nullptr;
    g_MFDmode = 0;
}

const OrbiterNativeModuleDescriptor terminalModule = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_PLUGIN, "Stock Lua Terminal MFD",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
    InitializeLuaMfd, ShutdownLuaMfd
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &terminalModule : nullptr;
}
