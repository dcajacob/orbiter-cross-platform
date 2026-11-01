// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_WORLD_VESSEL_SERVICES_H
#define ORBITER_PRODUCTION_WORLD_VESSEL_SERVICES_H
#include "Export.h"
#include "CoreTypes.h"
#include <iosfwd>
class Body;
class PlanetarySystem;
class Vessel;
class SuperVessel;
namespace orbiter::production {
// Required access to real vessels while their module/SDK boundary is extracted.
// The production system owns every object and retains the original loop order.
class WorldVesselServices {
public:
    virtual ~WorldVesselServices()=default;
    virtual Body& State(Vessel&) const=0;
    virtual const char* Name(const Vessel&) const=0;
    virtual Vessel* Create(PlanetarySystem&,const char*,const char*,std::ifstream&)=0;
    virtual void PostCreation(Vessel&)=0;
    virtual void InitSupervessel(Vessel&)=0;
    virtual void ModulePostCreation(Vessel&)=0;
    virtual void Write(const Vessel&,std::ostream&)=0;
    virtual void OptionChanged(Vessel&,UInt32,UInt32)=0;
    virtual void UpdateBodyForces(Vessel&)=0;
    virtual void Update(Vessel&,bool)=0;
    virtual void PostUpdate(Vessel&)=0;
    virtual void Timejump(Vessel&,double,int)=0;
    virtual void ProcessMessage(Vessel&,UInt32,void*)=0;
    virtual SuperVessel* Structure(Vessel&) const=0;
    virtual SuperVessel* CreateStructure(Vessel&,Vessel&,int,int,bool)=0;
    virtual void DeleteStructure(SuperVessel*)=0;
    virtual void Merge(SuperVessel&,Vessel&,int,Vessel&,int)=0;
    virtual void Add(SuperVessel&,Vessel&,int,Vessel&,int,bool)=0;
    virtual void Detach(SuperVessel&,Vessel&,int,double)=0;
    virtual bool Empty(const SuperVessel&) const=0;
    virtual void Update(SuperVessel&,bool)=0;
    virtual void PostUpdate(SuperVessel&)=0;
    virtual void ForceUpdate()=0;
};
ORBITER_PRODUCTION_API WorldVesselServices* BindWorldVesselServices(WorldVesselServices*);
ORBITER_PRODUCTION_API WorldVesselServices& GetWorldVesselServices();
}
#endif
