// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Narrow production external-view host. It owns real WorldOwner/Camera/Psys,
// native source modules and the original shared Session ordering, never POC state.
#include "NativeGraphics.h"
#include "NativeParticle.h"
#include "FlightControls.h"
#include "FlightReplay.h"
#include "FlightClock.h"
#include "BodyServices.h"
#include "RigidBodyServices.h"
#include "SurfaceServices.h"
#include "NavigationServices.h"
#include "VesselServices.h"
#include "CameraServices.h"
#include "NativeWorldVesselServices.h"
#include "NativeVesselModule.h"
#include "NativeCelestialServices.h"
#include "NativeElevationServices.h"
#include "MeshServices.h"
#include "GeometryConversions.h"
#include "WorldOwner.h"
#include "Session.h"
#include "Text.h"
#include "PsysCore.h"
#include "Vessel.h"
#include "Mesh.h"
#include "Planet.h"
#include "Base.h"
#include "Camera.h"
#include "Config.h"
#include "State.h"
#include "Star.h"
#include "ConfigFile.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <sstream>
using namespace orbiter::production;
namespace {
struct Resources {
    ResourceResolver program,config,data,modules,textures,highTextures,planets,meshFiles;
    Resources(const std::filesystem::path& assets,const std::filesystem::path& celestial,
        const std::filesystem::path& plugins,const std::filesystem::path& planetary)
        :program(assets),config(assets/"Config"),data(celestial),modules(plugins),textures(assets/"Textures"),
        highTextures(assets/"Textures2"),planets(planetary/"Textures"),meshFiles(assets/"Meshes") {}
};
[[noreturn]] void unsupported(const char* text) {throw std::runtime_error(std::string("Native production external view does not support ")+text);}
struct Runtime final:BodyServices,RigidBodyServices,SurfaceServices,NavigationServices,VesselServices,
    CameraServices,WorldFactory,SessionServices {
    Resources& resources;const ResourceResolver& config;Config settings;TimeData time;CFG_PHYSICSPRM physics{};
    PlanetarySystem* system=nullptr;NativeRenderContext render;bool updating=false,force=true,running=false,playback=false,active=true;
    MeshManager meshes;NativeCelestialServices celestial;std::unique_ptr<NativeElevationServices> terrain;
    std::unique_ptr<WorldVesselServices> vessels;WorldOwner world;std::unique_ptr<NativeModule> graphicsModule;
    std::ofstream lifecycle,trace,flightTrace,inputTrace,inputEvents;
    unsigned pendingCockpitRedraw=0,inputTick=0,completedTicks=0;
    FlightControls controls;FlightReplay replay;FlightInput input;
    std::unique_ptr<State> scenarioState;
    std::filesystem::path savePath;
    bool savePending=false,reloadPending=false,stepOnce=false,finished=false;
    std::string testCase;
    void Commands(const char* phase) {
        for(const auto& command:replay.Take(inputTick,phase)) {
            const double value=FlightNumber(command.value);auto* v=render.focus->GetModuleInterface();
            if(command.action=="main" || command.action=="hover") {
                if(value<0 || value>1)throw std::runtime_error("Invalid replay throttle");
                v->SetThrusterGroupLevel(command.action=="main"?THGROUP_MAIN:THGROUP_HOVER,value);
            } else if(command.action=="attitude") {if(value!=1 && value!=2 && value!=0)throw std::runtime_error("Invalid RCS mode");v->SetAttitudeMode(int(value));}
            else if(command.action=="nav") {if(value<1 || value>7 || value!=int(value))throw std::runtime_error("Invalid autopilot mode");v->ActivateNavmode(int(value));}
            else if(command.action=="navreset") {for(int mode=1;mode<=7;++mode)v->DeactivateNavmode(mode);}
            else if(command.action=="warp") SetWarpFactor(value);
            else if(command.action=="pause") {if(value!=0 && value!=1)throw std::runtime_error("Invalid pause command");running=value==0;render.paused=!running;}
            else if(command.action=="undock") {if(value<0 || value>=v->DockCount() || std::floor(value)!=value)throw std::runtime_error("Invalid docking port");if(!v->Undock(int(value)))throw std::runtime_error("Replay undocking failed");}
            else if(command.action=="save") Save();
            else if(command.action.rfind("rcs",0)==0) {
                auto token=command.action.substr(3);std::size_t end=0;auto group=std::stoul(token,&end);if(end!=token.size())throw std::runtime_error("Invalid replay RCS group");
                if(group<THGROUP_ATT_PITCHUP || group>THGROUP_ATT_BACK || value<0 || value>1)throw std::runtime_error("Invalid replay RCS group");
                v->IncThrusterGroupLevel_SingleStep(THGROUP_TYPE(group),value);
            } else if(command.action=="key") {
                if(std::abs(value)<1 || std::abs(value)>255 || std::floor(std::abs(value))!=std::abs(value))throw std::runtime_error("Invalid replay key");auto code=unsigned(std::abs(value));if(code>=256 || code!=std::abs(value))throw std::runtime_error("Invalid replay key");
                input.keys[code]=value>=0?char(0x80):0;input.events.push_back({code,value>=0});
            } else throw std::runtime_error("Unknown flight replay command: "+command.action);
        }
    }
    void Save() {
        if(savePath.empty())throw std::runtime_error("No explicit user save path");
        std::filesystem::create_directories(savePath.parent_path());auto temporary=savePath;temporary+=".tmp";
        try {
            std::ofstream file(temporary);file.exceptions(std::ios::badbit|std::ios::failbit);file.imbue(std::locale::classic());
            scenarioState->Update(time.MJD0,render.focus->Name());scenarioState->Write(file,"Native production ShuttlePB flight");
            render.camera->Write(file);system->Write(file);file.close();std::filesystem::rename(temporary,savePath);
        } catch(...) {std::error_code ignored;std::filesystem::remove(temporary,ignored);throw;}
        std::cout<<"Saved finalized production scenario: "<<savePath<<'\n';
    }
    void Buffered(FlightInput& snapshot) {
        for(auto event:snapshot.events) {
            if(inputEvents.is_open()) {
                inputEvents<<inputTick<<','<<event.code<<','<<event.down;
                for(unsigned key:{OAPI_KEY_LSHIFT,OAPI_KEY_RSHIFT,OAPI_KEY_LCONTROL,OAPI_KEY_RCONTROL,OAPI_KEY_LALT,OAPI_KEY_RALT})inputEvents<<','<<bool(KEYDOWN(snapshot.keys.data(),key));
                inputEvents<<'\n';
            }
            auto code=UInt32(event.code);
            auto& keymap=controls.keymap;
            if(event.down) {
                if(code==OAPI_KEY_SPACE || keymap.IsLogicalKey(code,snapshot.keys.data(),OAPI_LKEY_Pause)) {running=!running;render.paused=!running;continue;}
                if(keymap.IsLogicalKey(code,snapshot.keys.data(),OAPI_LKEY_Quicksave)) {savePending=true;continue;}
                if(code==OAPI_KEY_F5 && !KEYMOD_CONTROL(snapshot.keys.data())) {reloadPending=true;continue;}
                if(code==OAPI_KEY_F6 && !KEYMOD_CONTROL(snapshot.keys.data())) {stepOnce=true;continue;}
                if(keymap.IsLogicalKey(code,snapshot.keys.data(),OAPI_LKEY_Quit)) {active=false;continue;}
                if(keymap.IsLogicalKey(code,snapshot.keys.data(),OAPI_LKEY_IncSimSpeed)) {SetWarpFactor(std::pow(10.,std::floor(std::log10(time.Warp())+1e-6)+1));continue;}
                if(keymap.IsLogicalKey(code,snapshot.keys.data(),OAPI_LKEY_DecSimSpeed)) {SetWarpFactor(std::pow(10.,std::ceil(std::log10(time.Warp())-1e-6)-1));continue;}
            }
            if(running)render.focus->ConsumeBufferedKey(code,event.down,snapshot.keys.data());
        }
        snapshot.events.clear();
    }
    void InputRecord() {
        if(!inputTrace.is_open())return;
        inputTrace<<inputTick<<',';static const char hex[]="0123456789abcdef";
        for(unsigned char key:input.keys)inputTrace<<hex[key>>4]<<hex[key&15];
        inputTrace<<','<<input.x<<','<<input.y<<','<<input.rz<<','<<input.alternate<<','<<input.throttle<<'\n';
    }
    Runtime(Resources& data):resources(data),config(data.config),celestial(config,data.data,data.modules),world(*this) {}
    void Finish() {
        if(finished)return;
        if(render.graphics)render.graphics->CloseSession();world.Reset();meshes.Flush();
        if(render.graphics)render.graphics->Close();graphicsModule.reset();render.graphics=nullptr;
        for(auto* file:{&lifecycle,&trace,&flightTrace,&inputTrace,&inputEvents})if(file->is_open())file->close();
        finished=true;
    }
    ~Runtime() {
        try {Finish();}catch(const std::exception& error) {std::cerr<<"Production teardown: "<<error.what()<<'\n';}
        BindFlightControls(nullptr);BindNativeRenderContext(nullptr);BindNativeVesselModuleResources(nullptr);BindVesselServices(nullptr);
        BindCameraServices(nullptr);BindWorldVesselServices(nullptr);BindElevationServices(nullptr);BindMeshServices({});
        BindNavigationServices(nullptr);BindSurfaceServices(nullptr);BindCelestialServices(nullptr);BindRigidBodyServices(nullptr);BindBodyServices(nullptr);
    }
    void Initialize(const std::filesystem::path& master,const std::filesystem::path& scenario,const std::filesystem::path& evidence,double captureTime) {
        if(!settings.Load(master.string().c_str())) throw std::runtime_error("Cannot load explicit production configuration");
        if(!settings.GetActiveModules().empty())unsupported("application plugins in this external-view host");
        scenarioState=std::make_unique<State>(51982.5);State& metadata=*scenarioState;if(!metadata.Read(scenario,51982.5))throw std::runtime_error("Cannot parse production scenario");
        if(metadata.Script())unsupported("bundled Lua yet");
        if(!std::isfinite(metadata.Mjd()))throw std::runtime_error("Scenario epoch must be finite");
        time.Reset(metadata.Mjd());physics=settings.CfgPhysicsPrm;BindFlightControls(&controls);
        BindBodyServices(this);BindRigidBodyServices(this);BindCelestialServices(&celestial);BindSurfaceServices(this);
        BindNavigationServices(this);BindVesselServices(this);BindCameraServices(this);
        vessels=CreateNativeWorldVesselServices(force);BindWorldVesselServices(vessels.get());BindNativeVesselModuleResources(&resources.modules);
        terrain=std::make_unique<NativeElevationServices>(resources.planets,time,[&](const CelestialBody& body) {
            const auto& planet=static_cast<const Planet&>(body);
            return ElevationSetup{settings.CfgVisualPrm.ElevMode,settings.CfgPRenderPrm.TileLoadFlags,
                int((std::min)(UInt32(14),planet.MaxPatchLevel()-UInt32(7))),planet.ElevationResolution()};
        },std::vector<std::string>{"Earth/Archive/Elev.tree","Earth/Archive/Elev_mod.tree","Moon/Archive/Elev.tree","Mars/Archive/Elev.tree"});
        BindElevationServices(terrain.get());
        render.configuration=&settings;render.time=&time;render.meshes=&meshes;render.textures=&resources.textures;
        render.highTextures=&resources.highTextures;render.planetTextures=&resources.planets;render.meshFiles=&resources.meshFiles;render.programFiles=&resources.program;
        render.evidence=evidence;render.captureTime=captureTime;BindNativeRenderContext(&render);
        if(!evidence.empty()) {std::filesystem::create_directories(evidence);lifecycle.open(evidence/"application-lifecycle.csv");lifecycle.exceptions(std::ios::badbit|std::ios::failbit);lifecycle<<"event,seconds,mjd,running\n";
            trace.open(evidence/"production-state.csv");trace.imbue(std::locale::classic());trace.exceptions(std::ios::badbit|std::ios::failbit);trace<<std::setprecision(17)<<"step,seconds,mjd,object,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,ground\n";}
        if(!evidence.empty()) {
            flightTrace.open(evidence/"flight-state.csv");flightTrace.imbue(std::locale::classic());flightTrace.exceptions(std::ios::badbit|std::ios::failbit);
            flightTrace<<std::setprecision(17)<<"tick,frame,seconds,mjd,object,class,rx,ry,rz,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,altitude_agl,altitude_mean,airspeed,density,dynamic_pressure,lift,drag,ground,dock,focus,navmask,attached\n";
            inputTrace.open(evidence/"input-state.csv");inputTrace.imbue(std::locale::classic());inputTrace.exceptions(std::ios::badbit|std::ios::failbit);
            inputTrace<<std::setprecision(17)<<"tick,keys,x,y,rz,alternate,throttle\n";
            inputEvents.open(evidence/"input-events.csv");inputEvents.exceptions(std::ios::badbit|std::ios::failbit);inputEvents<<"tick,key,down,lshift,rshift,lctrl,rctrl,lalt,ralt\n";
        }
        graphicsModule=std::make_unique<NativeModule>(resources.modules.Resolve("Graphics/OGLClient.so"),ORBITER_NATIVE_GRAPHICS,&render);
        render.graphics=static_cast<NativeGraphics*>(graphicsModule->Instance());render.graphics->Open();
        MeshServices mesh;mesh.context=this;
        mesh.path=[](void* context,const char* name){return static_cast<Runtime*>(context)->resources.meshFiles.Resolve(std::string(name)+".msh");};
        mesh.loadTexture=[](void* context,const char* name,UInt32 flags) -> MeshSurface {
            auto& self=*static_cast<Runtime*>(context);auto result=self.render.graphics->LoadTextureResource(name,flags);
            if(!result)throw std::runtime_error(std::string("Required stock mesh texture could not load: ")+name);return result;
        };
        mesh.releaseTexture=[](void* context,MeshSurface texture){if(texture)static_cast<Runtime*>(context)->render.graphics->ReleaseTextureResource(texture);};
        mesh.error=[](void*,const char* text){throw std::runtime_error(text);};mesh.allocation=[](void*,const char*,int){};BindMeshServices(mesh);
        RigidBody::GlobalSetup();
        if(!world.Initialize(metadata.Solsys()))throw std::runtime_error("Production solar system contains no objects");
        system->InitState(scenario.string().c_str());
        auto* pb=system->GetVessel("PB",true);auto* iss=system->GetVessel("ISS",true);
        if(!pb || !iss || pb->GetModuleInterface()->Version()!=2 || iss->GetModuleInterface()->Version()!=0 ||
            std::string(pb->GetModuleInterface()->GetClassName())!="ShuttlePB" ||
            std::string(iss->GetModuleInterface()->GetClassName())!="ProjectAlpha_ISS" ||
            pb->GetModuleInterface()->GetMeshCount()!=1 || pb->GetModuleInterface()->GetThrusterCount()!=16 ||
            pb->GetModuleInterface()->GetPropellantCount()!=1 || iss->GetModuleInterface()->GetMeshCount()!=1)
            throw std::runtime_error("Required actual stock ISS and native ShuttlePB module/capabilities are missing; generic replacement is forbidden");
        auto* focus=system->GetVessel(metadata.Focus(),true);if(!focus)throw std::runtime_error("Required production focus vessel is missing");
        SetFocus(focus);
        render.camera->ResizeViewport(1280,720);render.camera->InitState(scenario.string().c_str(),focus);
        if(!render.camera->IsExternal())unsupported("cockpits yet; select an external camera");
        render.graphics->PostCreation();system->PostCreation();render.camera->Update();
        if(system->nGrav()!=41 || system->nVessel()!=2 || !system->GetVessel("ISS",true) || !system->GetVessel("PB",true))
            throw std::runtime_error("This native scene requires the actual stock Sol, ISS and ShuttlePB graph");
        WriteTrace();
    }
    bool IsUpdating() const override {return updating;}
    std::filesystem::path ConfigPath(const char* name) override {
        std::string path=name;if (std::filesystem::path(path).extension().empty()) path+=".cfg";
        return config.Resolve(path);
    }
    void LoadStatus(const char* path,int) override {std::clog<<"Loading production celestial config: "<<path<<'\n';}
    void SizeChanged(Body* body) override {if(render.camera && body==render.camera->Target()) render.camera->Drag(Vector(0,0,0));}
    void VisualEvent(Body* body,BodyVisual visual,BodyParameter message,BodyContent content) override {if(render.graphics) render.graphics->VisualEvent(body,visual,message,content);}
    void CheckUpdateState(bool valid) override {if (!valid) throw std::logic_error("Invalid production update state");}
    TimeData& Time() override {return time;}
    const CFG_PHYSICSPRM& Physics() const override {return physics;}
    PlanetarySystem* World() const override {return system;}
    const Body& Reference(const CelestialBody* body) const override {return *body;}
    Vector ReferencePosition(const CelestialBody* body,double fraction) const override {return body->InterpolatePosition(fraction);}
    PlanetarySystem& RequireWorld() const {if (!system) throw std::logic_error("No production world is initialized");return *system;}
    double GravityContribution(const CelestialBody* body,const Vector& position) const override {return RequireWorld().GetGravityContribution(body,position);}
    void ScanGravity(const PlanetarySystem* world,const Vector& position,const Body* exclude,GFieldData* field,bool update) const override {
        if (update) world->UpdateGFieldSources(&position,exclude,field);
        else world->ScanGFieldSources(&position,exclude,field);
    }
    Vector Acceleration(const Vector& position,double fraction,const Body* exclude,GFieldData* field) const override {return RequireWorld().Gacc_intermediate(position,fraction,exclude,field);}
    Vector PerturbedAcceleration(const CelestialBody* reference,const Vector& position,double fraction,const Body* exclude,GFieldData* field) const override {return RequireWorld().Gacc_intermediate_pert(reference,position,fraction,exclude,field);}
    Vector RelativeAcceleration(const Vector& position,const CelestialBody* reference,double fraction,const CelestialBody* exclude,GFieldData* field) const override {return RequireWorld().GaccRel(position,reference,fraction,exclude,field);}
    Vector NonsphericalAcceleration(const Vector& position,const CelestialBody* reference) const override {return SingleGacc_perturbation(position,reference);}
    void TraceAllocation(const char*,int) override {} // No memory-allocation diagnostic sink selected.
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
    bool HasGraphics() const override {return render.graphics!=nullptr;}
    SURFHANDLE LoadTexture(const char* name,bool) override {auto result=render.graphics->LoadTextureResource(name,0);if(!result) throw std::runtime_error(std::string("Required engine texture failed: ")+name);return result;}
    void ReleaseTexture(SURFHANDLE texture,bool) override {if(texture && !render.graphics->ReleaseTextureResource(texture)) throw std::runtime_error("Texture release failed");}
    VesselBase* VesselState(Vessel* vessel) const override {return vessel;}
    void Refuel(VesselBase& vessel) override {vessel.Refuel();}
    Vector CameraPosition() const override {return render.camera->GPos();}
    Vector CameraDirection() const override {return render.camera->Direction();}
    double CameraAperture() const override {return render.camera->Aperture();}
    void Log(const std::string& text) override {std::clog<<text<<'\n';}
    const CelestialBody& PlanetState(const Planet* planet) const override {return *planet;}
    double TerrainHeight(const Planet* planet,double longitude,double latitude) const override {return planet->Elevation(longitude,latitude);}
    const Planet* BasePlanet(const Base* base) const override {return base->RefPlanet();}
    const Body& BaseState(const Base* base) const override {return *base;}
    const Body& VesselState(const Vessel* vessel) const override {return *vessel;}
    UInt32 DockCount(const Vessel* vessel) const override {return vessel->nDock();}
    const PortSpec* Dock(const Vessel* vessel,UInt32 index) const override {return vessel->GetDockParams(index);}
    Vector DockPosition(const Vessel* vessel,const PortSpec* dock) const override {return vessel->GetDockGPos(dock);}

    std::filesystem::path ConfigFile(const char* name,bool extension) override {
        std::string path=ResourceResolver::Normalize(name);if(extension && std::filesystem::path(path).extension().empty())path+=".cfg";
        return config.Contains(path)?config.Resolve(path):config.Root()/path;
    }
    void Fatal(const char* text) override {throw std::runtime_error(text);}
    void Check(bool valid,const char* text) override {if(!valid)throw std::logic_error(text);}
    MeshManager& Meshes() override {return meshes;}
    const char* PlaybackDirectory() const override {unsupported("flight playback yet");}
    void SetWarpFactor(double warp) override {
        if(!std::isfinite(warp) || warp<=0)throw std::runtime_error("Invalid time acceleration");
        time.SetWarp(std::clamp(warp,.1,100000.));
    }
    double TimejumpDelta() const override {unsupported("time jumps in this scene host");}
    void RedrawCockpitAreas(int flags) override {pendingCockpitRedraw|=unsigned(flags);} // No Panel/VC areas are registered in external-view scope.
    const double* ParticleLevel(const oapi::ParticleStream* stream) const override {return stream->Level();}
    void InsertVessel(Vessel*) override {unsupported("dynamic vessel creation yet");}
    double ManualControl(THGROUP_TYPE group,UInt32 device) const override {return controls.Manual(group,device);}
    void NotifyJump(const Vessel& vessel,const Vector& delta) override {if(&vessel==render.camera->Target())render.camera->Drag(-delta);if(render.camera->Target())render.camera->Update();}
    void ShiftCockpit(const Vessel&,const Vector&) override {unsupported("virtual cockpit movement yet");}
    std::filesystem::path RecorderFile(const char*,bool) override {unsupported("flight recording yet");}
    void PlaybackWarp(double,double) override {unsupported("playback time acceleration yet");}
    void RecallCameraPreset(int index) override {render.camera->RecallPreset(index);}
    void PlaybackNote(char*) override {unsupported("playback annotations yet");}
    void EndPlayback() override {unsupported("flight playback yet");}
    Vessel* Focus() const override {return render.focus;}
    void SetFocus(Vessel* vessel) override {
        if(vessel==render.focus)return;auto* previous=render.focus;render.focus=vessel;
        if(previous)previous->FocusChanged(false,vessel,previous);vessel->FocusChanged(true,vessel,previous);
    }
    void SetFOV(double value) override {if(render.camera->Aperture()!=value){render.camera->SetAperture(value);force=true;}}
    bool SetPanelMode(int) override {unsupported("cockpit panels yet");}
    void SelectPanel(int) override {unsupported("2D panels yet");}
    void SelectVC(int) override {unsupported("virtual cockpits yet");}
    std::filesystem::path ScenarioPath(const char* name) const override {return name;}
    Camera* CreateCamera() override {return render.camera=new Camera;}
    PlanetarySystem* CreateSystem(const char* name) override {
        auto status=[](const char* text,int,void*) {std::clog<<text<<'\n';};
        return render.world=system=new PlanetarySystem(const_cast<char*>(name),&settings,status,nullptr);
    }
    bool HasObjects(const PlanetarySystem* body) const override {return body->nObj()!=0;}
    void DestroyCamera(Camera* camera) noexcept override {delete camera;render.camera=nullptr;}
    void DestroySystem(PlanetarySystem* body) noexcept override {delete body;render.world=system=nullptr;}
    void Observe(const char* event,bool state) override {if(lifecycle.is_open())lifecycle<<event<<','<<time.SimT0<<','<<time.MJD0<<','<<state<<'\n';}
    void ModulePreStep() override {Commands("pre");for(auto* vessel:system->GetVessels())vessel->ModulePreStep(time.SimT0,time.SimDT,time.MJD0);}
    void PlaybackStep() override {unsupported("playback yet");}
    void UpdateBodies(bool update) override {system->Update(update);}
    void UpdateDialogs() override {} // No dialogs are instantiated in external-view scope.
    void ModulePostStep() override {for(auto* vessel:system->GetVessels())vessel->ModulePostStep(time.SimT1,time.SimDT,time.MJD1);}
    bool DeletePendingVessels() override {for(auto* vessel:system->GetVessels())if(vessel->KillPending())unsupported("dynamic vessel deletion yet");return system->nVessel()!=0;}
    void NoVessels() override {active=false;}
    void FinaliseBodies() override {system->FinaliseUpdate();}
    void AdvanceTime(bool state) override {time.EndStep(state);if(state)++completedTicks;}
    void WriteTrace() override {
        if(flightTrace.is_open()) {
            const auto& ep=system->GetGravObj("Earth",true)->GPos();const auto& ev=system->GetGravObj("Earth",true)->GVel();
            for(auto* vessel:{system->GetVessel("ISS",true),system->GetVessel("PB",true)}) {
                auto* v=vessel->GetModuleInterface();VECTOR3 p{},velocity{},omega{};MATRIX3 r{};
                v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(r);
                flightTrace<<completedTicks<<','<<time.FrameCount()<<','<<time.SimT0<<','<<time.MJD0<<','<<v->GetName()<<','<<v->GetClassName();
                for(double value:{p.x-ep.x,p.y-ep.y,p.z-ep.z,velocity.x-ev.x,velocity.y-ev.y,velocity.z-ev.z,
                    r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass(),
                    v->GetAltitude(ALTMODE_GROUND),v->GetAltitude(),v->GetAirspeed(),v->GetAtmDensity(),v->GetDynPressure(),v->GetLift(),v->GetDrag()}) {
                    if(!std::isfinite(value))throw std::runtime_error("Nonfinite flight state");flightTrace<<','<<value;
                }
                unsigned mask=0;for(int nav=1;nav<=7;++nav)if(v->GetNavmodeState(nav))mask|=1u<<nav;
                auto dock=v->DockCount()?v->GetDockStatus(v->GetDockHandle(0)):nullptr;
                flightTrace<<','<<int(v->GroundContact())<<','<<(dock?static_cast<Vessel*>(dock)->Name():"")<<','<<render.focus->Name()<<','<<mask<<",\n";
            }
        }
        if(!trace.is_open())return;
        for(const char* name:{"Sun","Earth","Moon","ISS","PB"}) {
            auto* vessel=system->GetVessel(name,true);const Body* body=vessel?static_cast<const Body*>(vessel):system->GetGravObj(name,true);
            if(!body)throw std::runtime_error("Required production trace body missing");
            const auto& p=body->GPos();const auto& v=body->GVel();const auto& r=body->GRot();Vector w(0,0,0);if(vessel)w=vessel->AngularVelocity();
            trace<<time.FrameCount()<<','<<time.SimT0<<','<<time.MJD0<<','<<name;
            for(double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,w.x,w.y,w.z,body->Mass(),vessel?vessel->GetModuleInterface()->GetFuelMass():0}) {
                if(!std::isfinite(value))throw std::runtime_error("Nonfinite production state");trace<<','<<value;
            }
            trace<<','<<(vessel && vessel->GetModuleInterface()->GroundContact()?1:0)<<'\n';
        }
    }
    void UpdateCamera() override {render.camera->Update();}
    void UpdatePanels(double,double) override {} // No Panel object is selected.
    void UpdateVisuals(bool) override {} // This client updates its visuals in the original Scene::Render phase, as on Windows.
    void CheckSessionLimit() override {}
    std::string Status() const {
        auto* v=render.focus->GetModuleInterface();std::ostringstream text;text.imbue(std::locale::classic());
        text<<"Orbiter | "<<v->GetName()<<" | "<<(running?"RUNNING":"PAUSED")<<" t="<<std::fixed<<std::setprecision(3)<<time.SimT0<<"s"
            <<" | RCS "<<(v->GetAttitudeMode()==1?"ROT":v->GetAttitudeMode()==2?"LIN":"OFF")
            <<" | MAIN "<<std::setprecision(0)<<v->GetThrusterGroupLevel(THGROUP_MAIN)*100<<"% HOV "<<v->GetThrusterGroupLevel(THGROUP_HOVER)*100<<"%"
            <<" | fuel "<<std::setprecision(3)<<v->GetFuelMass()<<"kg | x"<<time.Warp();
        if(auto dock=v->DockCount()?v->GetDockStatus(v->GetDockHandle(0)):nullptr)text<<" | DOCKED "<<static_cast<Vessel*>(dock)->Name();
        else text<<" | ISS "<<std::setprecision(1)<<render.focus->GPos().dist(system->GetVessel("ISS",true)->GPos())<<"m";
        return text.str();
    }
    void Step(double dt) {
        Commands("before");Buffered(input);InputRecord();
        const bool wasRunning=running;if(stepOnce){running=true;stepOnce=false;}
        render.paused=!running;time.BeginStep(dt,running);
        if(running)controls.Immediate(*render.focus,time,input);
        Session::UpdateWorld(*this,time,running,playback,updating,force);
        Session::EndTimeStep(*this,time,running,active,force);
        if(!wasRunning)running=false;
        input.throttle=-1;Commands("after");render.paused=!running;if(savePending){Save();savePending=false;}++inputTick;
    }
};
}
int main(int argc,char** argv) {
    try {
        std::map<std::string,std::string> arguments;
        for(int i=1;i<argc;++i) {
            std::string name=argv[i];
            if(name=="--help") {std::cout<<"orbiter-production --assets PATH --data PATH --modules PATH --planets PATH --config PATH --scenario PATH [--keymap PATH --save PATH --replay PATH --evidence PATH --fixed-step S --ticks N --render-every N --frames N --sessions N --run]\n";return 0;}
            if(name.rfind("--",0)!=0 || arguments.count(name))throw std::runtime_error("Invalid or duplicate argument: "+name);
            if(name=="--run"){arguments[name]="1";continue;}
            if(i+1==argc || std::string(argv[i+1]).rfind("--",0)==0)throw std::runtime_error("Argument value missing: "+name);
            arguments[name]=argv[++i];
        }
        const std::vector<std::string> allowed={"--assets","--data","--modules","--planets","--config","--scenario","--evidence","--frames","--fixed-step","--run","--capture-time","--keymap","--save","--replay","--ticks","--render-every","--sessions","--joystick-throttle-axis","--joystick-twist-axis"};
        for(const auto& entry:arguments)if(std::find(allowed.begin(),allowed.end(),entry.first)==allowed.end())throw std::runtime_error("Unknown argument: "+entry.first);
        for(const char* name:{"--assets","--data","--modules","--planets","--config","--scenario"})if(!arguments.count(name))throw std::runtime_error(std::string("Required argument missing: ")+name);
        const auto absolute=[&](const char* name){return std::filesystem::absolute(arguments.at(name));};
        auto integer=[&](const char* name,int fallback){if(!arguments.count(name))return fallback;double n=FlightNumber(arguments.at(name));if(n<0 || n>10000000 || n!=int(n))throw std::runtime_error(std::string("Invalid integer: ")+name);return int(n);};
        const int frames=integer("--frames",0),ticks=integer("--ticks",0),renderEvery=integer("--render-every",1),sessions=integer("--sessions",1);
        const double fixed=arguments.count("--fixed-step")?FlightNumber(arguments.at("--fixed-step")):1.0/60.0;
        const double capture=arguments.count("--capture-time")?FlightNumber(arguments.at("--capture-time")):-1;
        if(fixed<=0 || (arguments.count("--capture-time") && capture<0) || !renderEvery || !sessions || (ticks && frames))throw std::runtime_error("Invalid frame/step/capture/session limits");
        std::srand(0);Resources resources(absolute("--assets"),absolute("--data"),absolute("--modules"),absolute("--planets"));
        std::filesystem::path scenario=absolute("--scenario");
        const auto evidence=arguments.count("--evidence")?absolute("--evidence"):std::filesystem::path{};
        std::filesystem::path save;
        if(arguments.count("--save"))save=absolute("--save");
        else {const char* data=std::getenv("XDG_DATA_HOME");const char* home=std::getenv("HOME");if(data && *data)save=std::filesystem::path(data)/"orbiter/Scenarios/Quicksave.scn";else if(home)save=std::filesystem::path(home)/".local/share/orbiter/Scenarios/Quicksave.scn";else throw std::runtime_error("Provide --save or a user data directory");}
        unsigned launches=0;bool startRunning=arguments.count("--run")!=0;
        for(int session=0;session<sessions;++session) {
            Runtime application(resources);
            ++launches;
            const auto output=evidence.empty() || (sessions==1 && launches==1)?evidence:evidence/("session-"+std::to_string(launches));
            application.render.joystickThrottleAxis=integer("--joystick-throttle-axis",-1);
            application.render.joystickTwistAxis=integer("--joystick-twist-axis",2);
            if(application.render.joystickThrottleAxis>15 || application.render.joystickTwistAxis>15)throw std::runtime_error("Invalid joystick axis");
            application.savePath=save;application.Initialize(absolute("--config"),scenario,output,capture);
            if(arguments.count("--keymap") && (!std::filesystem::is_regular_file(absolute("--keymap")) || !application.controls.keymap.Read(absolute("--keymap").string().c_str())))throw std::runtime_error("Cannot load explicit flight keymap");
            if(arguments.count("--replay"))application.replay.Load(absolute("--replay"));
            application.time.SetFixedStep(fixed);application.running=startRunning;application.render.paused=!application.running;
            std::cout<<"Production ShuttlePB flight. Space/Ctrl-P: pause. T/R: warp. Ctrl-S: save. F5: reload. F6: step. Escape: close.\n";
            FlightClock clock(fixed);auto previous=std::chrono::steady_clock::now();
            int presented=0;bool reload=false;
            while(application.active && (!frames || presented<frames) && (!ticks || application.inputTick<unsigned(ticks))) {
                auto input=application.render.graphics->Poll();if(input.close)break;
                if(!frames && !ticks && !arguments.count("--replay")) {
                    application.input.keys=input.flight.keys;
                    application.input.events.insert(application.input.events.end(),input.flight.events.begin(),input.flight.events.end());
                    application.input.x=input.flight.x;application.input.y=input.flight.y;application.input.rz=input.flight.rz;application.input.alternate=input.flight.alternate;
                    if(input.flight.throttle>=0)application.input.throttle=input.flight.throttle;
                    application.render.camera->ShiftPhi(input.yaw);application.render.camera->ShiftTheta(input.pitch);
                    if(input.zoom)application.render.camera->ChangeDist(std::pow(1.1,-input.zoom));
                }
                if(input.width>0 && input.height>0){application.render.graphics->Resize(input.width,input.height);application.render.camera->ResizeViewport(input.width,input.height);}
                if(frames || ticks) {
                    for(int n=0;n<(ticks?renderEvery:1) && (!ticks || application.inputTick<unsigned(ticks));++n)application.Step(fixed);
                } else {
                    auto now=std::chrono::steady_clock::now();clock.Add(std::chrono::duration<double>(now-previous).count());previous=now;
                    int count=0;while(count<256 && application.active && !application.reloadPending && clock.Tick()) {application.Step(fixed);++count;}
                    // Buffered actions remain responsive even without a due physics tick.
                    application.Buffered(application.input);
                    if(application.savePending && !application.stepOnce){application.Save();application.savePending=false;}
                }
                if(application.reloadPending) {if(!std::filesystem::is_regular_file(save)){std::cerr<<"No saved scenario exists: "<<save<<'\n';application.reloadPending=false;}else{scenario=save;reload=true;break;}}
                if(input.width>0 && input.height>0) {
                    application.render.paused=!application.running;application.render.graphics->Status(application.Status());application.render.graphics->Render();if(!application.render.graphics->Present())throw std::runtime_error("Native frame presentation failed");++presented;
                } else std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            if((ticks || frames) && !application.replay.Empty())throw std::runtime_error("Unconsumed flight replay commands");
            application.Finish();
            if(reload) {startRunning=application.running;--session;continue;}
        }
        return 0;
    } catch(const std::exception& error) {std::cerr<<"Orbiter native production: "<<error.what()<<'\n';return 1;}
}
