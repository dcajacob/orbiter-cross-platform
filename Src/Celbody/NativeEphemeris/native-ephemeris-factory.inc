// Licensed under the MIT License
namespace {
int ORBITER_NATIVE_CALL initialize(const OrbiterNativeHost* host, void** value,
                                  char* error, std::uint32_t capacity) noexcept
{
    try {
        if (!host || host->struct_size != sizeof(*host) || !host->context || !value)
            throw std::runtime_error("Missing celestial initialization context");
        const auto& context = *static_cast<const orbiter::native::CelestialInit*>(host->context);
        *value = static_cast<orbiter::native::CelestialModule*>(new EphemerisProvider(context));
        return 0;
    } catch (const std::exception& problem) {
        std::snprintf(error, capacity, "%s", problem.what());
        return 1;
    } catch (...) {
        std::snprintf(error, capacity, "Unexpected celestial initialization failure");
        return 1;
    }
}

void ORBITER_NATIVE_CALL shutdown(void* value) noexcept
{
    delete static_cast<orbiter::native::CelestialModule*>(value);
}

const OrbiterNativeModuleDescriptor module = {
    sizeof(module), ORBITER_NATIVE_BOOTSTRAP_VERSION, sizeof(void*),
    ORBITER_NATIVE_CELESTIAL, ephemerisName, ORBITER_NATIVE_SDK_BUILD,
    ORBITER_NATIVE_CPP_ABI, initialize, shutdown
};
}

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL
OrbiterNativeQuery(std::uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &module : nullptr;
}
