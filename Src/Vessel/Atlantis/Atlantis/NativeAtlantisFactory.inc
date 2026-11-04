// Licensed under the MIT License. Included after the unchanged stock vessel entry points.
#include "Production/NativeVesselFactory.h"
namespace {
unsigned activeAtlantisVessels=0;
VESSEL* CreateNativeAtlantis(OBJHANDLE object,int flightmodel) {
    try {
        if(activeAtlantisVessels==0)InitDrawingResources();
        VESSEL* vessel=ovcInit(object,flightmodel);
        ++activeAtlantisVessels;
        return vessel;
    } catch(...) {
        if(activeAtlantisVessels==0)ReleaseDrawingResources();
        throw;
    }
}
void DestroyNativeAtlantis(VESSEL* vessel) {
    ovcExit(vessel);
    if(--activeAtlantisVessels==0)ReleaseDrawingResources();
}
using AtlantisFactory=orbiter::native::VesselFactory<CreateNativeAtlantis,DestroyNativeAtlantis>;
const OrbiterNativeModuleDescriptor atlantisModule={
    sizeof(OrbiterNativeModuleDescriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*),ORBITER_NATIVE_VESSEL,"Stock Atlantis",
    ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,AtlantisFactory::initialize,AtlantisFactory::shutdown
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept {
    return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&atlantisModule:nullptr;
}
