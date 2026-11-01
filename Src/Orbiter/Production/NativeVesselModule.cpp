// Licensed under the MIT License
#include "NativeVesselModule.h"
#include "Vessel.h"
#include "Config.h"
#include "ConfigFile.h"
#include "SurfaceServices.h"
#include <cstring>
#include <memory>
#include <stdexcept>
namespace orbiter::production {
namespace {const ResourceResolver* resources=nullptr;}
const ResourceResolver* BindNativeVesselModuleResources(const ResourceResolver* next)
{auto* previous=resources;resources=next;return previous;}
namespace {
struct LoadedVessel {
    native::VesselInit context;
    std::unique_ptr<NativeModule> module;
    native::VesselInstance* instance=nullptr;
    LoadedVessel(Vessel& vessel,int flightmodel,const char* name)
        :context{sizeof(context),&vessel,flightmodel}
    {
        if(!resources) throw std::logic_error("Native vessel module resources are not bound");
        const auto file=resources->Resolve(std::string("Vessel/")+name+".so");
        module=std::make_unique<NativeModule>(file,ORBITER_NATIVE_VESSEL,&context);
        instance=static_cast<native::VesselInstance*>(module->Instance());
        if(instance->size!=sizeof(*instance) || !instance->vessel || !instance->release)
            throw std::runtime_error("Native vessel interface is incompatible: "+std::string(name));
    }
};
}
}
using namespace orbiter::production;
bool Vessel::LoadModule(std::ifstream& config)
{
    hMod=nullptr;ClearModule();
    flightmodel=GetSurfaceServices().Configuration().CfgLogicPrm.FlightModelLevel;
    char name[256];
    if(GetItemString(config,"Module",name)) {
        RegisterModule(name);
        return true;
    }
    // Config-driven stock vessels such as ISS intentionally have no DLL.
    modIntf.v=new VESSEL(this,flightmodel);modIntf.coreCreated=true;
    return false;
}
bool Vessel::RegisterModule(const char* name)
{
    auto loaded=std::make_unique<LoadedVessel>(*this,flightmodel,name);
    modIntf.v=loaded->instance->vessel;
    modIntf.ovcExit=ReleaseNativeInterface;
    hMod=loaded.release();return true;
}
void Vessel::ReleaseNativeInterface(VESSEL* interface)
{
    auto* vessel=static_cast<Vessel*>(interface->GetHandle());
    auto* loaded=static_cast<LoadedVessel*>(vessel->hMod);
    loaded->instance->release(loaded->instance);
}
void Vessel::ClearModule()
{
    delete static_cast<LoadedVessel*>(hMod);hMod=nullptr;
    std::memset(&modIntf,0,sizeof(modIntf));
}
