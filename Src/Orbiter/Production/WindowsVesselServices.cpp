// Licensed under the MIT License
#include "WindowsVesselServices.h"
#include "Orbiter.h"
#include "Log.h"
#include "Pane.h"
#include "GraphicsAPI.h"
#include "State.h"
extern Orbiter* g_pOrbiter;
extern Pane* g_pane;
namespace orbiter::production {
namespace {
class WindowsVesselServices final:public VesselServices {
public:
    std::filesystem::path ConfigFile(const char* name,bool extension) override
    {return extension?g_pOrbiter->ConfigPath(name):g_pOrbiter->Cfg()->ConfigPathNoext(name);}
    void Fatal(const char* message) override
    {LOGOUT_ERR("%s",message);g_pOrbiter->TerminateOnError();}
    void Check(bool valid,const char* message) override {dCHECK(valid,message)}
    MeshManager& Meshes() override {return g_pOrbiter->meshmanager;}
    const char* PlaybackDirectory() const override {return g_pOrbiter->PState()->PlaybackDir();}
    void SetWarpFactor(double warp) override {g_pOrbiter->SetWarpFactor(warp);}
    double TimejumpDelta() const override {return g_pOrbiter->tjump.dt;}
    void RedrawCockpitAreas(int flags) override {g_pane->RedrawCockpitAreas(flags);}
    const double* ParticleLevel(const oapi::ParticleStream* stream) const override {return stream->Level();}
};
}
VesselServices& GetWindowsVesselServices() {static WindowsVesselServices services;return services;}
}
