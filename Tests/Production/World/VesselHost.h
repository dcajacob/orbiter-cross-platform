// Licensed under the MIT License
// Explicit unsupported-vessel policy for the celestial-world component probe.
#ifndef ORBITER_WORLD_COMPONENT_VESSEL_HOST_H
#define ORBITER_WORLD_COMPONENT_VESSEL_HOST_H
#include "Production/WorldVesselServices.h"
#include <stdexcept>
using orbiter::production::UInt32;
struct WorldVesselHost final:orbiter::production::WorldVesselServices {
    bool force=true;
    Body& State(Vessel&) const override {throw std::runtime_error("Native vessel boundary is not implemented: State");}
    const char* Name(const Vessel&) const override {throw std::runtime_error("Native vessel boundary is not implemented: Name");}
    Vessel* Create(PlanetarySystem&,const char*,const char*,std::ifstream&) override {throw std::runtime_error("Native vessel boundary is not implemented: Create");}
    void PostCreation(Vessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: PostCreation");}
    void InitSupervessel(Vessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: InitSupervessel");}
    void ModulePostCreation(Vessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: ModulePostCreation");}
    void Write(const Vessel&,std::ostream&) override {throw std::runtime_error("Native vessel boundary is not implemented: Write");}
    void OptionChanged(Vessel&,UInt32,UInt32) override {throw std::runtime_error("Native vessel boundary is not implemented: OptionChanged");}
    void UpdateBodyForces(Vessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: UpdateBodyForces");}
    void Update(Vessel&,bool) override {throw std::runtime_error("Native vessel boundary is not implemented: Update");}
    void PostUpdate(Vessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: PostUpdate");}
    void Timejump(Vessel&,double,int) override {throw std::runtime_error("Native vessel boundary is not implemented: Timejump");}
    void ProcessMessage(Vessel&,UInt32,void*) override {throw std::runtime_error("Native vessel boundary is not implemented: ProcessMessage");}
    SuperVessel* Structure(Vessel&) const override {throw std::runtime_error("Native vessel boundary is not implemented: Structure");}
    SuperVessel* CreateStructure(Vessel&,Vessel&,int,int,bool) override {throw std::runtime_error("Native vessel boundary is not implemented: CreateStructure");}
    void DeleteStructure(SuperVessel*) override {throw std::runtime_error("Native vessel boundary is not implemented: DeleteStructure");}
    void Merge(SuperVessel&,Vessel&,int,Vessel&,int) override {throw std::runtime_error("Native vessel boundary is not implemented: Merge");}
    void Add(SuperVessel&,Vessel&,int,Vessel&,int,bool) override {throw std::runtime_error("Native vessel boundary is not implemented: Add");}
    void Detach(SuperVessel&,Vessel&,int,double) override {throw std::runtime_error("Native vessel boundary is not implemented: Detach");}
    bool Empty(const SuperVessel&) const override {throw std::runtime_error("Native vessel boundary is not implemented: Empty");}
    void Update(SuperVessel&,bool) override {throw std::runtime_error("Native vessel boundary is not implemented: Update");}
    void PostUpdate(SuperVessel&) override {throw std::runtime_error("Native vessel boundary is not implemented: PostUpdate");}
    void ForceUpdate() override {force=true;}
};
#endif
