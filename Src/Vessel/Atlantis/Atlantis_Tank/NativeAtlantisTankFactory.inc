// Licensed under the MIT License. Included after the unchanged stock tank entry points.
#include "Production/NativeVesselFactory.h"
namespace {
using TankFactory=orbiter::native::VesselFactory<ovcInit,ovcExit>;
const OrbiterNativeModuleDescriptor tankModule={
    sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_VESSEL,"Stock Atlantis external tank",
    ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,TankFactory::initialize,TankFactory::shutdown
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeAtlantisTankQuery(std::uint32_t version) noexcept {
    return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&tankModule:nullptr;
}
