// Licensed under the MIT License
#include "WindowsSurfaceServices.h"
#include "Orbiter.h"
#include "State.h"
#include "Vessel.h"
#include "Camera.h"
#include "Log.h"
extern Orbiter* g_pOrbiter;
extern Camera* g_camera;
namespace orbiter::production {
namespace {
class WindowsSurfaceServices final:public SurfaceServices {
public:
    Config& Configuration() const override {return *g_pOrbiter->Cfg();}
    const char* Context() const override {return g_pOrbiter->PState()->Context();}
    std::filesystem::path ConfigDirectory(const char* relative) const override
    {return std::filesystem::path(g_pOrbiter->ConfigPath((std::string(relative)+"/dummy").c_str())).parent_path();}
    std::filesystem::path MarkerDirectory(const char* body,const char* overridePath) const override
    {return overridePath ? std::filesystem::path(overridePath) : std::filesystem::path(g_pOrbiter->Cfg()->CfgDirPrm.ConfigDir)/body/"Marker";}
    void DeallocationProgress() override {g_pOrbiter->UpdateDeallocationProgress();}
    bool HasGraphics() const override {return g_pOrbiter->GetGraphicsClient()!=nullptr;}
    SURFHANDLE LoadTexture(const char* name,bool applicationSurface) override {
        if (applicationSurface) return g_pOrbiter->LoadTexture(name);
        auto* graphics=g_pOrbiter->GetGraphicsClient();
        return graphics ? graphics->clbkLoadTexture(name) : nullptr;
    }
    void ReleaseTexture(SURFHANDLE texture,bool applicationSurface) override {
        if (applicationSurface) g_pOrbiter->ReleaseSurface(texture);
        else if (auto* graphics=g_pOrbiter->GetGraphicsClient()) graphics->clbkReleaseTexture(texture);
    }
    VesselBase* VesselState(Vessel* vessel) const override {return vessel;}
    void Refuel(VesselBase& vessel) override {vessel.Refuel();}
    Vector CameraPosition() const override {return g_camera->GPos();}
    Vector CameraDirection() const override {return g_camera->Direction();}
    double CameraAperture() const override {return g_camera->Aperture();}
    void Log(const std::string& message) override {LOGOUT("%s",message.c_str());}
};
}
SurfaceServices& GetWindowsSurfaceServices() {static WindowsSurfaceServices services;return services;}
}
