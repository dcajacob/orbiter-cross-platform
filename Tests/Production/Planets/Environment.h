#ifndef ORBITER_PLANET_COMPONENT_ENVIRONMENT_H
#define ORBITER_PLANET_COMPONENT_ENVIRONMENT_H
// Licensed under the MIT License
// Direct production Planet/Base lifecycle validation, not a native application.
// Unsupported world/vessel/camera operations fail explicitly in this probe.
#include "Celbody.h"
#include "PsysCore.h"
#include "Planet.h"
#include "Base.h"
#include "Mesh.h"
#include "Vesselbase.h"
#include "Config.h"
#include "Production/SurfaceServices.h"
#include "Production/Text.h"
#include "Production/NavigationServices.h"
#include "Production/MeshServices.h"
#include "Star.h"
#include "elevmgr.h"
#include "ConfigFile.h"
#include "Production/BodyServices.h"
#include "Production/RigidBodyServices.h"
#include "Production/NativeCelestialServices.h"
#include "Production/NativeElevationServices.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>
#include <memory>
#include <stdexcept>
#include <vector>
using namespace orbiter::production;
namespace production_component_test {
struct Environment : BodyServices,RigidBodyServices,SurfaceServices,NavigationServices {
    const ResourceResolver& config;
    Config settings;
    PlanetarySystem* system=nullptr;
    bool updating=false;
    TimeData time;
    CFG_PHYSICSPRM physics{};
    explicit Environment(const ResourceResolver& c):config(c) {time.Reset(51982.5);physics=settings.CfgPhysicsPrm;}
    bool IsUpdating() const override {return updating;}
    std::filesystem::path ConfigPath(const char* name) override {
        std::string path=name;if (std::filesystem::path(path).extension().empty()) path+=".cfg";
        return config.Resolve(path);
    }
    void LoadStatus(const char* path,int) override {std::clog<<"Loading production celestial config: "<<path<<'\n';}
    void SizeChanged(Body*) override {++sizeNotifications;}
    void VisualEvent(Body*,BodyVisual,BodyParameter,BodyContent) override {throw std::logic_error("No renderer in direct module probe");}
    void CheckUpdateState(bool valid) override {if (!valid) throw std::logic_error("Invalid production update state");}
    TimeData& Time() override {return time;}
    const CFG_PHYSICSPRM& Physics() const override {return physics;}
    PlanetarySystem* World() const override {return system;}
    const Body& Reference(const CelestialBody* body) const override {return *body;}
    Vector ReferencePosition(const CelestialBody* body,double fraction) const override {return body->InterpolatePosition(fraction);}
    PlanetarySystem& RequireWorld() const {if (!system) throw std::logic_error("No world bound in component probe");return *system;}
    double GravityContribution(const CelestialBody* body,const Vector& position) const override {return RequireWorld().GetGravityContribution(body,position);}
    void ScanGravity(const PlanetarySystem* world,const Vector& position,const Body* exclude,GFieldData* field,bool update) const override {
        if (update) world->UpdateGFieldSources(&position,exclude,field);
        else world->ScanGFieldSources(&position,exclude,field);
    }
    Vector Acceleration(const Vector& position,double fraction,const Body* exclude,GFieldData* field) const override {return RequireWorld().Gacc_intermediate(position,fraction,exclude,field);}
    Vector PerturbedAcceleration(const CelestialBody* reference,const Vector& position,double fraction,const Body* exclude,GFieldData* field) const override {return RequireWorld().Gacc_intermediate_pert(reference,position,fraction,exclude,field);}
    Vector RelativeAcceleration(const Vector& position,const CelestialBody* reference,double fraction,const CelestialBody* exclude,GFieldData* field) const override {return RequireWorld().GaccRel(position,reference,fraction,exclude,field);}
    Vector NonsphericalAcceleration(const Vector& position,const CelestialBody* reference) const override {return SingleGacc_perturbation(position,reference);}
    void TraceAllocation(const char*,int) override {++allocations;}
    Config& Configuration() const override {return const_cast<Config&>(settings);}
    const char* Context() const override {return nullptr;}
    std::filesystem::path ConfigDirectory(const char* path) const override {
        return config.ContainsDirectory(path) ? config.ResolveDirectory(path) : config.Root()/ResourceResolver::Normalize(path);
    }
    std::filesystem::path MarkerDirectory(const char* body,const char* overridePath) const override {
        if (overridePath) {
            std::string relative=overridePath;
            std::replace(relative.begin(),relative.end(),'\\','/');
            if (ComparePrefix(relative.c_str(),"Config/",7)==0) relative.erase(0,7);
            return ConfigDirectory(relative.c_str());
        }
        return ConfigDirectory((std::string(body)+"/Marker").c_str());
    }
    void DeallocationProgress() override {}
    bool HasGraphics() const override {return false;}
    SURFHANDLE LoadTexture(const char*,bool) override {throw std::logic_error("No renderer in planet lifecycle probe");}
    void ReleaseTexture(SURFHANDLE,bool) override {throw std::logic_error("No renderer in planet lifecycle probe");}
    VesselBase* VesselState(Vessel*) const override {throw std::logic_error("No vessels in direct planet probe");}
    void Refuel(VesselBase&) override {throw std::logic_error("No vessels in direct planet probe");}
    Vector CameraPosition() const override {throw std::logic_error("No camera in direct planet probe");}
    Vector CameraDirection() const override {throw std::logic_error("No camera in direct planet probe");}
    double CameraAperture() const override {throw std::logic_error("No camera in direct planet probe");}
    void Log(const std::string& text) override {throw std::runtime_error(text);}
    const CelestialBody& PlanetState(const Planet* planet) const override {return *planet;}
    double TerrainHeight(const Planet* planet,double longitude,double latitude) const override {return planet->Elevation(longitude,latitude);}
    const Planet* BasePlanet(const Base* base) const override {return base->RefPlanet();}
    const Body& BaseState(const Base* base) const override {return *base;}
    const Body& VesselState(const Vessel*) const override {throw std::logic_error("No vessels in direct planet probe");}
    UInt32 DockCount(const Vessel*) const override {throw std::logic_error("No vessels in direct planet probe");}
    const PortSpec* Dock(const Vessel*,UInt32) const override {throw std::logic_error("No vessels in direct planet probe");}
    Vector DockPosition(const Vessel*,const PortSpec*) const override {throw std::logic_error("No vessels in direct planet probe");}
    unsigned sizeNotifications=0,allocations=0;
};
struct Binding {
    BodyServices* oldBody;
    RigidBodyServices* oldRigid;
    CelestialServices* oldCelestial;
    SurfaceServices* oldSurface;
    NavigationServices* oldNavigation;
    Binding(Environment& environment,NativeCelestialServices& celestial):oldBody(BindBodyServices(&environment)),
        oldRigid(BindRigidBodyServices(&environment)),oldCelestial(BindCelestialServices(&celestial)),oldSurface(BindSurfaceServices(&environment)),oldNavigation(BindNavigationServices(&environment)) {}
    ~Binding() {BindNavigationServices(oldNavigation);BindSurfaceServices(oldSurface);BindCelestialServices(oldCelestial);BindRigidBodyServices(oldRigid);BindBodyServices(oldBody);}
};
}

#endif
