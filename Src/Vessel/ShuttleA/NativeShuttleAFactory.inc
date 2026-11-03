// Licensed under the MIT License. Included after the stock vessel entry points.
#include "Production/NativeVesselFactory.h"

namespace {
// Drawing resources belong to the module, shared by all simultaneous ships.
unsigned activeVessels = 0;

VESSEL *CreateNativeShuttleA(OBJHANDLE object, int flightmodel)
{
    try {
        if (activeVessels == 0) InitDrawingResources();
        VESSEL *vessel = ovcInit(object, flightmodel);
        ++activeVessels;
        return vessel;
    } catch (...) {
        if (activeVessels == 0) ReleaseDrawingResources();
        throw;
    }
}

void DestroyNativeShuttleA(VESSEL *vessel)
{
    ovcExit(vessel);
    if (--activeVessels == 0) ReleaseDrawingResources();
}

using ShuttleAFactory = orbiter::native::VesselFactory<CreateNativeShuttleA, DestroyNativeShuttleA>;
const OrbiterNativeModuleDescriptor shuttleAModule = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_VESSEL, "Stock ShuttleA",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
    ShuttleAFactory::initialize, ShuttleAFactory::shutdown
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &shuttleAModule : nullptr;
}
