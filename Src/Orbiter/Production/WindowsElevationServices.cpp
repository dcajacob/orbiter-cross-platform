// Licensed under the MIT License
#include "ElevationServices.h"
#include "elevmgr.h"
#include "Planet.h"
#include "Orbiter.h"
#include "TimeData.h"
#include <algorithm>
extern Orbiter* g_pOrbiter;
extern TimeData td;
namespace {
class WindowsElevationServices final : public orbiter::production::ElevationServices {
public:
    orbiter::production::ElevationSetup Setup(const CelestialBody& value) const override
    {
        const auto* body=&value;
        const auto* config=g_pOrbiter->Cfg();
        orbiter::production::ElevationSetup result{config->CfgVisualPrm.ElevMode,config->CfgPRenderPrm.TileLoadFlags,SURF_MAX_PATCHLEVEL2-7,1.0};
        if (body->Type()==OBJTP_PLANET) {
            const auto* planet=static_cast<const Planet*>(body);
            result.maximumLevel=std::min((DWORD)result.maximumLevel,planet->MaxPatchLevel()-7);
            result.resolution=planet->ElevationResolution();
        }
        return result;
    }
    std::unique_ptr<ZTreeMgr> OpenArchive(const CelestialBody& body,bool modified) override {
        char path[256];g_pOrbiter->Cfg()->PTexPath(path,body.Name());
        return std::unique_ptr<ZTreeMgr>(ZTreeMgr::CreateFromFile(path,modified ? ZTreeMgr::LAYER_ELEVMOD : ZTreeMgr::LAYER_ELEV));
    }
    bool HasLooseLayer(const CelestialBody& body,bool modified) const override {
        char path[256];const auto name=std::string(body.Name())+(modified ? "\\Elev_mod" : "\\Elev");
        g_pOrbiter->Cfg()->PTexPath(path,name.c_str());
        return std::filesystem::is_directory(path);
    }
    std::filesystem::path LooseTile(const CelestialBody& body,bool modified,int level,int latitude,int longitude) const override {
        char name[256],path[256];
        std::snprintf(name,sizeof(name),"%s\\%s\\%02d\\%06d\\%06d.elv",body.Name(),modified ? "Elev_mod" : "Elev",level,latitude,longitude);
        g_pOrbiter->Cfg()->PTexPath(path,name);return path;
    }
    double SystemTime() const override {return td.SysT0;}
    void Filter(const CelestialBody& body,int latitude,int longitude,int level,double resolution,std::int16_t* data) override {
        auto* client=g_pOrbiter->GetGraphicsClient();
        if (client) client->clbkFilterElevation((OBJHANDLE)&body,latitude,longitude,level,resolution,data);
    }
};
WindowsElevationServices services;

}
namespace orbiter::production {
ElevationServices& GetWindowsElevationServices() {return services;}
}
