// Licensed under the MIT License. Included after each actual atmosphere class.
#include "Production/NativeAbi.h"
#include <cstdio>
#include <exception>
#include <memory>
#include <stdexcept>
namespace {
int ORBITER_NATIVE_CALL initializeAtmosphere(const OrbiterNativeHost* host,void** result,char* error,uint32_t capacity) noexcept
{
    try {
        if (!host || !host->context || !result) throw std::runtime_error("Missing native atmosphere context");
        auto* body=static_cast<orbiter::native::CelestialModule*>(host->context);
        auto instance=std::make_unique<ORBITER_NATIVE_ATMOSPHERE_CLASS>(body);
        *result=static_cast<orbiter::native::Atmosphere*>(instance.release());return 0;
    } catch (const std::exception& e) {std::snprintf(error,capacity,"%s",e.what());return 1;}
    catch (...) {std::snprintf(error,capacity,"Unexpected native atmosphere initialization failure");return 1;}
}
void ORBITER_NATIVE_CALL shutdownAtmosphere(void* instance) noexcept
{delete static_cast<orbiter::native::Atmosphere*>(instance);}
const OrbiterNativeModuleDescriptor nativeAtmosphereDescriptor={sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_ATMOSPHERE,ORBITER_NATIVE_ATMOSPHERE_NAME,ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,
    initializeAtmosphere,shutdownAtmosphere};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t version) noexcept
{return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&nativeAtmosphereDescriptor:nullptr;}
