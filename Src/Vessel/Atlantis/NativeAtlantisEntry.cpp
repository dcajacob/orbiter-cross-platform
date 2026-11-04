// Licensed under the MIT License
// Three checked SDK entry modules share the original cross-referencing C++ types.
#include "Production/NativeVesselModule.h"
#ifndef ATLANTIS_NATIVE_QUERY
#error The Atlantis SDK entry must select its original vessel factory
#endif
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
ATLANTIS_NATIVE_QUERY(std::uint32_t version) noexcept;
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept {
    return ATLANTIS_NATIVE_QUERY(version);
}
