// Licensed under the MIT License. Included after the actual SpiceBody class.
#include "Production/NativeAbi.h"
#include <exception>
#include <memory>
#include <stdexcept>
namespace {
unsigned nativeSpiceInstances=0;
int ORBITER_NATIVE_CALL initializeNativeSpice(const OrbiterNativeHost* host,void** result,char* error,uint32_t capacity) noexcept
{
    try {
        if (!host || !host->context || !result) throw std::runtime_error("Missing native SPICE context");
        const auto& context=*static_cast<const orbiter::native::CelestialInit*>(host->context);
        if (context.size!=sizeof(context) || !context.body || !context.host) throw std::runtime_error("Invalid native SPICE context");
        if (nativeSpiceInstances && spiceHost!=context.host) throw std::runtime_error("SPICE is already bound to another production world");
        if (!nativeSpiceInstances) {
            spiceHost=context.host;
            loaded_kernels.clear();
            // Diagnostics go through the native host; never write in the cwd.
            errdev_c("SET",1024,"NULL");errprt_c("SET",1024,"ALL");erract_c("SET",1024,"REPORT");trcoff_c();
        }
        auto instance=std::make_unique<SpiceBody>(context);
        *result=static_cast<orbiter::native::CelestialModule*>(instance.release());
        ++nativeSpiceInstances;return 0;
    } catch (const std::exception& e) {std::snprintf(error,capacity,"%s",e.what());return 1;}
    catch (...) {std::snprintf(error,capacity,"Unexpected native SPICE initialization failure");return 1;}
}
void ORBITER_NATIVE_CALL shutdownNativeSpice(void* instance) noexcept
{
    delete static_cast<SpiceBody*>(static_cast<orbiter::native::CelestialModule*>(instance));
    if (--nativeSpiceInstances==0) {kclear_c();loaded_kernels.clear();spiceHost=nullptr;}
}
const OrbiterNativeModuleDescriptor nativeSpiceDescriptor={sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_CELESTIAL,"Production SPICE",ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,
    initializeNativeSpice,shutdownNativeSpice};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t version) noexcept
{return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&nativeSpiceDescriptor:nullptr;}
