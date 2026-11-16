// Licensed under the MIT License
#include "XRSoundDLL.h"
#include "VesselXRSoundEngine.h"
#include "Production/ModuleBootstrap.h"
#include "Production/NativeAbi.h"
#include "Production/NativeSound.h"
#include <memory>
#include <stdexcept>

using namespace orbiter::production;
const ResourceResolver* xrsound::resources = nullptr;

namespace {
NativeSoundApi api{
    sizeof(NativeSoundApi),
    [](double t, double dt, double mjd) { XRSoundDLL::s_pInstance->clbkPreStep(t, dt, mjd); },
    [](bool paused) { XRSoundDLL::s_pInstance->clbkPause(paused); },
    [](OBJHANDLE vessel) {
        auto& sounds = XRSoundDLL::s_pInstance->m_allVesselsMap;
        const auto found = sounds.find(vessel);
        if (found != sounds.end()) {
            XRSoundEngine::DestroyInstance(found->second);
            sounds.erase(found);
        }
    }
};

int Initialize(const OrbiterNativeHost* host, void** instance, char* error, std::uint32_t capacity) noexcept
{
    if (!host || host->struct_size != sizeof(*host) || !host->context || !instance || XRSoundDLL::s_pInstance) {
        std::snprintf(error, capacity, "Invalid or repeated XRSound initialization");
        return 1;
    }
    try {
        xrsound::resources = &static_cast<const NativeSoundContext*>(host->context)->assets;
        auto module = std::make_unique<XRSoundDLL>();
        module->clbkSimulationStart(XRSoundDLL::RenderMode::Native);
        if (module->GetGlobalConfig().ParseFailed())
            throw std::runtime_error("Cannot load XRSound configuration (see XRSound.log)");
        XRSoundDLL::s_pInstance = module.release();
        *instance = &api;
        return 0;
    } catch (const std::exception& e) {
        std::snprintf(error, capacity, "%s", e.what());
    } catch (...) {
        std::snprintf(error, capacity, "XRSound initialization failed");
    }
    xrsound::resources = nullptr;
    return 1;
}

void Shutdown(void*) noexcept
{
    std::unique_ptr<XRSoundDLL> module(XRSoundDLL::s_pInstance);
    module->clbkSimulationEnd();
    XRSoundDLL::s_pInstance = nullptr;
    xrsound::resources = nullptr;
}

const OrbiterNativeModuleDescriptor descriptor{
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_PLUGIN, "XRSound",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI, Initialize, Shutdown
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor*
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &descriptor : nullptr;
}
