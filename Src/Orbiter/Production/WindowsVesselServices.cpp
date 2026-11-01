// Licensed under the MIT License
#include "WindowsVesselServices.h"
#include "Orbiter.h"
#include "Log.h"
extern Orbiter* g_pOrbiter;
namespace orbiter::production {
namespace {
class WindowsVesselServices final:public VesselServices {
public:
    std::filesystem::path ConfigFile(const char* name,bool extension) override
    {return extension?g_pOrbiter->ConfigPath(name):g_pOrbiter->Cfg()->ConfigPathNoext(name);}
    void Fatal(const char* message) override
    {LOGOUT_ERR("%s",message);g_pOrbiter->TerminateOnError();}
    void Check(bool valid,const char* message) override {dCHECK(valid,message)}
};
}
VesselServices& GetWindowsVesselServices() {static WindowsVesselServices services;return services;}
}
