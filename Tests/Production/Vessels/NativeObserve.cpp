// Licensed under the MIT License
// Actual production Vessel/PlanetarySystem and stock source-built ShuttlePB.
// This is a numerical component observer, with no native camera or renderer.
#include "../Planets/Environment.h"
#include "Vessel.h"
#include "Production/NativeWorldVesselServices.h"
#include "Production/NativeVesselModule.h"
#include "State.h"
#include "Camera.h"
#include "Production/CameraServices.h"
#include "../StockControlSchedules.h"
using namespace production_component_test;
namespace {
struct VesselEnvironment final:Environment {
    using Environment::Environment;
    VesselBase* VesselState(Vessel* vessel) const override {return vessel;}
    const Body& VesselState(const Vessel* vessel) const override {return *vessel;}
    UInt32 DockCount(const Vessel* vessel) const override {return vessel->nDock();}
    const PortSpec* Dock(const Vessel* vessel,UInt32 index) const override {return vessel->GetDockParams(index);}
    Vector DockPosition(const Vessel* vessel,const PortSpec* dock) const override {return vessel->GetDockGPos(dock);}
    void Refuel(VesselBase& vessel) override {dynamic_cast<Vessel&>(vessel).Refuel();}
    void Log(const std::string& message) override {std::clog<<message<<'\n';}
};
struct VesselHost final:VesselServices {
    VesselEnvironment& environment;
    MeshManager meshes;
    explicit VesselHost(VesselEnvironment& env):environment(env) {}
    std::filesystem::path ConfigFile(const char* name,bool extension) override {
        std::string path=ResourceResolver::Normalize(name);
        if(extension && std::filesystem::path(path).extension().empty()) path+=".cfg";
        if(environment.config.Contains(path)) return environment.config.Resolve(path);
        return environment.config.Root()/path; // Original optional Vessels/ search, then required root file.
    }
    void Fatal(const char* message) override {throw std::runtime_error(message);}
    void Check(bool valid,const char* message) override {if(!valid) throw std::logic_error(message);}
    MeshManager& Meshes() override {return meshes;}
    const char* PlaybackDirectory() const override {throw std::runtime_error("No playback selected in vessel reference");}
    void SetWarpFactor(double) override {throw std::runtime_error("Fixed-step reference cannot change time acceleration");}
    double TimejumpDelta() const override {throw std::runtime_error("No time jump selected in vessel reference");}
    void RedrawCockpitAreas(int) override {throw std::runtime_error("No cockpit in vessel reference");}
    const double* ParticleLevel(const oapi::ParticleStream*) const override {throw std::runtime_error("No particle resources in headless reference");}
    void InsertVessel(Vessel*) override {throw std::runtime_error("No dynamic creation in vessel reference");}
    double ManualControl(THGROUP_TYPE,UInt32) const override {return 0;} // No physical input device attached.
    void NotifyJump(const Vessel&,const Vector&) override {throw std::runtime_error("No origin shift in vessel reference");}
    void ShiftCockpit(const Vessel&,const Vector&) override {throw std::runtime_error("No cockpit in vessel reference");}
    std::filesystem::path RecorderFile(const char*,bool) override {throw std::runtime_error("No flight recording selected in vessel reference");}
    void PlaybackWarp(double,double) override {throw std::runtime_error("No playback in vessel reference");}
    void RecallCameraPreset(int) override {throw std::runtime_error("No camera in vessel reference");}
    void PlaybackNote(char*) override {throw std::runtime_error("No playback in vessel reference");}
    void EndPlayback() override {throw std::runtime_error("No playback in vessel reference");}
};
struct CameraHost final:CameraServices {
    VesselEnvironment& environment;Vessel* focus=nullptr;Camera* camera=nullptr;
    explicit CameraHost(VesselEnvironment& env):environment(env) {}
    Vessel* Focus() const override {return focus;}
    Config& Configuration() const override {return environment.settings;}
    void SetFocus(Vessel*) override {throw std::runtime_error("Focus change outside camera component fixture");}
    void SetFOV(double value) override {camera->SetAperture(value);}
    bool SetPanelMode(int) override {throw std::runtime_error("No cockpit in camera component fixture");}
    void SelectPanel(int) override {throw std::runtime_error("No panel in camera component fixture");}
    void SelectVC(int) override {throw std::runtime_error("No VC in camera component fixture");}
    std::filesystem::path ScenarioPath(const char* name) const override {return name;}
};

}
int main(int argc,char** argv)
{
    try {
        if(argc!=10 && argc!=11) throw std::runtime_error("Expected config, celestial data, modules, textures, meshes, master config, scenario, trace and orbit/controls mode");
        const std::string mode=argv[9];
        const bool controls=mode=="controls",behavior=mode=="rcs" || mode=="autopilot" || mode=="callbacks";
        if(!controls && !behavior && mode!="orbit") throw std::runtime_error("Unknown reference control mode");
        const int frames=mode=="rcs"?500:mode=="autopilot"?420:mode=="callbacks"?60:6000;
        const double interval=behavior?0.25:1;
        std::srand(0);
        ResourceResolver config(argv[1]),data(argv[2]),modules(argv[3]),textures(argv[4]),meshes(argv[5]);
        NativeCelestialServices celestial(config,data,modules);VesselEnvironment environment(config);
        if(!environment.settings.Load(argv[6])) throw std::runtime_error("Cannot read production master configuration");
        State metadata(51982.5);
        if(!metadata.Read(std::filesystem::path(argv[7]),51982.5) || std::string(metadata.Solsys())!="Sol")
            throw std::runtime_error("Expected production Sol scenario metadata");
        environment.time.Reset(metadata.Mjd());
        environment.physics=environment.settings.CfgPhysicsPrm;
        Binding bound(environment,celestial);
        RigidBody::GlobalSetup();
        MeshServices meshServices;meshServices.context=&meshes;
        meshServices.path=[](void* root,const char* name) {return static_cast<ResourceResolver*>(root)->Resolve(std::string(name)+".msh");};
        meshServices.loadTexture=[](void*,const char*,UInt32)->MeshSurface {return nullptr;}; // Explicit headless resource policy.
        meshServices.releaseTexture=[](void*,MeshSurface resource) {if(resource) throw std::logic_error("Unexpected headless graphics resource");};
        meshServices.error=[](void*,const char* message) {throw std::runtime_error(message);};
        meshServices.allocation=[](void*,const char*,int) {};
        BindMeshServices(meshServices);
        NativeElevationServices terrain(textures,environment.time,[&](const CelestialBody& body) {
            const auto& planet=static_cast<const Planet&>(body);
            return ElevationSetup{environment.settings.CfgVisualPrm.ElevMode,environment.settings.CfgPRenderPrm.TileLoadFlags,
                static_cast<int>((std::min)(UInt32(14),planet.MaxPatchLevel()-UInt32(7))),planet.ElevationResolution()};
        },{"Earth/Archive/Elev.tree","Earth/Archive/Elev_mod.tree","Moon/Archive/Elev.tree","Mars/Archive/Elev.tree"});
        BindElevationServices(&terrain);
        bool force=true;auto vessels=CreateNativeWorldVesselServices(force);BindWorldVesselServices(vessels.get());
        VesselHost host(environment);BindVesselServices(&host);BindNativeVesselModuleResources(&modules);
        std::ofstream output(argv[8],std::ios::binary);output.imbue(std::locale::classic());
        output.exceptions(std::ios::failbit|std::ios::badbit);output<<std::setprecision(17);
        if(behavior) output<<"tick,frame,seconds,mjd,object,class,rx,ry,rz,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,altitude_agl,altitude_mean,airspeed,density,dynamic_pressure,lift,drag,ground,dock,focus,navmask,attached\n";
        else output<<"step,seconds,mjd,object,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,ground\n";
        {
            char name[]="Sol";
            auto status=[](const char* text,int,void*) {std::clog<<text<<'\n';};
            PlanetarySystem world(name,&environment.settings,status,nullptr);environment.system=&world;
            world.InitState(argv[7]);
            if(world.nGrav()!=41 || world.nVessel()!=2) throw std::runtime_error("Incomplete stock Sol/vessel graph");
            auto* pb=world.GetVessel("PB",true);auto* iss=world.GetVessel("ISS",true);
            if(!pb || !iss || pb->GetModuleInterface()->Version()!=2 || iss->GetModuleInterface()->Version()!=0)
                throw std::runtime_error("Actual source-built ShuttlePB and config-driven ISS are required");
            auto* api=pb->GetModuleInterface();
            std::clog<<std::setprecision(17)<<"Native PB atmosphere density="<<api->GetAtmDensity()
                <<" airspeed="<<api->GetAirspeed()<<" pressure="<<api->GetDynPressure()<<'\n';
            if(api->GetThrusterCount()!=16 || api->GetPropellantCount()!=1 || api->GetMeshCount()!=1)
                throw std::runtime_error("Stock ShuttlePB capabilities differ");
            for(auto* vessel:{iss,pb}) {
                auto* interface=vessel->GetModuleInterface();
                std::clog<<vessel->Name()<<','<<interface->GetClassName()<<','<<interface->GetMeshCount()<<','
                    <<interface->GetThrusterCount()<<','<<interface->GetPropellantCount()<<'\n';
            }
            auto* focus=world.GetVessel(metadata.Focus(),true);
            if(!focus) throw std::runtime_error("Missing scenario focus vessel");
            focus->FocusChanged(true,focus,nullptr);world.PostCreation();
            CameraHost cameraHost(environment);cameraHost.focus=focus;
            BindCameraServices(&cameraHost);
            Camera camera;cameraHost.camera=&camera;
            camera.ResizeViewport(1280,720);camera.InitState(argv[7],focus);camera.Update();
            if(argc==11) {
                std::ofstream record(argv[10]);record.imbue(std::locale::classic());record.exceptions(std::ios::badbit|std::ios::failbit);
                const auto& p=*camera.GPosPtr();const auto direction=camera.Direction();const auto& r=camera.GRot();
                record<<std::setprecision(17)<<"px,py,pz,dx,dy,dz,aperture,m11,m12,m13,m21,m22,m23,m31,m32,m33\n"
                    <<p.x<<','<<p.y<<','<<p.z<<','<<direction.x<<','<<direction.y<<','<<direction.z<<','<<camera.Aperture()
                    <<','<<r.m11<<','<<r.m12<<','<<r.m13<<','<<r.m21<<','<<r.m22<<','<<r.m23<<','<<r.m31<<','<<r.m32<<','<<r.m33<<'\n';
            }
            auto behaviorSample=[&](int tick) {
                const auto* earth=world.GetGravObj("Earth",true);
                for(auto* vessel:{iss,pb}) {
                    auto* v=vessel->GetModuleInterface();VECTOR3 p{},velocity{},omega{};MATRIX3 r{};
                    v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(r);
                    const auto& ep=earth->GPos();const auto& ev=earth->GVel();
                    output<<tick<<','<<tick<<','<<environment.time.SimT0<<','<<environment.time.MJD0<<','<<v->GetName()<<','<<v->GetClassName();
                    for(double value:{p.x-ep.x,p.y-ep.y,p.z-ep.z,velocity.x-ev.x,velocity.y-ev.y,velocity.z-ev.z,
                        r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass(),
                        v->GetAltitude(ALTMODE_GROUND),v->GetAltitude(),v->GetAirspeed(),v->GetAtmDensity(),v->GetDynPressure(),v->GetLift(),v->GetDrag()}) {
                        if(!std::isfinite(value)) throw std::runtime_error("Nonfinite native behavior state");output<<','<<value;
                    }
                    unsigned mask=0;for(int nav=1;nav<=7;++nav) if(v->GetNavmodeState(nav)) mask|=1u<<nav;
                    const auto dock=v->DockCount()?v->GetDockStatus(v->GetDockHandle(0)):nullptr;
                    output<<','<<int(v->GroundContact())<<','<<(dock?static_cast<Vessel*>(dock)->Name():"")<<','<<focus->Name()<<','<<mask<<",\n";
                }
            };
            auto sample=[&](int step) {
                for(const char* object:{"Sun","Earth","Moon","ISS","PB"}) {
                    auto* vessel=world.GetVessel(object,true);
                    const Body* body=vessel?static_cast<Body*>(vessel):world.GetGravObj(object,true);
                    if(!body) throw std::runtime_error("Missing required production object");
                    const auto& p=body->GPos();const auto& v=body->GVel();const auto& r=body->GRot();
                    Vector w(0,0,0);if(vessel) w=vessel->AngularVelocity();
                    const double fuel=vessel?vessel->GetModuleInterface()->GetFuelMass():0;
                    output<<step<<','<<environment.time.SimT0<<','<<environment.time.MJD0<<','<<object;
                    for(double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,
                        w.x,w.y,w.z,body->Mass(),fuel}) {
                        if(!std::isfinite(value)) throw std::runtime_error("Nonfinite production vessel state");output<<','<<value;
                    }
                    output<<','<<(vessel && vessel->GetModuleInterface()->GroundContact()?1:0)<<'\n';
                }
            };
            if(behavior) behaviorSample(0);else sample(0);environment.time.SetFixedStep(interval);
            for(int step=0;step<frames;++step) {
                environment.time.BeginStep(interval,true);
                if(mode=="rcs") production_test::Rcs(api,step);
                else if(mode=="autopilot") production_test::Autopilot(api,step);
                else if(!behavior) {
                    api->SetThrusterGroupLevel(THGROUP_MAIN,controls && step>=100 && step<160?0.5:0);
                    api->SetThrusterGroupLevel(THGROUP_ATT_RIGHT,controls && step>=200 && step<220?0.25:0);
                    api->SetThrusterGroupLevel(THGROUP_ATT_PITCHUP,controls && step>=300 && step<305?0.1:0);
                }
                for(auto* vessel:world.GetVessels()) vessel->ModulePreStep(environment.time.SimT0,environment.time.SimDT,environment.time.MJD0);
                environment.updating=true;world.Update(force);
                for(auto* vessel:world.GetVessels()) vessel->ModulePostStep(environment.time.SimT1,environment.time.SimDT,environment.time.MJD1);
                environment.updating=false;world.FinaliseUpdate();environment.time.EndStep(true);force=false;
                if(behavior) behaviorSample(step+1);else if((step+1)%10==0) sample(step+1);
            }
            std::cout<<"Actual native production Sol, ISS and ShuttlePB: "<<frames<<" finalized steps; no camera/renderer\n";
        }
        BindCameraServices(nullptr);environment.system=nullptr;host.meshes.Flush();output.close();
        BindNativeVesselModuleResources(nullptr);BindVesselServices(nullptr);BindWorldVesselServices(nullptr);
        BindElevationServices(nullptr);BindMeshServices({});return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
