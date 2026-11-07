// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NATIVE_VESSEL_MODULE_H
#define ORBITER_PRODUCTION_NATIVE_VESSEL_MODULE_H
#include "NativeModule.h"
#include "ResourceResolver.h"
#include "NativeVesselAPI.h"
#include <cstdint>
class Vessel;
namespace orbiter::native {
struct VesselInit {
    std::uint32_t size;
    OBJHANDLE vessel;
    int flightmodel;
};
// The interface is destroyed before vessel resources, and its library remains
// loaded until the vessel has released animations and all borrowed module data.
struct VesselInstance {
    std::uint32_t size;
    VESSEL* vessel;
    void (*release)(VesselInstance*) noexcept;
};
}
namespace orbiter::production {
const ResourceResolver* BindNativeVesselModuleResources(const ResourceResolver*);
// Internal admission metadata; configuration-only vessels return nullptr.
const char* NativeVesselModuleName(const Vessel&) noexcept;
}
#endif
