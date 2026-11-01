// Licensed under the MIT License
// Real production PlanetarySystem celestial graph; no native vessel/camera/client.
#include "../Planets/Environment.h"
#include "VesselHost.h"
#include <fstream>
using namespace production_component_test;
int main(int argc,char** argv)
{
    try {
        if (argc!=7) throw std::runtime_error("Expected config, celestial data, native modules, textures, meshes and CSV path");
        ResourceResolver config(argv[1]),data(argv[2]),modules(argv[3]),textures(argv[4]),meshes(argv[5]);
        NativeCelestialServices celestial(config,data,modules);Environment environment(config);Binding bound(environment,celestial);
        MeshServices meshServices;
        meshServices.context=&meshes;
        meshServices.path=[](void* root,const char* name) {return static_cast<ResourceResolver*>(root)->Resolve(std::string(name)+".msh");};
        meshServices.loadTexture=[](void*,const char*,UInt32)->MeshSurface {return nullptr;}; // Explicit headless component probe.
        meshServices.releaseTexture=[](void*,MeshSurface texture) {if (texture) throw std::logic_error("Unexpected graphics resource");};
        meshServices.error=[](void*,const char* message) {throw std::runtime_error(message);};
        meshServices.allocation=[](void*,const char*,int) {};
        BindMeshServices(meshServices);
        NativeElevationServices terrain(textures,environment.time,[&](const CelestialBody& body) {
            const auto& planet=static_cast<const Planet&>(body);
            return ElevationSetup{environment.settings.CfgVisualPrm.ElevMode,environment.settings.CfgPRenderPrm.TileLoadFlags,
                static_cast<int>((std::min)(UInt32(14),planet.MaxPatchLevel()-UInt32(7))),planet.ElevationResolution()};
        },{"Earth/Archive/Elev.tree","Earth/Archive/Elev_mod.tree","Moon/Archive/Elev.tree","Mars/Archive/Elev.tree"});
        BindElevationServices(&terrain);WorldVesselHost vessels;BindWorldVesselServices(&vessels);
        std::ofstream output(argv[6],std::ios::binary);
        output.imbue(std::locale::classic());output.exceptions(std::ios::failbit|std::ios::badbit);
        output<<std::setprecision(17)<<"step,seconds,mjd,index,body,mass,px,py,pz,vx,vy,vz,r11,r12,r13,r21,r22,r23,r31,r32,r33\n";
        {
            char name[]="Sol";
            auto status=[](const char* text,int,void*) {std::clog<<text<<'\n';};
            PlanetarySystem world(name,&environment.settings,status,nullptr);environment.system=&world;
            if (world.nGrav()!=41 || world.nStar()!=1 || world.nPlanet()!=40 || world.nVessel()!=0)
                throw std::runtime_error("Incomplete production Sol graph");
            std::size_t baseCount=0;for (std::size_t i=0;i<world.nPlanet();++i) baseCount+=world.GetPlanet(static_cast<int>(i))->nBase();
            if (baseCount!=39) throw std::runtime_error("Incomplete production Sol surface bases");
            auto sample=[&](int step) {
                for (std::size_t i=0;i<world.nGrav();++i) {
                    const auto* body=world.GetGravObj(static_cast<int>(i));
                    const auto& p=body->GPos();const auto& v=body->GVel();const auto& r=body->GRot();
                    for (double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33})
                        if (!std::isfinite(value)) throw std::runtime_error("Nonfinite production world state");
                    output<<step<<','<<environment.time.SimT0<<','<<environment.time.MJD0<<','<<i<<','<<body->Name()<<','<<body->Mass()<<','
                        <<p.x<<','<<p.y<<','<<p.z<<','<<v.x<<','<<v.y<<','<<v.z<<','
                        <<r.m11<<','<<r.m12<<','<<r.m13<<','<<r.m21<<','<<r.m22<<','<<r.m23<<','<<r.m31<<','<<r.m32<<','<<r.m33<<'\n';
                }
            };
            sample(0);environment.time.SetFixedStep(1);
            for (int step=1;step<=6000;++step) {
                environment.time.BeginStep(1,true);environment.updating=true;
                world.Update(vessels.force);world.FinaliseUpdate();
                environment.time.EndStep(true);environment.updating=false;vessels.force=false;
                if (step%10==0) sample(step);
            }
            environment.system=nullptr;
            std::cout<<"Actual production Sol: 41 celestial bodies, 40 planets/moons, 39 bases; 6000 finalized steps\n";
        }
        output.close();
        BindWorldVesselServices(nullptr);BindElevationServices(nullptr);BindMeshServices({});return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
