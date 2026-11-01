// Licensed under the MIT License
// A boundary fixture linked to the actual shared production Body implementation.
// It is not a native stock vessel, atmosphere, ephemeris or graphics client.
#include "Production/ModuleBootstrap.h"
#include "Production/NativeAbi.h"
#include "Body.h"
#include <cstdio>
#include <memory>
#include <exception>
namespace {
struct Instance { Body* host;double size;Body body{250,4}; };
int ORBITER_NATIVE_CALL initialize(const OrbiterNativeHost* host,void** result,char* error,uint32_t capacity) noexcept
{
    try {
        if (!host || !host->context) return 1;
        auto* body=static_cast<Body*>(host->context);
        auto instance=std::make_unique<Instance>();instance->host=body;instance->size=body->Size();
#ifdef FIXTURE_FAIL_INIT
        std::snprintf(error,capacity,"intentional fixture initialization failure");return 1;
#endif
        body->SetSize(20);
        *result=instance.release();return 0;
    } catch (const std::exception& e) { std::snprintf(error,capacity,"%s",e.what());return 1; }
    catch (...) { std::snprintf(error,capacity,"unexpected fixture failure");return 1; }
}
void ORBITER_NATIVE_CALL shutdown(void* value) noexcept
{
    auto* instance=static_cast<Instance*>(value);
    instance->host->SetSize(instance->size);delete instance;
}
const OrbiterNativeModuleDescriptor descriptor={
#ifdef FIXTURE_BAD_SIZE
    4,
#else
    sizeof(OrbiterNativeModuleDescriptor),
#endif
#ifdef FIXTURE_BAD_ABI
    99,
#else
    ORBITER_NATIVE_BOOTSTRAP_VERSION,
#endif
    sizeof(void*),
#ifdef FIXTURE_BAD_KIND
    ORBITER_NATIVE_ATMOSPHERE,
#else
    ORBITER_NATIVE_PLUGIN,
#endif
    "ProductionBodyBoundaryFixture",
#ifdef FIXTURE_BAD_BUILD
    "different-engine-sdk-build",
#else
    ORBITER_NATIVE_SDK_BUILD,
#endif
#ifdef FIXTURE_BAD_CPP
    "different-cpp-toolchain-or-standard-library",
#else
    ORBITER_NATIVE_CPP_ABI,
#endif
    initialize,
#ifdef FIXTURE_MISSING_SHUTDOWN
    nullptr
#else
    shutdown
#endif
};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t abi) noexcept
{ return abi==ORBITER_NATIVE_BOOTSTRAP_VERSION ? &descriptor : nullptr; }
extern "C" ORBITER_NATIVE_EXPORT double ORBITER_NATIVE_CALL NativeFixtureMass(void* instance) noexcept
{ return static_cast<Instance*>(instance)->body.Mass(); }
