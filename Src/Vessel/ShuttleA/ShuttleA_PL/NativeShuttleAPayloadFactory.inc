// Licensed under the MIT License. Included after the stock payload entry points.
#include "Production/NativeVesselFactory.h"
namespace {
using PayloadFactory = orbiter::native::VesselFactory<ovcInit, ovcExit>;
const OrbiterNativeModuleDescriptor payloadModule = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_VESSEL, "Stock ShuttleA payload",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
    PayloadFactory::initialize, PayloadFactory::shutdown
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &payloadModule : nullptr;
}
