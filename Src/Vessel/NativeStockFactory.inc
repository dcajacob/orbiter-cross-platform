// Licensed under the MIT License. Included after the actual stock entry points.
#include "Production/NativeVesselFactory.h"
#ifndef ORBITER_NATIVE_STOCK_CREATE
#define ORBITER_NATIVE_STOCK_CREATE ovcInit
#define ORBITER_NATIVE_STOCK_DESTROY ovcExit
#endif
namespace {
using StockFactory=orbiter::native::VesselFactory<ORBITER_NATIVE_STOCK_CREATE,ORBITER_NATIVE_STOCK_DESTROY>;
const OrbiterNativeModuleDescriptor stockModule={
    sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_VESSEL,ORBITER_NATIVE_STOCK_NAME,
    ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,
    StockFactory::initialize,StockFactory::shutdown};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept {
    return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&stockModule:nullptr;
}
