// Licensed under the MIT License
// Invalid metadata only. Never constructs a vessel or changes a host object.
#include "Production/ModuleBootstrap.h"
#include "Production/NativeAbi.h"
#include <cstdio>

#ifndef PHASE6_REJECTED_METADATA
#error Select one explicit invalid-metadata control
#endif
static_assert(PHASE6_REJECTED_METADATA >= 0 && PHASE6_REJECTED_METADATA <= 6);
namespace {
int ORBITER_NATIVE_CALL initialize(const OrbiterNativeHost*,void**,char*,uint32_t) noexcept {
    std::fputs("REJECTION_FIXTURE_INITIALIZE_CALLED\n",stderr);
    return 1;
}
void ORBITER_NATIVE_CALL shutdown(void*) noexcept {}
const OrbiterNativeModuleDescriptor descriptor={
    PHASE6_REJECTED_METADATA==4 ? 4u : sizeof(OrbiterNativeModuleDescriptor),
    PHASE6_REJECTED_METADATA==3 ? 99u : ORBITER_NATIVE_BOOTSTRAP_VERSION,
    PHASE6_REJECTED_METADATA==2 ? 4u : sizeof(void*),
    PHASE6_REJECTED_METADATA==5 ? ORBITER_NATIVE_GRAPHICS : ORBITER_NATIVE_VESSEL,
    "Phase6 invalid bootstrap metadata",
    PHASE6_REJECTED_METADATA==0 ? "unqualified-sdk-build" : ORBITER_NATIVE_SDK_BUILD,
    PHASE6_REJECTED_METADATA==1 ? "incompatible-cpp-abi" : ORBITER_NATIVE_CPP_ABI,
    initialize,
    PHASE6_REJECTED_METADATA==6 ? nullptr : shutdown
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor*
ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t abi) noexcept {
    return abi==ORBITER_NATIVE_BOOTSTRAP_VERSION ? &descriptor : nullptr;
}
