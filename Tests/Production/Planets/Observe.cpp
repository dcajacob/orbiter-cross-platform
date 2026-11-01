// Licensed under the MIT License
#include "Environment.h"
using namespace production_component_test;
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
                static_cast<int>((std::min)(UInt32(14),planet.MaxPatchLevel()-UInt32(7))),planet.ElevationResolution()};
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
