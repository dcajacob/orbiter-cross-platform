// Licensed under the MIT License
#include "NativeVesselModule.h"
#include "Vessel.h"
#include "Config.h"
#include "ConfigFile.h"
#include "SurfaceServices.h"
#include "RigidBodyServices.h"
#include "TimeData.h"
#include "NativeObservation/ApplicationObservation.h"
#include <cstring>
#include <memory>
#include <stdexcept>
namespace orbiter::production {
namespace {
const ResourceResolver* resources=nullptr;
void moduleEvent(const char* phase,const Vessel& vessel) {
    const auto& time=GetRigidBodyServices().Time();
    OrbiterTestObserve(phase,vessel.Name(),time.SimT0,time.MJD0,1);
}
}
const ResourceResolver* BindNativeVesselModuleResources(const ResourceResolver* next)
{auto* previous=resources;resources=next;return previous;}
namespace {
struct LoadedVessel {
    native::VesselInit context;
    std::string name;
    std::unique_ptr<NativeModule> module;
    native::VesselInstance* instance=nullptr;
    LoadedVessel(Vessel& vessel,int flightmodel,const char* name)
        :context{sizeof(context),&vessel,flightmodel},name(name)
    {
        if(!resources) throw std::logic_error("Native vessel module resources are not bound");
        const auto file=resources->Resolve(std::string("Vessel/")+name+".so");
        module=std::make_unique<NativeModule>(file,ORBITER_NATIVE_VESSEL,&context);
        instance=static_cast<native::VesselInstance*>(module->Instance());
        if(instance->size!=sizeof(*instance) || !instance->vessel || !instance->release)
            throw std::runtime_error("Native vessel interface is incompatible: "+std::string(name));
        moduleEvent("module.library.open",vessel);
    }
};
}
}
using namespace orbiter::production;
const char* Vessel::NativeModuleName() const noexcept
{
    const auto* loaded=static_cast<const LoadedVessel*>(hMod);
    return loaded?loaded->name.c_str():nullptr;
}
bool Vessel::LoadModule(std::ifstream& config)
{
    hMod=nullptr;ClearModule();
    flightmodel=GetSurfaceServices().Configuration().CfgLogicPrm.FlightModelLevel;
    char name[256];
    try {
        if(GetItemString(config,"Module",name)) {
            RegisterModule(name);
            return true;
        }
        // Config-driven stock vessels such as ISS intentionally have no DLL.
        modIntf.v=new VESSEL(this,flightmodel);modIntf.coreCreated=true;
        return false;
    } catch(...) {
        // All three constructors call this after the default allocations and
        // before class capabilities. Their Vessel destructor will not run if
        // module loading throws; LoadedVessel already owns any loader state.
        ClearTouchdownPoints();
        delete[]forcevec;forcevec=nullptr;
        delete[]forcepos;forcepos=nullptr;
        delete[]classname;classname=nullptr;
        throw;
    }
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
    moduleEvent("module.interface.release.before",*vessel);
    loaded->instance->release(loaded->instance);
    moduleEvent("module.interface.release.after",*vessel);
}
void Vessel::ClearModule()
{
    const bool loaded=hMod!=nullptr;
    if(loaded)moduleEvent("module.library.close.before",*this);
    delete static_cast<LoadedVessel*>(hMod);
    if(loaded)moduleEvent("module.library.close.after",*this);
    hMod=nullptr;
    std::memset(&modIntf,0,sizeof(modIntf));
}
