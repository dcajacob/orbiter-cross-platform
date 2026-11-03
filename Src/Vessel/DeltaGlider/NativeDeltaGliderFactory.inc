// Licensed under the MIT License. Included after the stock vessel entry points.
#include "Production/NativeVesselFactory.h"

namespace {
// The native loader owns one factory instance per vessel. The stock drawing
// resources belong to the module, shared by all simultaneous DG and DG-S ships.
unsigned activeVessels = 0;

VESSEL *CreateNativeGlider(OBJHANDLE object, int flightmodel)
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

void DestroyNativeGlider(VESSEL *vessel)
{
    ovcExit(vessel);
    if (--activeVessels == 0) ReleaseDrawingResources();
}

using GliderFactory = orbiter::native::VesselFactory<CreateNativeGlider, DestroyNativeGlider>;
const OrbiterNativeModuleDescriptor gliderModule = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_VESSEL, "Stock DeltaGlider",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI,
    GliderFactory::initialize, GliderFactory::shutdown
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &gliderModule : nullptr;
}
