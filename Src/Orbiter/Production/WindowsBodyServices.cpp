// Licensed under the MIT License
#include "WindowsBodyServices.h"
#include "Orbiter.h"
#include "Log.h"
#include <type_traits>
extern Orbiter* g_pOrbiter;
extern bool g_bStateUpdate;
namespace orbiter::production {
static_assert(std::is_same<BodyParameter, DWORD>::value, "Windows body parameter ABI changed");
static_assert(std::is_same<BodyContent, DWORD_PTR>::value, "Windows visual content ABI changed");
static_assert(std::is_same<BodyVisual, VISHANDLE>::value, "Windows visual handle ABI changed");
static_assert(GenericBodyType == OBJTP_GENERIC, "Windows object type changed");
namespace {
class WindowsBodyServices final : public BodyServices {
public:
    bool IsUpdating() const override { return g_bStateUpdate; }
    std::filesystem::path ConfigPath(const char* name) override { return g_pOrbiter->ConfigPath(name); }
    void LoadStatus(const char* path, int line) override { g_pOrbiter->OutputLoadStatus(path, line); }
    void SizeChanged(Body* body) override { g_pOrbiter->NotifyObjectSize(body); }
    void VisualEvent(Body* body, BodyVisual visual, BodyParameter message, BodyContent content) override
    {
        g_pOrbiter->SendBodyVisualEvent(body, visual, message, content);
    }
    void CheckUpdateState(bool valid) override { dCHECK(valid, "Update state not available") }
};
}
BodyServices& GetWindowsBodyServices()
{
    static WindowsBodyServices services;
    return services;
}
}
