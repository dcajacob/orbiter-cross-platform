// Licensed under the MIT License. Included after the actual stock module.
#include "Production/NativeVesselFactory.h"
namespace {
using NativeShuttlePB=orbiter::native::VesselFactory<ovcInit,ovcExit>;
const OrbiterNativeModuleDescriptor nativeShuttlePB={
    sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_VESSEL,"Stock ShuttlePB",
    ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,
    NativeShuttlePB::initialize,NativeShuttlePB::shutdown};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL OrbiterNativeQuery(std::uint32_t version) noexcept
{return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&nativeShuttlePB:nullptr;}
