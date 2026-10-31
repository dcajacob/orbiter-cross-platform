// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_BODY_SERVICES_H
#define ORBITER_PRODUCTION_BODY_SERVICES_H
#include "Export.h"
#include <cstdint>
#include <filesystem>
class Body;
namespace orbiter::production {
// The Windows internal class signatures retain DWORD's exact underlying type.
// Native code uses the same 32-bit quantity, without declaring Win32 types/APIs.
#ifdef _WIN32
using BodyParameter = unsigned long;
#else
using BodyParameter = std::uint32_t;
#endif
static_assert(sizeof(BodyParameter) == 4, "Body parameter width changed");
using BodyVisual = void*;
using BodyContent = std::uintptr_t;
constexpr int GenericBodyType = 1;

class BodyServices {
public:
    virtual ~BodyServices() = default;
    virtual bool IsUpdating() const = 0;
    virtual std::filesystem::path ConfigPath(const char* name) = 0;
    virtual void LoadStatus(const char* path, int line) = 0;
    virtual void SizeChanged(Body* body) = 0;
    virtual void VisualEvent(Body* body, BodyVisual visual, BodyParameter message, BodyContent content) = 0;
    virtual void CheckUpdateState(bool valid) = 0;
};
// The existing world is process-global and simulation-thread confined. Bind its
// services before constructing any Body and release them after world teardown.
// An unbound native world fails explicitly rather than inventing defaults.
ORBITER_PRODUCTION_API BodyServices* BindBodyServices(BodyServices* services);
ORBITER_PRODUCTION_API BodyServices& GetBodyServices();
}
#endif
