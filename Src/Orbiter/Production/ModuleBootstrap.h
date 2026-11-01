// Licensed under the MIT License
// Internal native bootstrap ABI. This does not expose a vessel/atmosphere SDK.
#ifndef ORBITER_NATIVE_MODULE_BOOTSTRAP_H
#define ORBITER_NATIVE_MODULE_BOOTSTRAP_H
#include <stdint.h>
#ifdef _WIN32
#define ORBITER_NATIVE_CALL __cdecl
#define ORBITER_NATIVE_EXPORT __declspec(dllexport)
#else
#define ORBITER_NATIVE_CALL
#define ORBITER_NATIVE_EXPORT __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
#define ORBITER_NATIVE_NOEXCEPT noexcept
#else
#define ORBITER_NATIVE_NOEXCEPT
#endif
#define ORBITER_NATIVE_BOOTSTRAP_VERSION 1u
enum OrbiterNativeModuleKind {
    ORBITER_NATIVE_VESSEL=1, ORBITER_NATIVE_CELESTIAL=2,
    ORBITER_NATIVE_ATMOSPHERE=3, ORBITER_NATIVE_PLUGIN=4, ORBITER_NATIVE_GRAPHICS=5
};
typedef struct OrbiterNativeHost {
    uint32_t struct_size, abi_version;
    const char* sdk_build;
    const char* cpp_abi;
    void* context; // borrowed; must outlive the module instance
} OrbiterNativeHost;
typedef struct OrbiterNativeModuleDescriptor {
    uint32_t struct_size, abi_version, pointer_bytes, kind;
    const char* name;
    const char* sdk_build;
    const char* cpp_abi;
    int (ORBITER_NATIVE_CALL *initialize)(const OrbiterNativeHost*, void** instance,
        char* error, uint32_t error_capacity) ORBITER_NATIVE_NOEXCEPT;
    void (ORBITER_NATIVE_CALL *shutdown)(void* instance) ORBITER_NATIVE_NOEXCEPT;
} OrbiterNativeModuleDescriptor;
typedef const OrbiterNativeModuleDescriptor* (ORBITER_NATIVE_CALL *OrbiterNativeQueryFunction)(uint32_t)
    ORBITER_NATIVE_NOEXCEPT;
// Modules export OrbiterNativeQuery. It returns immutable metadata, creates no
// engine objects, and performs no registration. Initialization is explicit and
// follows all compatibility checks. No exception may cross this C interface.
#endif
