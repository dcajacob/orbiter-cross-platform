// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NATIVE_MODULE_H
#define ORBITER_PRODUCTION_NATIVE_MODULE_H
#include "ModuleBootstrap.h"
#include "Export.h"
#include <filesystem>
#include <string>
namespace orbiter::production {
struct NativeModuleInfo { std::string name, sdkBuild, cppAbi; uint32_t kind; };
// Internal bootstrap owner. The borrowed parent context and SDK services remain
// alive until shutdown has returned and the library has been unloaded.
class ORBITER_PRODUCTION_API NativeModule {
public:
    NativeModule(const std::filesystem::path& library, uint32_t expectedKind, void* context);
    ~NativeModule();
    NativeModule(const NativeModule&) = delete;
    NativeModule& operator=(const NativeModule&) = delete;
    const NativeModuleInfo& Info() const noexcept { return info; }
    void* Instance() const noexcept { return instance; }
    void* Symbol(const char* name) const;
    static const char* SdkBuild() noexcept;
    static const char* CppAbi() noexcept;
private:
    void Close() noexcept;
    void* library = nullptr;
    const OrbiterNativeModuleDescriptor* descriptor = nullptr;
    void* instance = nullptr;
    OrbiterNativeHost host{};
    NativeModuleInfo info;
};
}
#endif
