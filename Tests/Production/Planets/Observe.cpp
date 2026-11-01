// Licensed under the MIT License
// Direct production Planet/Base lifecycle validation, not a native application.
// Unsupported world/vessel/camera operations fail explicitly in this probe.
#include "Celbody.h"
#include "Planet.h"
#include "Base.h"
#include "Mesh.h"
#include "Vesselbase.h"
#include "Config.h"
#include "Production/SurfaceServices.h"
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
namespace {
struct Environment final : BodyServices,RigidBodyServices,SurfaceServices,NavigationServices {
    const ResourceResolver& config;
    Config settings;
    TimeData time;
    CFG_PHYSICSPRM physics{};
    explicit Environment(const ResourceResolver& c):config(c) {time.Reset(51982.5);}
    bool IsUpdating() const override {return false;}
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
    PlanetarySystem* World() const override {return nullptr;}
    const Body& Reference(const CelestialBody* body) const override {return *body;}
    Vector ReferencePosition(const CelestialBody*,double) const override {throw std::logic_error("No world propagation in direct module probe");}
    double GravityContribution(const CelestialBody*,const Vector&) const override {throw std::logic_error("No world gravity in direct module probe");}
    void ScanGravity(const PlanetarySystem*,const Vector&,const Body*,GFieldData*,bool) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector Acceleration(const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector PerturbedAcceleration(const CelestialBody*,const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector RelativeAcceleration(const Vector&,const CelestialBody*,double,const CelestialBody*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector NonsphericalAcceleration(const Vector&,const CelestialBody*) const override {throw std::logic_error("No world gravity in direct module probe");}
    void TraceAllocation(const char*,int) override {++allocations;}
    Config& Configuration() const override {return const_cast<Config&>(settings);}
    const char* Context() const override {return nullptr;}
    std::filesystem::path ConfigDirectory(const char* path) const override {
        return config.ContainsDirectory(path) ? config.ResolveDirectory(path) : config.Root()/ResourceResolver::Normalize(path);
    }
    std::filesystem::path MarkerDirectory(const char* body,const char* overridePath) const override {
        if (overridePath) return ConfigDirectory(overridePath);
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
int main(int argc,char** argv)
{
    try {
        if (argc!=6) throw std::runtime_error("Expected config, celestial data, native modules, textures and meshes roots");
        ResourceResolver config(argv[1]),data(argv[2]),modules(argv[3]),textures(argv[4]),meshes(argv[5]);
        NativeCelestialServices celestial(config,data,modules);Environment environment(config);Binding bound(environment,celestial);
        MeshServices meshServices;
        meshServices.context=&meshes;
        meshServices.path=[](void* root,const char* name) {return static_cast<ResourceResolver*>(root)->Resolve(std::string(name)+".msh");};
        meshServices.loadTexture=[](void*,const char*,UInt32)->MeshSurface {return nullptr;}; // Actual CPU mesh data, explicit headless probe.
        meshServices.releaseTexture=[](void*,MeshSurface texture) {if (texture) throw std::logic_error("Unexpected GPU resource");};
        meshServices.error=[](void*,const char* message) {throw std::runtime_error(message);};
        meshServices.allocation=[](void*,const char*,int) {};
        BindMeshServices(meshServices);
        NativeElevationServices terrain(textures,environment.time,[&](const CelestialBody& body) {
            const auto& planet=static_cast<const Planet&>(body);
            return ElevationSetup{environment.settings.CfgVisualPrm.ElevMode,environment.settings.CfgPRenderPrm.TileLoadFlags,
                std::min(14,static_cast<int>(planet.MaxPatchLevel())-7),planet.ElevationResolution()};
        },{"Earth/Archive/Elev.tree","Earth/Archive/Elev_mod.tree","Moon/Archive/Elev.tree","Mars/Archive/Elev.tree"});
        BindElevationServices(&terrain);
        for (int cycle=0;cycle<20;++cycle) {
            char sunName[]="Sun";Star sun(sunName);
            Base::CreateStaticDeviceObjects();
            for (std::string name:{"Earth","Moon","Mars"}) {
                Planet planet(name.data());planet.Attach(&sun);
                if (planet.Type()!=OBJTP_PLANET || planet.nBase()==0) throw std::runtime_error("Stock planet/bases were not loaded: "+name);
                for (UInt32 i=0;i<planet.nBase();++i) {
                    const auto* base=planet.GetBase(i);
                    {
                        Mesh **under=nullptr,**over=nullptr,**shadow=nullptr,**collision=nullptr;UInt32 nu=0,no=0,ns=0,nc=0;double* heights=nullptr;
                        base->ExportBaseStructures(&under,&nu,&over,&no);
                        base->ExportShadowGeometry(&shadow,&heights,&ns);
                        base->ExportCollisionMeshes(&collision,&nc);
                        for (UInt32 meshIndex=0;meshIndex<no;++meshIndex) if (!over[meshIndex] || !over[meshIndex]->nGroup()) throw std::runtime_error("Empty stock base mesh");
                    }
                    if (base->RefPlanet()!=&planet || !std::isfinite(base->Elevation())) throw std::runtime_error("Invalid production base state");
                }
                StateVectors surface=*planet.s0,flight=*planet.s0;
                const Vector above=mul(surface.R,Vector(planet.Size()+200000.0,0,0));
                flight.pos=surface.pos+above;
                if (std::abs(SurfParam::ComputeAltitude(flight,surface,&planet,nullptr)-200000.0)>.001)
                    throw std::runtime_error("Production vessel surface altitude transform differs");
                ATMPARAM atmosphere;
                planet.GetAtmParam(0,0,0,&atmosphere);
                if (!std::isfinite(atmosphere.T) || !std::isfinite(atmosphere.p) || !std::isfinite(atmosphere.rho)) throw std::runtime_error("Nonfinite stock atmosphere");
                const double elevation=planet.Elevation(0,0);
                if (!std::isfinite(elevation)) throw std::runtime_error("Nonfinite stock planet terrain");
                if (!cycle) std::cout<<name<<" bases="<<planet.nBase()<<" nav="<<planet.nNav()<<" elevation="<<elevation<<" pressure="<<atmosphere.p<<'\n';
            }
            Base::DestroyStaticDeviceObjects();
        }
        BindElevationServices(nullptr);BindMeshServices({});
        std::cout<<"20 actual production Planet/Base load/unload cycles passed (headless component probe)\n";
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
