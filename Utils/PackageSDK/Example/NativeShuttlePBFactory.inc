// Licensed under the MIT License.
// The stock example retains the exact ShuttlePB capabilities and records its SDK calls.
#include "Production/NativeVesselFactory.h"
#include <fstream>

namespace {
void record(const char* event)
{
    std::ofstream("sdk-vessel.txt", std::ios::app) << event << '\n';
}

class SdkShuttlePB final : public ShuttlePB {
public:
    SdkShuttlePB(OBJHANDLE vessel, int model) : ShuttlePB(vessel, model) { record("created"); }
    ~SdkShuttlePB() { record("destroyed"); }

    void clbkSetClassCaps(FILEHANDLE config) override
    {
        ShuttlePB::clbkSetClassCaps(config);
        record("configured");
    }

    void clbkPostCreation() override
    {
        if (GetEmptyMass() == PB_EMPTYMASS) record("read-back-mass");
    }
};

VESSEL* createVessel(OBJHANDLE handle, int model) { return new SdkShuttlePB(handle, model); }
void destroyVessel(VESSEL* vessel) { delete static_cast<SdkShuttlePB*>(vessel); }

using Factory = orbiter::native::VesselFactory<createVessel, destroyVessel>;
const OrbiterNativeModuleDescriptor descriptor = {
    sizeof(OrbiterNativeModuleDescriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION,
    sizeof(void*), ORBITER_NATIVE_VESSEL, "Phase 8 SDK stock ShuttlePB example",
    ORBITER_NATIVE_SDK_BUILD, ORBITER_NATIVE_CPP_ABI, Factory::initialize, Factory::shutdown
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor*
ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &descriptor : nullptr;
}
