// Licensed under the MIT License. Included after the unchanged stock booster entry points.
#include "Production/NativeVesselFactory.h"
namespace {
using SrbFactory=orbiter::native::VesselFactory<ovcInit,ovcExit>;
const OrbiterNativeModuleDescriptor srbModule={
    sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_VESSEL,"Stock Atlantis solid rocket booster",
    ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,SrbFactory::initialize,SrbFactory::shutdown
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeAtlantisSrbQuery(std::uint32_t version) noexcept {
    return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&srbModule:nullptr;
}
