// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "Random.h"
#include "VesselLifetime.h"
#include "NativeObservation/ApplicationObservation.h"
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
#ifdef ORBITER_NATIVE_COCKPIT
#include "Pane.h"
#include "Select.h"
#include "NativeCockpitUi.h"
#include "NativeAnnotations.h"
#include "NativeScript.h"
#include "NativeInterpreterSdk.h"
#include "SystemPlayback.h"
#include "PlaybackObservation.h"
#include "CockpitSystemClock.h"
#include "CockpitServices.h"
#endif
#include "Star.h"
#include "ConfigFile.h"
#include "MathObservation.h"
#include "ContactObservation.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>
#include <limits>
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
double RcsLevel(const VESSEL& vessel) {
    double level=0;
    for(int group=THGROUP_ATT_PITCHUP;group<=THGROUP_ATT_BACK;++group)
        level=std::max(level,vessel.GetThrusterGroupLevel(THGROUP_TYPE(group)));
    return level;
}
int ReadFlightStatus(const VESSEL& vessel) {
    VESSELSTATUS2 status{};status.version=2;vessel.GetStatusEx(&status);return status.status;
}
bool SupportedStockStation(const VESSEL& vessel,const char* type) {
    const bool mir=CompareText(type,"Mir")==0,wheel=CompareText(type,"Wheel")==0;
    const bool legacy=CompareText(type,"ISS")==0,module=CompareText(type,"Module1")==0;
    if((!mir && !wheel && !legacy && !module) || vessel.Version()!=0 || vessel.GetEnableFocus()!=module || vessel.GetMeshCount()!=1 ||
       vessel.GetThrusterCount()!=0 || vessel.GetPropellantCount()!=0 || vessel.AttachmentCount(true)!=0 ||
       vessel.AttachmentCount(false)!=0 || bool(vessel.GetTransponder())!=!module || vessel.GetFuelMass()!=0 ||
       vessel.GetMass()!=vessel.GetEmptyMass())return false;
    VECTOR3 pmi{},cs{};vessel.GetPMI(pmi);vessel.GetCrossSections(cs);
    const auto dock=[&](oapi::UInt index,const VECTOR3& position,const VECTOR3& direction,const VECTOR3& rotation) {
        const auto handle=vessel.GetDockHandle(index);if(!handle)return false;
        VECTOR3 p{},d{},r{};vessel.GetDockParams(handle,p,d,r);
        return p.x==position.x && p.y==position.y && p.z==position.z &&
               d.x==direction.x && d.y==direction.y && d.z==direction.z &&
               r.x==rotation.x && r.y==rotation.y && r.z==rotation.z;
    };
    // Original ISS/Module1 capabilities and local ports are independently
    // audited in LegacyStations/observations.lock.json. Native parity remains
    // a separate gate; no declared module may fall back to a generic vessel.
    if(legacy)
        return vessel.GetEmptyMass()==450000 && vessel.GetSize()==55 && vessel.DockCount()==3 &&
            pmi.x==395 && pmi.y==559 && pmi.z==290 && cs.x==897.2 && cs.y==3641.3 && cs.z==610.8 &&
            dock(0,_V(13.67,5.56,0),_V(1,0,0),_V(0,1,0)) &&
            dock(1,_V(-4.32,17.6,0),_V(0,1,0),_V(1,0,0)) &&
            dock(2,_V(-36,4.21,0),_V(-1,0,0),_V(0,-1,0));
    if(module)
        return vessel.GetEmptyMass()==8000 && vessel.GetSize()==6 && vessel.DockCount()==2 &&
            pmi.x==7.7 && pmi.y==7.7 && pmi.z==2.3 && cs.x==20 && cs.y==20 && cs.z==20 &&
            dock(0,_V(0,0,5),_V(0,0,1),_V(0,1,0)) && dock(1,_V(0,0,-5),_V(0,0,-1),_V(0,1,0));
    // Explicit original configuration-defined classes, qualified against the
    // preserved Windows application. Required modules still use the loader.
    return (mir && vessel.GetEmptyMass()==124340 && vessel.GetSize()==40 && vessel.DockCount()==3 &&
            pmi.x==86.1 && pmi.y==79.6 && pmi.z==37 && cs.x==186.8 && cs.y==272.9 && cs.z==341.1) ||
           (wheel && vessel.GetEmptyMass()==1e6 && vessel.GetSize()==250 && vessel.DockCount()==2 &&
            pmi.x==26000 && pmi.y==26000 && pmi.z==52800 && cs.x==20 && cs.y==20 && cs.z==20);
}
#ifdef ORBITER_NATIVE_COCKPIT
bool SupportedRemainingStock(const Vessel& body,const VESSEL& vessel,const char* type) {
    struct Capabilities {
        const char* type;
        const char* module;
        int version;
        bool focus;
        double size;
        unsigned meshes,thrusters,propellants,docks,parents,children;
        bool transponder;
    };
    // The sixteen initial structural combinations observed in the preserved
    // original Windows cohort. Diagnostic admission ranges are not reused.
    static constexpr Capabilities qualified[]={
        {"Atlantis","Atlantis",3,true,19.6,3,19,1,1,0,2,false},
        {"Atlantis","Atlantis",3,true,19.6,3,19,1,2,0,2,false},
        {"Atlantis","Atlantis",3,true,19.6,4,19,1,1,0,2,false},
        {"Atlantis","Atlantis",3,true,19.6,4,19,1,2,0,2,false},
        {"Atlantis_SRB","Atlantis_SRB",1,false,23,1,2,1,1,0,0,false},
        {"Atlantis_SRB","Atlantis_SRB",1,false,51.397999999999996,1,2,1,1,0,0,false},
        {"Atlantis_SRB","Atlantis_SRB",1,false,51.399,1,2,1,1,0,0,false},
        {"Atlantis_Tank","Atlantis_Tank",1,false,24,1,21,1,3,0,0,false},
        {"Carina",nullptr,0,true,5,1,21,1,0,2,0,false},
        {"Dragonfly","Dragonfly",1,true,4,1,25,12,1,0,0,false},
        {"HST","HST",2,true,7.52,1,0,0,0,3,0,false},
        {"LDEF",nullptr,0,true,12,1,18,1,0,2,1,true},
        {"Leonardo_mplm",nullptr,0,true,6,1,0,0,1,2,0,true},
        {"Module2",nullptr,0,true,2.5,1,0,0,6,0,0,false},
        {"Quadcopter","Quadcopter",3,true,.3,1,1,1,0,0,0,false},
        {"SolarSail","SolarSail",2,true,1000,1,0,0,1,0,0,false}
    };
    const char* module=NativeVesselModuleName(body);
    for(const auto& caps:qualified) {
        if(CompareText(type,caps.type)!=0 || (caps.module?
           (!module || CompareText(module,caps.module)!=0):module!=nullptr))continue;
        if(vessel.Version()==caps.version && vessel.GetEnableFocus()==caps.focus &&
           vessel.GetSize()==caps.size && vessel.GetMeshCount()==caps.meshes &&
           vessel.GetThrusterCount()==caps.thrusters && vessel.GetPropellantCount()==caps.propellants &&
           vessel.DockCount()==caps.docks && vessel.AttachmentCount(true)==caps.parents &&
           vessel.AttachmentCount(false)==caps.children && bool(vessel.GetTransponder())==caps.transponder)
            return true;
    }
    return false;
}
bool SupportedStockShuttleA(const VESSEL& vessel,const char* type) {
    // Initial capabilities observed in all four preserved Windows profiles.
    // Declared modules still have to load through the checked native factory.
    if(!vessel.GetEnableFocus() || !vessel.GetTransponder() || vessel.DockCount()!=1)return false;
    VECTOR3 pmi{},cs{};vessel.GetPMI(pmi);vessel.GetCrossSections(cs);
    if(CompareText(type,"ShuttleA")==0)
        return vessel.Version()==3 && vessel.GetSize()==17 && vessel.GetMeshCount()==2 &&
            vessel.GetThrusterCount()==20 && vessel.GetPropellantCount()==2 &&
            vessel.AttachmentCount(true)==0 && vessel.AttachmentCount(false)==6 &&
            pmi.x==86.6 && pmi.y==89.8 && pmi.z==5.5 && cs.x==132.2 && cs.y==237.9 && cs.z==42.4;
    if(CompareText(type,"ShuttleA_pl")==0)
        return vessel.Version()==1 && vessel.GetSize()==5 && vessel.GetMeshCount()==1 &&
            vessel.GetThrusterCount()==0 && vessel.GetPropellantCount()==0 &&
            vessel.AttachmentCount(true)==3 && vessel.AttachmentCount(false)==0 &&
            vessel.GetEmptyMass()==20000 && vessel.GetFuelMass()==0 &&
            pmi.x==2.56 && pmi.y==2.39 && pmi.z==2.02 &&
            cs.x==17.61f && cs.y==17.44f && cs.z==13.09f;
    return false;
}
#if defined(ORBITER_ATLANTIS_DIAGNOSTIC) || defined(ORBITER_REMAINING_STOCK_DIAGNOSTIC)
// An isolated test executable exercises the actual, not-yet-qualified modules.
// The production executable retains its admission checks below.
bool SupportedAtlantisDiagnostic(const VESSEL& vessel,const char* type) {
    if(CompareText(type,"Atlantis")==0)
        return vessel.Version()==3 && vessel.GetSize()==19.6 &&
            vessel.GetMeshCount()>=3 && vessel.GetMeshCount()<=5 &&
            vessel.GetThrusterCount()==19 && vessel.GetPropellantCount()==1 &&
            vessel.DockCount()>=1 && vessel.DockCount()<=2 &&
            vessel.AttachmentCount(true)==0 && vessel.AttachmentCount(false)==2;
    if(CompareText(type,"Atlantis_Tank")==0)
        return vessel.Version()==1 && !vessel.GetEnableFocus() && vessel.GetSize()==24 &&
            vessel.GetMeshCount()==1 && vessel.GetThrusterCount()==21 &&
            vessel.GetPropellantCount()==1 && vessel.DockCount()==3;
    if(CompareText(type,"Atlantis_SRB")==0)
        return vessel.Version()==1 && !vessel.GetEnableFocus() && vessel.GetSize()>=23 &&
            vessel.GetMeshCount()==1 && vessel.GetThrusterCount()==2 &&
            vessel.GetPropellantCount()==1 && vessel.DockCount()==1;
    return false;
}
#endif
#ifdef ORBITER_REMAINING_STOCK_DIAGNOSTIC
bool SupportedRemainingStockDiagnostic(const VESSEL& vessel,const char* type) {
    if(vessel.GetMeshCount()!=1)return false;
    if(CompareText(type,"HST")==0)
        return vessel.Version()==2 && vessel.GetEmptyMass()==10886 && vessel.GetSize()==7.52;
    if(CompareText(type,"Dragonfly")==0)
        return vessel.Version()==1 && vessel.GetEmptyMass()==7000 && vessel.GetSize()==4 &&
            // Original ShipInternal::Init adds eleven vent jets/tanks before
            // SetClassCaps adds the fourteen RCS thrusters and main propellant.
            vessel.GetThrusterCount()==25 && vessel.GetPropellantCount()==12 && vessel.DockCount()==1;
    if(CompareText(type,"SolarSail")==0)
        return vessel.Version()==2 && vessel.GetEmptyMass()==100 && vessel.GetSize()==1000;
    if(CompareText(type,"Quadcopter")==0)
        return vessel.Version()==3 && vessel.GetEmptyMass()==2 && vessel.GetSize()==0.3 &&
            vessel.GetThrusterCount()==1 && vessel.GetPropellantCount()==1;
    if(vessel.Version()!=0)return false;
    if(CompareText(type,"Carina")==0)
        return vessel.GetEmptyMass()==5000 && vessel.GetSize()==5 && vessel.AttachmentCount(true)==2;
    if(CompareText(type,"LDEF")==0)
        return vessel.GetEmptyMass()==2500 && vessel.GetSize()==12 && vessel.AttachmentCount(true)==2 &&
            vessel.AttachmentCount(false)==1;
    if(CompareText(type,"Leonardo_mplm")==0)
        return vessel.GetEmptyMass()==1800 && vessel.GetSize()==6 && vessel.AttachmentCount(true)==2;
    if(CompareText(type,"Module2")==0)
        return vessel.GetEmptyMass()==4000 && vessel.GetSize()==2.5 && vessel.DockCount()==6;
    return false;
}
#endif
#endif
struct Runtime final:BodyServices,RigidBodyServices,SurfaceServices,NavigationServices,VesselServices,
    CameraServices,WorldFactory,SessionServices,VesselLifetimeServices
#ifdef ORBITER_NATIVE_COCKPIT
    , ScriptApplication
#endif
{
    Resources& resources;const ResourceResolver& config;Config settings;TimeData time;CFG_PHYSICSPRM physics{};
    PlanetarySystem* system=nullptr;NativeRenderContext render;bool updating=false,force=true,running=false,playback=false,active=true;
    MeshManager meshes;NativeCelestialServices celestial;std::unique_ptr<NativeElevationServices> terrain;
    std::unique_ptr<WorldVesselServices> vessels;WorldOwner world;std::unique_ptr<NativeModule> graphicsModule;
    std::ofstream lifecycle,trace,flightTrace,inputTrace,inputEvents,thrustTrace,animationTrace,controlTrace,mathTrace,contactTrace;
    unsigned pendingCockpitRedraw=0,inputTick=0,completedTicks=0,observationTick=0;
    FlightControls controls;FlightReplay replay;FlightInput input;
#ifdef ORBITER_NATIVE_COCKPIT
    NativeAnnotations annotations;
    std::string playbackDirectory;
    std::ifstream systemPlayback;
    bool recording=false;
    std::string recordingName;
    std::filesystem::path localPlaybackRoot;
    std::filesystem::path initialScenario;
    double nextPlaybackEvent=0;
    NativeScriptHost scripts{resources.modules};
    std::array<char,256> simulatedKeys{};
    TimeJumpData scriptJump{};
    INTERPRETERHANDLE scenarioInterpreter=nullptr;
    std::unique_ptr<Pane> cockpit;
    bool instrumentResources=false,cockpitObserved=false,guiCreated=false;
    std::ofstream cockpitState,playbackTrace;
    CockpitSystemClock cockpitClock;
    unsigned paneMouseCapture=0;
    bool observeControls=false;
    std::ofstream cockpitMouse;
#endif
    std::unique_ptr<State> scenarioState;
    std::filesystem::path savePath;
    std::filesystem::path optionsPath;
    Vessel* previousFocus=nullptr;
    struct AttachmentPair {Vessel* parent;ATTACHMENTHANDLE parentHandle,childHandle;};
    std::map<std::string,AttachmentPair> attachments;
    std::ofstream vesselCallbacks,lifetimeEvents;
    bool savePending=false,reloadPending=false,stepOnce=false,finished=false,baseResources=false;
    std::string testCase;
#ifdef ORBITER_NATIVE_COCKPIT
    static const char* MouseName(RenderMouseAction action) {
        switch(action) {
        case RenderMouseAction::Move:return "move";
        case RenderMouseAction::LeftDown:return "left_down";
        case RenderMouseAction::LeftUp:return "left_up";
        case RenderMouseAction::RightDown:return "right_down";
        case RenderMouseAction::RightUp:return "right_up";
        case RenderMouseAction::Wheel:return "wheel";
        }
        throw std::invalid_argument("Unknown native mouse event");
    }
    bool Mouse(const RenderMouseEvent& mouse) {
        if(cockpitMouse.is_open()){cockpitMouse<<inputTick<<','<<MouseName(mouse.action)<<','<<mouse.x<<','<<mouse.y<<'\n';cockpitMouse.flush();}
        // Original Orbiter::MouseEvent excludes movement before Pane dispatch.
        if(mouse.action==RenderMouseAction::Move)return false;
        oapi::UInt event=0;oapi::UInt32 state=0;unsigned button=0;bool down=false;
        switch(mouse.action) {
        case RenderMouseAction::LeftDown:event=CockpitMouse::LeftDown;state=1;button=1;down=true;break;
        case RenderMouseAction::LeftUp:event=CockpitMouse::LeftUp;button=1;break;
        case RenderMouseAction::RightDown:event=CockpitMouse::RightDown;state=2;button=2;down=true;break;
        case RenderMouseAction::RightUp:event=CockpitMouse::RightUp;button=2;break;
        case RenderMouseAction::Wheel:
            if(!std::isfinite(mouse.wheel))throw std::invalid_argument("Nonfinite native scroll input");
            event=CockpitMouse::Wheel;
            state=oapi::UInt32(std::uint16_t(static_cast<int>(std::clamp(mouse.wheel*120.,-32768.,32767.))))<<16;
            break;
        case RenderMouseAction::Move:break;
        }
        if(!down && button)paneMouseCapture&=~button;
        // Original Orbiter::MouseEvent gives an active camera drag priority.
        if(render.cameraRotating && render.camera->ProcessMouse(event,state,mouse.x,mouse.y,input.keys.data()))return true;
        if(CockpitGuiCapturesMouse())return true;
        bool consumed=running && cockpit->ProcessMouse_OnRunning(event,state,mouse.x,mouse.y,input.keys.data());
        if(!consumed)consumed=cockpit->ProcessMouse_System(event,state,mouse.x,mouse.y,input.keys.data());
        if(down && consumed)paneMouseCapture|=button;
        if(!consumed)consumed=render.camera->ProcessMouse(event,state,mouse.x,mouse.y,input.keys.data());
        return consumed;
    }
    void CockpitSnapshot() {
        if(!cockpitState.is_open())return;
        auto* v=render.focus->GetModuleInterface();VECTOR3 p{},velocity{},omega{};MATRIX3 rotation{};
        v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(rotation);
        const auto mode=[&](int index){auto* instrument=cockpit->MFD(index);return instrument?instrument->Type():MFD_NONE;};
        cockpitState<<completedTicks<<','<<time.SimT0<<','<<time.MJD0<<','<<v->GetName()<<','<<v->GetClassName()<<','<<cockpit->GetPanelMode()<<','<<cockpit->GetHUDMode()<<','<<mode(0)<<','<<mode(1);
        for(double value:{p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,rotation.m11,rotation.m12,rotation.m13,rotation.m21,rotation.m22,rotation.m23,rotation.m31,rotation.m32,rotation.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass()})cockpitState<<','<<value;
        cockpitState<<','<<v->GetMeshCount()<<','<<v->GetThrusterCount();
        if(observeControls)cockpitState<<','<<v->GetAttitudeMode();
        cockpitState<<'\n';cockpitState.flush();
        ObserveCockpitGui(completedTicks);
    }
#endif
    void EventAt(const char* phase,const char* object,const char* detail,double seconds,double mjd) {
        if(lifetimeEvents.is_open())lifetimeEvents<<inputTick<<','<<observationTick<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<','<<detail<<'\n';
    }
    void LifetimeEvent(const char* phase,const char* object="",const char* detail="") {EventAt(phase,object,detail,time.SimT0,time.MJD0);}
    static void VesselEvent(void* context,const char* phase,const char* object,double seconds,double mjd,int) {
        auto& self=*static_cast<Runtime*>(context);self.EventAt(phase,object,"1",seconds,mjd);
        if(self.vesselCallbacks.is_open())self.vesselCallbacks<<self.inputTick<<','<<self.completedTicks<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<'\n';
    }
    Vessel* RequireVessel(const std::string& name) {
        auto* vessel=system->GetVessel(name.c_str(),true);if(!vessel)throw std::runtime_error("Required live vessel missing: "+name);return vessel;
    }
    void Commands(const char* phase) {
        for(const auto& command:replay.Take(inputTick,phase)) {
            auto* v=render.focus->GetModuleInterface();
#ifdef ORBITER_NATIVE_COCKPIT
            if(command.action=="ui") {
                std::istringstream fields(command.value);std::string event,text,extra;int x,y;
                if(!(fields>>event>>x>>y>>text) || fields>>extra)throw std::invalid_argument("Invalid declared GUI replay input");
                if(text=="-")text.clear();
                if(event=="open_input") {
                    auto enter=[](void*,char*,void*) { return true; };
                    auto cancel=[](void*,char* value,void* data) {
                        auto& self=*static_cast<Runtime*>(data);
                        std::ofstream out(self.render.evidence/"ui-cancel.txt");out<<value<<'\n';return true;
                    };
                    oapiOpenInputBoxEx("Reference input cancellation",enter,cancel,nullptr,20,this);
                } else {
                    render.graphics->ReplayGuiInput(event,x,y,text);
                    if(event=="left_down" || event=="popup_down")Mouse({RenderMouseAction::LeftDown,x,y,0});
                    if(event=="left_up")Mouse({RenderMouseAction::LeftUp,x,y,0});
                }
                if(std::filesystem::is_regular_file(render.evidence/"ui-evidence.enabled")) {
                    const auto path=render.evidence/"ui-inputs.csv";
                    const bool exists=std::filesystem::exists(path);
                    std::ofstream out(path,std::ios::app);
                    if(!exists)out<<"tick,event,x,y,text_hex\n";
                    out<<inputTick<<','<<event<<','<<x<<','<<y<<',';
                    static const char hex[]="0123456789abcdef";
                    for(unsigned char c:text)out<<hex[c>>4]<<hex[c&15];
                    out<<'\n';
                }
                continue;
            }
            if(command.action=="mouse") {
                std::istringstream fields(command.value);std::string action,extra;int x,y;
                if(!(fields>>action>>x>>y) || fields>>extra || x<0 || y<0 || x>=cockpit->Width() || y>=cockpit->Height())
                    throw std::invalid_argument("Mouse replay requires an event and valid viewport coordinates");
                RenderMouseAction type;
                if(action=="left_down")type=RenderMouseAction::LeftDown;
                else if(action=="left_up")type=RenderMouseAction::LeftUp;
                else if(action=="right_down")type=RenderMouseAction::RightDown;
                else if(action=="right_up")type=RenderMouseAction::RightUp;
                else throw std::invalid_argument("Unsupported replay mouse event");
                Mouse({RenderMouseAction::Move,x,y,0});Mouse({type,x,y,0});continue;
            }
            if(command.action=="mfd") {
                std::istringstream fields(command.value);int index,mode;std::string extra;
                if(!(fields>>index>>mode) || fields>>extra || index<0 || index>=MAXMFD || mode<1 || mode>10)throw std::invalid_argument("MFD replay requires a stock index and mode");
                cockpit->OpenMFD(index,mode);continue;
            }
            if(command.action=="hud") {
                double value=FlightNumber(command.value);
                if(value<0 || value>3 || value!=int(value))throw std::invalid_argument("HUD replay requires mode 0 through 3");
                cockpit->SetHUDMode(int(value));continue;
            }
#endif
            if(command.action=="airborne") {
                if(std::string(phase)!="start" || time.FrameCount()!=0 || ReadFlightStatus(*v)!=1)
                    throw std::runtime_error("Airborne initialization requires an initially landed vessel at session start");
                std::istringstream fields(command.value);fields.imbue(std::locale::classic());std::string heightText,forwardText,downText,extra;
                if(!(fields>>heightText>>forwardText>>downText) || fields>>extra)throw std::runtime_error("Airborne initialization requires height, forward speed and downward speed");
                const double height=FlightNumber(heightText),forward=FlightNumber(forwardText),down=FlightNumber(downText);
                if(height<0)throw std::runtime_error("Airborne height offset must be nonnegative");
                // The original SDK converts landed state to free flight. No force or integrator is replaced.
                VESSELSTATUS2 state{};state.version=2;v->GetStatusEx(&state);
                VECTOR3 p{},ep{};oapiGetGlobalPos(state.rbody,&ep);v->GetGlobalPos(p);state.rpos=p-ep;
                const double radius=length(state.rpos);state.rpos*=1+height/radius;
                MATRIX3 r{};v->GetRotationMatrix(r);v->GetGlobalOrientation(state.arot);v->GetAngularVel(state.vrot);
                if(forward)state.rvel+=mul(r,_V(0,0,forward));
                if(down)state.rvel-=state.rpos*(down/length(state.rpos));
                state.status=0;state.flag=0;v->DefSetStateEx(&state);continue;
            }
            if(command.action=="create" || command.action=="create_legacy") {
                std::istringstream fields(command.value);std::string name,type,extra;
                if(!(fields>>name>>type) || fields>>extra)throw std::runtime_error("Creation requires vessel name and class");
                VESSELSTATUS2 state{};state.version=2;v->GetStatusEx(&state);state.rpos.x+=100;state.flag=0;
                OBJHANDLE child;
                if(command.action=="create_legacy") {VESSELSTATUS legacy{};v->GetStatus(legacy);legacy.rpos.x+=100;child=oapiCreateVessel(name.c_str(),type.c_str(),legacy);}
                else child=oapiCreateVesselEx(name.c_str(),type.c_str(),&state);
                if(!child || oapiGetVesselInterface(child)->GetThrusterCount()!=16)throw std::runtime_error("Required source-built child vessel module missing");
                LifetimeEvent("input.create",name.c_str(),type.c_str());continue;
            }
            if(command.action=="focus") {
                auto* next=RequireVessel(command.value);auto* before=render.focus;auto previous=oapiSetFocusObject(next);
                if(previous!=(before==next?nullptr:before) || oapiGetFocusInterface()!=next->GetModuleInterface())throw std::logic_error("Focus SDK return/interface contract failed");
                LifetimeEvent("input.focus",next->Name());continue;
            }
            if(command.action=="delete") {
                std::istringstream fields(command.value);std::string name,replacement,extra;
                if(!(fields>>name))throw std::runtime_error("Deletion requires a vessel name");
                fields>>replacement;if(fields>>extra)throw std::runtime_error("Invalid deletion arguments");
                auto* vessel=RequireVessel(name);auto* target=replacement.empty()?nullptr:system->GetObj(replacement.c_str(),true);
                if(!replacement.empty() && !target)throw std::runtime_error("Required alternative camera target missing");
                if(!oapiDeleteVessel(vessel,target))throw std::runtime_error("Vessel deletion request failed");
                LifetimeEvent("input.delete",name.c_str());continue;
            }
            if(command.action=="attachment") {
                auto* child=RequireVessel(command.value)->GetModuleInterface();
                auto a=v->CreateAttachment(false,_V(0,0,5),_V(0,0,1),_V(0,1,0),"parent");
                auto b=child->CreateAttachment(true,_V(0,0,-5),_V(0,0,-1),_V(0,1,0),"child");
                if(!a || !b || !attachments.emplace(command.value,AttachmentPair{static_cast<Vessel*>(v->GetHandle()),a,b}).second)throw std::runtime_error("Attachment creation failed or duplicated");continue;
            }
            if(command.action=="attach" || command.action=="detach") {
                auto* child=RequireVessel(command.value);auto it=attachments.find(command.value);
                if(it==attachments.end())throw std::runtime_error("Required attachment not created");
                const bool valid=command.action=="attach"?it->second.parent->GetModuleInterface()->AttachChild(child,it->second.parentHandle,it->second.childHandle):it->second.parent->GetModuleInterface()->DetachChild(it->second.parentHandle,.2);
                if(!valid)throw std::runtime_error("Attachment operation failed");
                LifetimeEvent(command.action=="attach"?"input.attach":"input.detach",v->GetName(),child->Name());continue;
            }
            const double value=FlightNumber(command.value);
            if(command.action=="main" || command.action=="hover") {
                if(value<0 || value>1)throw std::runtime_error("Invalid replay throttle");
                v->SetThrusterGroupLevel(command.action=="main"?THGROUP_MAIN:THGROUP_HOVER,value);
            } else if(command.action=="attitude") {if(value!=1 && value!=2 && value!=0)throw std::runtime_error("Invalid RCS mode");v->SetAttitudeMode(int(value));}
            else if(command.action=="nav") {if(value<1 || value>7 || value!=int(value))throw std::runtime_error("Invalid autopilot mode");v->ActivateNavmode(int(value));}
            else if(command.action=="navoff") {if(value<1 || value>7 || value!=int(value))throw std::runtime_error("Invalid autopilot mode");v->DeactivateNavmode(int(value));}
            else if(command.action=="navreset") {for(int mode=1;mode<=7;++mode)v->DeactivateNavmode(mode);}
            else if(command.action=="holdalt_ground") {if(value<0 || value>1e6)throw std::runtime_error("Invalid hover altitude target");v->SetHoverHoldAltitude(value,true);}
            else if(command.action=="aerodynamic") {if(value<0 || value>7 || value!=int(value))throw std::runtime_error("Invalid aerodynamic control mode");v->SetADCtrlMode(UInt32(value));}
            else if(command.action=="elevator" || command.action=="aileron" || command.action=="rudder") {
                if(value < -1 || value>1)throw std::runtime_error("Invalid control surface level");
                v->SetControlSurfaceLevel(command.action=="elevator"?AIRCTRL_ELEVATOR:command.action=="aileron"?AIRCTRL_AILERON:AIRCTRL_RUDDER,value);
            }
            else if(command.action=="warp") SetWarpFactor(value);
            else if(command.action=="pause") {if(value!=0 && value!=1)throw std::runtime_error("Invalid pause command");running=value==0;render.paused=!running;}
            else if(command.action=="undock") {if(value<0 || value>=v->DockCount() || std::floor(value)!=value)throw std::runtime_error("Invalid docking port");if(!v->Undock(int(value)))throw std::runtime_error("Replay undocking failed");}
            else if(command.action=="endplayback") {
                if(value!=0)throw std::runtime_error("Invalid end-playback command");
                LifetimeEvent("input.endplayback","",playback?"active":"idle");
                if(playback)EndPlayback();
            }
            else if(command.action=="save") {LifetimeEvent("input.save");Save();}
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
    void SaveTo(const std::filesystem::path& destination,const char *description,int format,const char *recordName=nullptr) {
        if(destination.empty())throw std::runtime_error("No explicit user save path");
        std::filesystem::create_directories(destination.parent_path());auto temporary=destination;temporary+=".tmp";
        try {
            std::ofstream file(temporary);file.exceptions(std::ios::badbit|std::ios::failbit);file.imbue(std::locale::classic());
            scenarioState->Update(time.MJD0,render.focus->Name());
            auto metadata=*scenarioState;
            if(recordName)metadata.SetPlaybackDirectory(recordName);
            metadata.Write(file,description,format);
            render.camera->Write(file);
#ifdef ORBITER_NATIVE_COCKPIT
            if(cockpit)cockpit->Write(file);
#endif
            system->Write(file);file.close();std::filesystem::rename(temporary,destination);
        } catch(...) {std::error_code ignored;std::filesystem::remove(temporary,ignored);throw;}
        std::cout<<"Saved finalized production scenario: "<<destination<<'\n';
    }
    void Save() {
        std::string desc=std::string("Native production ")+render.focus->GetModuleInterface()->GetClassName()+" flight";
        SaveTo(savePath,desc.c_str(),0);
    }
#ifdef ORBITER_NATIVE_COCKPIT
    std::string quicksaveStem;
    unsigned quicksaveIndex=0;
    void Quicksave() override {
        std::ostringstream name;
        name<<quicksaveStem<<' '<<std::setfill('0')<<std::setw(4)<<++quicksaveIndex<<".scn";
        const auto destination=render.scriptSaveDirectory/"Quicksave"/name.str();
        char desc[128];
        std::snprintf(desc,sizeof(desc),"Orbiter saved state at T = %0.0f",time.SimT0);
        try {
            SaveTo(destination,desc,0);
            oapiAddNotification(OAPINOTIF_SUCCESS,"Scenario saved successfully",name.str().c_str());
        } catch(const std::exception& error) {
            oapiAddNotification(OAPINOTIF_ERROR,"Failed to save scenario",error.what());
        }
    }
    int RecorderStatus() const override {return recording ? 1 : playback ? 2 : 0;}
    void RecordSystemEvent(const char* type,const char* payload) {
        if(!recording)return;
        std::ofstream file(RecorderFile(("Flights/"+recordingName+"/system.dat").c_str(),true),std::ios::app);
        file.exceptions(std::ios::badbit|std::ios::failbit);
        file.imbue(std::locale::classic());
        file<<std::setprecision(10)<<(time.SimT1-Tofs)<<' '<<type<<' '<<payload<<std::endl;
    }
    void StopRecording() {
        if(!recording)return;
        for(auto* vessel:system->GetVessels())vessel->FRecorder_Activate(false,nullptr,false);
        recording=false;
    }
    bool ToggleRecorder(const char* requested,bool overwrite=false) override {
        if(playback)return true;
        if(recording) {StopRecording();return true;}
        try {
            const std::string name=ResourceResolver::Normalize(requested ? requested : playbackDirectory);
            // The stock recorder uses fixed 256-byte paths. Accept a single
            // recording name and validate every vessel filename before activation.
            if(name.size()>120 || name.find('/')!=std::string::npos)
                throw std::invalid_argument("Recording name must be a filename of at most 120 characters");
            for(auto* vessel:system->GetVessels()) {
                const auto vesselName=ResourceResolver::Normalize(vessel->Name());
                if(vesselName.find('/')!=std::string::npos || name.size()+std::strlen(vessel->Name())+16>=256)
                    throw std::invalid_argument("Vessel name is too long or contains a path separator");
            }
            const auto directory=render.scriptSaveDirectory/"Flights"/name;
            if(std::filesystem::exists(directory) && !overwrite)return false;
            if(std::filesystem::is_symlink(directory))throw std::runtime_error("Recording directory is a symbolic link");
            if(overwrite)std::filesystem::remove_all(directory);
            std::filesystem::create_directories(directory);
            recordingName=name;
            // Probe the destination before activating any vessel writer.
            std::ofstream probe(directory/"system.dat");
            probe.exceptions(std::ios::badbit|std::ios::failbit);probe.close();
            recording=true;
            for(auto* vessel:system->GetVessels())vessel->FRecorder_Activate(true,name.c_str(),false);
            char description[128];
            std::snprintf(description,sizeof(description),"Orbiter playback scenario at T = %0.0f",time.SimT0);
            SaveTo(render.scriptSaveDirectory/"Playback"/(name+".scn"),description,0,name.c_str());
            std::clog<<"Flight recording started: "<<name<<'\n';
            return true;
        } catch(const std::exception& error) {
            StopRecording();
            oapiAddNotification(OAPINOTIF_ERROR,"Flight recording failed",error.what());
            return true; // An I/O error is not an overwrite confirmation.
        }
    }
    std::filesystem::path PlaybackFile(bool writing) override {
        const auto relative="Flights/"+playbackDirectory+"/system.dat";
        if(!writing)return RecorderFile(relative.c_str(),false);
        // Editing a bundled flight creates a user copy of the complete flight.
        // Subsequent playback resolves this user directory as one unit.
        const auto destination=render.scriptSaveDirectory/"Flights"/ResourceResolver::Normalize(playbackDirectory);
        const auto source=RecorderFile(relative.c_str(),false).parent_path();
        if(source!=destination) {
            std::filesystem::create_directories(destination);
            for(const auto& file:std::filesystem::directory_iterator(source))
                if(file.is_regular_file())std::filesystem::copy_file(file.path(),destination/ResourceResolver::Normalize(file.path().filename().string()),std::filesystem::copy_options::overwrite_existing);
            const auto scenarioCopy=render.scriptSaveDirectory/"Playback"/(ResourceResolver::Normalize(playbackDirectory)+".scn");
            std::filesystem::create_directories(scenarioCopy.parent_path());
            if(initialScenario!=scenarioCopy)
                std::filesystem::copy_file(initialScenario,scenarioCopy,std::filesystem::copy_options::overwrite_existing);
            localPlaybackRoot=render.scriptSaveDirectory;
        }
        return destination/"system.dat";
    }
    void SuspendPlayback() override {systemPlayback.close();systemPlayback.clear();}
    void RescanPlayback() override {
        SuspendPlayback();
        if(!playback)return;
        annotations.EndPlayback();
        systemPlayback.open(PlaybackFile(false));
        systemPlayback>>nextPlaybackEvent;
        PlaybackStep();
    }
    void EndSession() override {active=false;}
    bool SaveScriptScenario(const char *name,const char *desc) override {
        SaveTo(name,desc,1);
        return true;
    }
    bool Jump(double mjd,int mode) override {
        if (!std::isfinite(mjd)) return false;
        scriptJump={time.JumpTo(mjd),mode};
        system->Timejump(scriptJump);
        render.camera->Update();
        if (cockpit) cockpit->Timejump();
        return true;
    }
    void Pause(bool pause) override { running=!pause; render.paused=pause; }
    void SetScriptFOV(double value) override {
        if (render.camera->Aperture()!=value) {render.camera->SetAperture(value,false);force=true;}
    }
    bool BufferedKey(oapi::UInt32 key,const oapi::UInt32 *modifiers,oapi::UInt32 count,bool runningOnly) override {
        if ((runningOnly && !running) || key>=256 || (count && !modifiers)) return false;
        FlightInput event;
        for (oapi::UInt32 i=0;i<count;++i) {
            if (modifiers[i]>=event.keys.size()) return false;
            event.keys[modifiers[i]]=char(0x80);
        }
        event.events.push_back({key,true});
        Buffered(event);
        return true;
    }
    bool ImmediateKeys(const char *keys,bool runningOnly) override {
        if ((runningOnly && !running) || !keys) return false;
        for (std::size_t i=0;i<simulatedKeys.size();++i) simulatedKeys[i]|=keys[i];
        return true;
    }
    const char *KeyState() const override {return input.keys.data();}
#endif
    void Buffered(FlightInput& snapshot) {
        BufferedKeyState buffered(snapshot);
        for(auto event:snapshot.events) {
            auto& eventKeys=buffered.Advance(event);
            if(inputEvents.is_open()) {
                inputEvents<<inputTick<<','<<event.code<<','<<event.down;
                for(unsigned key:{OAPI_KEY_LSHIFT,OAPI_KEY_RSHIFT,OAPI_KEY_LCONTROL,OAPI_KEY_RCONTROL,OAPI_KEY_LALT,OAPI_KEY_RALT})inputEvents<<','<<bool(KEYDOWN(eventKeys.data(),key));
                inputEvents<<'\n';
            }
            auto code=UInt32(event.code);
            auto& keymap=controls.keymap;
            if(event.down) {
                const bool spacePause=code==OAPI_KEY_SPACE && !KEYMOD_SHIFT(eventKeys.data()) &&
                    !KEYMOD_CONTROL(eventKeys.data()) && !KEYMOD_ALT(eventKeys.data());
                if(spacePause || keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_Pause)) {running=!running;render.paused=!running;continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_Quicksave)) {savePending=true;continue;}
#ifdef ORBITER_NATIVE_COCKPIT
                if(HandleCockpitStepFov(keymap,code,eventKeys.data()))continue;
#endif
                if(code==OAPI_KEY_F5 && !KEYMOD_CONTROL(eventKeys.data())) {reloadPending=true;continue;}
#ifndef ORBITER_NATIVE_COCKPIT
                if(code==OAPI_KEY_F6 && !KEYMOD_CONTROL(eventKeys.data())) {stepOnce=true;continue;}
#endif
#ifdef ORBITER_NATIVE_COCKPIT
                if(HandleCockpitMenuKey(keymap,code,eventKeys.data()))continue;
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_TogglePlanetarium)) {settings.CfgVisHelpPrm.flagPlanetarium^=PLN_ENABLE;continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_ToggleLabels)) {settings.CfgVisHelpPrm.flagMarkers^=MKR_ENABLE;continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_ToggleCamInternal)) {
                    SetView(render.focus,!render.camera->IsExternal());continue;
                }
                if(render.camera->IsInternal()) {
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_TogglePanelMode)) {cockpit->TogglePanelMode();continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_CockpitResetCam)) {render.camera->ResetCockpitDir();continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_PanelSwitchLeft)) {cockpit->SwitchPanel(0);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_PanelSwitchRight)) {cockpit->SwitchPanel(1);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_PanelSwitchUp)) {cockpit->SwitchPanel(2);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_PanelSwitchDown)) {cockpit->SwitchPanel(3);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_CockpitDontLean)) {render.focus->LeanCamera(0);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_CockpitLeanForward)) {render.focus->LeanCamera(1);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_CockpitLeanLeft)) {render.focus->LeanCamera(2);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_CockpitLeanRight)) {render.focus->LeanCamera(3);continue;}
                    if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_HUDColour)) {cockpit->ToggleHUDColour();continue;}
                } else if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_ToggleTrackMode)) {
                    render.camera->SetTrackMode(ExtCamMode((int(render.camera->GetExtMode())+1)%3));continue;
                }
#else
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_DlgSelectVessel)) {
                    const auto& list=system->GetVessels();auto it=std::find(list.begin(),list.end(),render.focus);auto start=std::size_t(it-list.begin());
                    for(std::size_t i=1;i<=list.size();++i) {auto* next=list[(start+i)%list.size()];if(next->GetEnableFocus() && !next->KillPending()) {orbiter::production::SetFocusObject(*this,next);break;}}
                    continue;
                }
#endif
#ifdef ORBITER_NATIVE_COCKPIT
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_ToggleRecPlay)) {
                    if(playback)EndPlayback();
                    else ToggleCockpitRecorder();
                    continue;
                }
#else
                if(playback && keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_ToggleRecPlay)) {EndPlayback();continue;}
#endif
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_SelectPrevVessel)) {if(previousFocus)orbiter::production::SetFocusObject(*this,previousFocus);continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_Quit)) {active=false;continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_IncSimSpeed)) {SetWarpFactor(std::pow(10.,std::floor(std::log10(time.Warp())+1e-6)+1));continue;}
                if(keymap.IsLogicalKey(code,eventKeys.data(),OAPI_LKEY_DecSimSpeed)) {SetWarpFactor(std::pow(10.,std::ceil(std::log10(time.Warp())-1e-6)-1));continue;}
            }
            if(running) {
                if(render.focus->ConsumeBufferedKey(code,event.down,eventKeys.data()))continue;
#ifdef ORBITER_NATIVE_COCKPIT
                // Preserve the original vessel-first priority and Shift-side
                // selection; Control combinations never reach this MFD path.
                if(event.down && code!=OAPI_KEY_LSHIFT && code!=OAPI_KEY_RSHIFT &&
                   !KEYMOD_CONTROL(eventKeys.data()) && KEYMOD_SHIFT(eventKeys.data())) {
                    auto* g_pane=cockpit.get();auto* kstate=eventKeys.data();auto key=code;
#include "CockpitMfdInput.inc"
                }
#endif
            }
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
#ifdef ORBITER_NATIVE_COCKPIT
        if(recording && system)StopRecording();
        if(render.optionsUsed) {
            auto temporary=optionsPath;temporary+=".tmp";
            try {
                if(!settings.Write(temporary.string().c_str()))throw std::runtime_error("Cannot write cockpit options");
                std::ofstream file(temporary,std::ios::app);file.exceptions(std::ios::badbit|std::ios::failbit);
                file<<"\nNativeJoystickThrottleAxis = "<<render.joystickThrottleAxis
                    <<"\nNativeJoystickRudderAxis = "<<render.joystickTwistAxis<<'\n';
                file.close();std::filesystem::rename(temporary,optionsPath);
            } catch(const std::exception& error) {
                std::error_code ignored;std::filesystem::remove(temporary,ignored);
                std::cerr<<"Cockpit options were not saved: "<<error.what()<<'\n';
            }
            render.optionsUsed=false;
        }
#endif
        if(playback && system)EndPlayback();
#ifdef ORBITER_NATIVE_COCKPIT
        if(scenarioInterpreter) {oapiDelInterpreter(scenarioInterpreter);scenarioInterpreter=nullptr;}
#endif
        if(render.graphics)render.graphics->CloseSession();
        if(baseResources){Base::DestroyStaticDeviceObjects();baseResources=false;}
#ifdef ORBITER_NATIVE_COCKPIT
        annotations.Clear();
        if (guiCreated) {
            render.graphics->ShutdownGui();
            DestroyCockpitGui();
            guiCreated=false;
        }
        cockpit.reset();render.cockpitPane=nullptr;
        scripts.EndTerminalMfd();
        if(instrumentResources){Instrument::GlobalExit(render.graphics);instrumentResources=false;}
        // Match the production Windows cockpit shutdown order while the
        // graphics context and logical world still exist.
        meshes.Flush();world.Reset();
#else
        world.Reset();meshes.Flush();
#endif
        if(render.graphics)render.graphics->Close();graphicsModule.reset();render.graphics=nullptr;
#ifdef ORBITER_NATIVE_COCKPIT
        scripts.End();render.scripts=nullptr;
#endif
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpitState.is_open())cockpitState.close();
        if(cockpitMouse.is_open())cockpitMouse.close();
#endif
        for(auto* file:{&vesselCallbacks,&lifetimeEvents,&lifecycle,&trace,&flightTrace,&inputTrace,&inputEvents,&thrustTrace,&animationTrace,&controlTrace,&mathTrace,&contactTrace})if(file->is_open())file->close();
        finished=true;
    }
    ~Runtime() {
        try {Finish();}catch(const std::exception& error) {std::cerr<<"Production teardown: "<<error.what()<<'\n';}
        BindVesselObserver(nullptr,nullptr);BindFlightControls(nullptr);BindNativeRenderContext(nullptr);BindNativeVesselModuleResources(nullptr);BindVesselServices(nullptr);
        BindCameraServices(nullptr);BindWorldVesselServices(nullptr);BindElevationServices(nullptr);BindMeshServices({});
        BindNavigationServices(nullptr);BindSurfaceServices(nullptr);BindCelestialServices(nullptr);BindRigidBodyServices(nullptr);BindBodyServices(nullptr);
    }
    void Initialize(const std::filesystem::path& master,const std::filesystem::path& scenario,const std::filesystem::path& evidence,double captureTime) {
        if(!settings.Load(master.string().c_str())) throw std::runtime_error("Cannot load explicit production configuration");
#ifdef ORBITER_NATIVE_COCKPIT
        optionsPath=master;
        int axis;
        if(render.joystickThrottleAxis==-2 && settings.GetInt("NativeJoystickThrottleAxis",axis) && axis>=-2 && axis<=15)
            render.joystickThrottleAxis=axis;
        if(render.joystickTwistAxis==-2)
            render.joystickTwistAxis=settings.GetInt("NativeJoystickRudderAxis",axis) && axis>=-1 && axis<=15 ? axis : 2;
#endif
#ifdef ORBITER_NATIVE_COCKPIT
        bool terminalMfdRequested=false;
        for(const auto& plugin:settings.GetActiveModules()) {
            if(CompareText(plugin.c_str(),"LuaMFD"))unsupported("application plugins in this external-view host");
            terminalMfdRequested=true;
        }
#else
        if(!settings.GetActiveModules().empty())unsupported("application plugins in this external-view host");
#endif
        scenarioState=std::make_unique<State>(51982.5);State& metadata=*scenarioState;if(!metadata.Read(scenario,51982.5))throw std::runtime_error("Cannot parse production scenario");
#ifndef ORBITER_NATIVE_COCKPIT
        if(metadata.Script())unsupported("bundled Lua in the external-view build");
#else
        quicksaveStem=scenario.stem().string();
        initialScenario=scenario;
        render.scenarioHelp=metadata.ScnHelp()?metadata.ScnHelp():"";
        localPlaybackRoot=CompareText(scenario.parent_path().filename().string().c_str(),"Playback")==0
            ? scenario.parent_path().parent_path() : savePath.parent_path();
        std::string directory=metadata.PlaybackDir();
        std::replace(directory.begin(),directory.end(),'\\','/');
        playbackDirectory=std::filesystem::path(directory).filename().string();
        render.annotations=&annotations;render.scripts=&scripts;render.scriptApplication=this;render.scriptSaveDirectory=savePath.parent_path();
#endif
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
        render.configurationFiles=&resources.config;
        render.highTextures=&resources.highTextures;render.planetTextures=&resources.planets;render.meshFiles=&resources.meshFiles;render.programFiles=&resources.program;
        render.evidence=evidence;render.captureTime=captureTime;BindNativeRenderContext(&render);
        if(!evidence.empty()) {std::filesystem::create_directories(evidence);lifecycle.open(evidence/"application-lifecycle.csv");lifecycle.exceptions(std::ios::badbit|std::ios::failbit);lifecycle<<"event,seconds,mjd,running\n";
            trace.open(evidence/"production-state.csv");trace.imbue(std::locale::classic());trace.exceptions(std::ios::badbit|std::ios::failbit);trace<<std::setprecision(17)<<"step,seconds,mjd,object,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,ground\n";}
        if(!evidence.empty()) {
            for(auto* file:{&vesselCallbacks,&lifetimeEvents}) {file->imbue(std::locale::classic());file->exceptions(std::ios::badbit|std::ios::failbit);}
            vesselCallbacks.open(evidence/"vessel-callbacks.csv");vesselCallbacks<<std::setprecision(17)<<"frame,tick,seconds,mjd,phase,object\n";
            lifetimeEvents.open(evidence/"lifetime-events.csv");lifetimeEvents<<std::setprecision(17)<<"frame,tick,seconds,mjd,phase,object,detail\n";
            std::ofstream numerical(evidence/"numerics.json");numerical.exceptions(std::ios::badbit|std::ios::failbit);
            numerical<<"{\"math\":\""<<SimulationMathProfile()<<"\",\"random\":\"private-msvc-lcg32\",\"random_maximum\":"<<RandomMaximum<<",\"process_seed\":0}\n";
            flightTrace.open(evidence/"flight-state.csv");flightTrace.imbue(std::locale::classic());flightTrace.exceptions(std::ios::badbit|std::ios::failbit);
            flightTrace<<std::setprecision(17)<<"tick,frame,seconds,mjd,object,class,rx,ry,rz,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,altitude_agl,altitude_mean,airspeed,density,dynamic_pressure,lift,drag,ground,dock,focus,navmask,attached\n";
            inputTrace.open(evidence/"input-state.csv");inputTrace.imbue(std::locale::classic());inputTrace.exceptions(std::ios::badbit|std::ios::failbit);
            inputTrace<<std::setprecision(17)<<"tick,keys,x,y,rz,alternate,throttle\n";
            inputEvents.open(evidence/"input-events.csv");inputEvents.exceptions(std::ios::badbit|std::ios::failbit);inputEvents<<"tick,key,down,lshift,rshift,lctrl,rctrl,lalt,ralt\n";
            thrustTrace.open(evidence/"thrust-state.csv");thrustTrace.imbue(std::locale::classic());thrustTrace.exceptions(std::ios::badbit|std::ios::failbit);
            thrustTrace<<std::setprecision(17)<<"tick,input_tick,seconds,object,main,hover,rcs,exhaust,navmask\n";
            animationTrace.open(evidence/"flight-animations.csv");animationTrace.imbue(std::locale::classic());animationTrace.exceptions(std::ios::badbit|std::ios::failbit);
            animationTrace<<std::setprecision(17)<<"tick,object,index,state\n";
            controlTrace.open(evidence/"flight-controls.csv");controlTrace.imbue(std::locale::classic());controlTrace.exceptions(std::ios::badbit|std::ios::failbit);
            controlTrace<<std::setprecision(17)<<"tick,seconds,object,flight_status,aerodynamic_mode,rcs_mode,elevator,aileron,rudder\n";
            mathTrace.open(evidence/"ground-math.csv");mathTrace.imbue(std::locale::classic());mathTrace.exceptions(std::ios::badbit|std::ios::failbit);
            mathTrace<<std::setprecision(17);math_observation::Header(mathTrace);
            contactTrace.open(evidence/"ground-contact.csv");contactTrace.imbue(std::locale::classic());contactTrace.exceptions(std::ios::badbit|std::ios::failbit);
            contactTrace<<std::setprecision(17);contact_observation::Header(contactTrace);
        }
#ifdef ORBITER_NATIVE_COCKPIT
        if(!evidence.empty()) {
            if(std::filesystem::is_regular_file(evidence/"playback.enabled")) {
                playbackTrace.exceptions(std::ios::badbit|std::ios::failbit);
                playbackTrace.imbue(std::locale::classic());
                playbackTrace.open(evidence/"playback-state.csv");playbackTrace<<std::setprecision(17);
                playback_observation::Header(playbackTrace);
            }
            observeControls=std::filesystem::is_regular_file(evidence/"control-evidence.enabled");
            cockpitState.imbue(std::locale::classic());cockpitState.exceptions(std::ios::badbit|std::ios::failbit);
            cockpitState.open(evidence/"cockpit-state.csv");cockpitState<<std::setprecision(17)<<"tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters";
            cockpitState<<(observeControls?",rcs_mode\n":"\n");
            if(observeControls){cockpitMouse.open(evidence/"control-inputs.csv");cockpitMouse.exceptions(std::ios::badbit|std::ios::failbit);cockpitMouse<<"tick,event,x,y\n";}
        }
#endif
        render.lifetime=this;BindVesselObserver(VesselEvent,this);
        graphicsModule=std::make_unique<NativeModule>(resources.modules.Resolve("Graphics/OGLClient.so"),ORBITER_NATIVE_GRAPHICS,&render);
        render.graphics=static_cast<NativeGraphics*>(graphicsModule->Instance());render.graphics->Open();
        UInt32 viewportWidth=0,viewportHeight=0;
        render.graphics->clbkGetViewportSize(&viewportWidth,&viewportHeight);
        if(!viewportWidth || !viewportHeight || viewportWidth>UInt32(std::numeric_limits<int>::max()) ||
           viewportHeight>UInt32(std::numeric_limits<int>::max()))throw std::runtime_error("Native render viewport is invalid");
        MeshServices mesh;mesh.context=this;
        mesh.path=[](void* context,const char* name){return static_cast<Runtime*>(context)->resources.meshFiles.Resolve(std::string(name)+".msh");};
        mesh.loadTexture=[](void* context,const char* name,UInt32 flags) -> MeshSurface {
            auto& self=*static_cast<Runtime*>(context);auto result=self.render.graphics->LoadTextureResource(name,flags);
            if(!result)throw std::runtime_error(std::string("Required stock mesh texture could not load: ")+name);return result;
        };
        mesh.releaseTexture=[](void* context,MeshSurface texture){if(texture)static_cast<Runtime*>(context)->render.graphics->ReleaseTextureResource(texture);};
        mesh.error=[](void*,const char* text){throw std::runtime_error(text);};mesh.allocation=[](void*,const char*,int){};BindMeshServices(mesh);
#ifdef ORBITER_NATIVE_COCKPIT
        cockpit=std::make_unique<Pane>(render.graphics,int(viewportWidth),int(viewportHeight),32);render.cockpitPane=cockpit.get();
        if(!evidence.empty()) {
            std::ofstream viewport(evidence/"cockpit-viewport.json");viewport.exceptions(std::ios::badbit|std::ios::failbit);
            viewport<<"{\"width\":"<<cockpit->Width()<<",\"height\":"<<cockpit->Height()<<"}\n";
        }
        CreateCockpitGui();guiCreated=true;
        render.graphics->InitGui();
        static bool modesRegistered=false;if(!modesRegistered){Instrument::RegisterBuiltinModes();modesRegistered=true;}
        if(terminalMfdRequested)scripts.LoadTerminalMfd();
        Instrument::GlobalInit(render.graphics);instrumentResources=true;
#endif
        Base::CreateStaticDeviceObjects();baseResources=true;
        RigidBody::GlobalSetup();
        if(!world.Initialize(metadata.Solsys()))throw std::runtime_error("Production solar system contains no objects");
        system->InitState(scenario.string().c_str());
        if(!system->nVessel())throw std::runtime_error("Native production session requires a live stock vessel");
#ifdef ORBITER_ATLANTIS_DIAGNOSTIC
        if(!evidence.empty()) {
            std::ofstream marker(evidence/"unqualified-atlantis-diagnostic.json");
            marker.exceptions(std::ios::badbit|std::ios::failbit);
            marker<<"{\"scope\":\"Unqualified Atlantis test host using real production modules and session algorithms\",\"native_admission_qualified\":false,\"phase6_complete\":false}\n";
        }
#endif
#ifdef ORBITER_REMAINING_STOCK_DIAGNOSTIC
        if(!evidence.empty()) {
            std::ofstream marker(evidence/"unqualified-remaining-stock-diagnostic.json");
            marker.exceptions(std::ios::badbit|std::ios::failbit);
            marker<<"{\"scope\":\"Unqualified remaining-stock host using actual original modules and session algorithms\",\"native_admission_qualified\":false,\"phase6_complete\":false}\n";
        }
#endif
        for(auto* body:system->GetVessels()) {
            auto* vessel=body->GetModuleInterface();const char* type=vessel->GetClassName();
            const bool pb=CompareText(type,"ShuttlePB")==0 && vessel->Version()==2 && vessel->GetMeshCount()==1 && vessel->GetThrusterCount()==16 && vessel->GetPropellantCount()==1;
            const bool iss=CompareText(type,"ProjectAlpha_ISS")==0 && vessel->Version()==0 && vessel->GetMeshCount()==1;
#ifdef ORBITER_NATIVE_COCKPIT
            const bool scram=CompareText(type,"DG-S")==0;
            if ((CompareText(type,"DeltaGlider")==0 || scram) && vessel->Version()==3 && vessel->GetMeshCount()==2 &&
                vessel->GetThrusterCount()==(scram ? 23 : 21) && vessel->GetPropellantCount()==(scram ? 3 : 2))
                continue;
            if(SupportedStockShuttleA(*vessel,type))continue;
            if(SupportedRemainingStock(*body,*vessel,type))continue;
#if defined(ORBITER_ATLANTIS_DIAGNOSTIC) || defined(ORBITER_REMAINING_STOCK_DIAGNOSTIC)
            if(SupportedAtlantisDiagnostic(*vessel,type))continue;
#endif
#ifdef ORBITER_REMAINING_STOCK_DIAGNOSTIC
            if(SupportedRemainingStockDiagnostic(*vessel,type))continue;
#endif
#endif
            if(!pb && !iss && !SupportedStockStation(*vessel,type))
                throw std::runtime_error(std::string("Unsupported stock vessel class or capabilities: ")+type+"; generic replacement is forbidden");
        }
        auto* focus=system->GetVessel(metadata.Focus());
        if(!focus)focus=system->GetVessel(oapi::UInt32(0));
        SetFocus(focus);
        render.camera->ResizeViewport(int(viewportWidth),int(viewportHeight));render.camera->InitState(scenario.string().c_str(),focus);
#ifndef ORBITER_NATIVE_COCKPIT
        if(!render.camera->IsExternal())unsupported("cockpits yet; select an external camera");
#endif
#ifdef ORBITER_NATIVE_COCKPIT
        playback=focus->bPlayback();
        if(playback) {
            systemPlayback.open(RecorderFile(("Flights/"+playbackDirectory+"/system.dat").c_str(),false));
            systemPlayback>>nextPlaybackEvent;
        }
        if(metadata.Script()) scenarioInterpreter=scripts.Load().run(metadata.Script());
#endif
        render.graphics->PostCreation();system->PostCreation();
#ifdef ORBITER_NATIVE_COCKPIT
        cockpit->InitState(scenario.string().c_str());
#endif
        Commands("start");
#ifndef ORBITER_NATIVE_COCKPIT
        render.camera->Update();
#endif
        if(system->nGrav()!=41)throw std::runtime_error("This native scene requires the actual stock Sol world");
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
    SURFHANDLE LoadTexture(const char* name,bool applicationSurface) override {
        auto result=render.graphics->LoadTextureResource(name,0);
        // Original generic base slots may have no day/night texture. Mesh
        // textures and required application surfaces retain their own checks.
        if(!result && applicationSurface)throw std::runtime_error(std::string("Required engine texture failed: ")+name);
        return result;
    }
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
    const char* PlaybackDirectory() const override {
#ifdef ORBITER_NATIVE_COCKPIT
        return playbackDirectory.c_str();
#else
        unsupported("recorded flights in the external-view build");
#endif
    }
    void SetWarpFactor(double warp) override {
        if(!std::isfinite(warp) || warp<=0)throw std::runtime_error("Invalid time acceleration");
#ifndef ORBITER_NATIVE_COCKPIT
        if(!playback || !settings.CfgRecPlayPrm.bReplayWarp)time.SetWarp(std::clamp(warp,.1,100000.));
#else
        if(playback && settings.CfgRecPlayPrm.bReplayWarp)return;
        warp=std::clamp(warp,.1,100000.);
        if(std::abs(warp-time.Warp())<=1e-6)return;
        time.SetWarp(warp);
        if(settings.CfgRecPlayPrm.bRecordWarp) {
            char payload[128];std::snprintf(payload,sizeof(payload),"%f",warp);
            RecordSystemEvent("TACC",payload);
        }
#endif
    }
    double TimejumpDelta() const override {
#ifdef ORBITER_NATIVE_COCKPIT
        return scriptJump.dt;
#else
        unsupported("time jumps in this scene host");
#endif
    }
    void RedrawCockpitAreas(int flags) override {
        pendingCockpitRedraw|=unsigned(flags);
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpit)cockpit->RedrawCockpitAreas(flags);
#endif
    }
    const double* ParticleLevel(const oapi::ParticleStream* stream) const override {return stream->Level();}
    void InsertVessel(Vessel* vessel) override {orbiter::production::InsertVessel(*this,vessel);}
    double ManualControl(THGROUP_TYPE group,UInt32 device) const override {return controls.Manual(group,device);}
    void NotifyJump(const Vessel& vessel,const Vector& delta) override {if(&vessel==render.camera->Target())render.camera->Drag(-delta);if(render.camera->Target())render.camera->Update();}
    void ShiftCockpit(const Vessel& vessel,const Vector& shift) override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpit && render.focus==&vessel)cockpit->ShiftVC(shift);
#else
        unsupported("virtual cockpit movement yet");
#endif
    }
    std::filesystem::path RecorderFile(const char* relative,bool writing) override {
        auto name=ResourceResolver::Normalize(relative);
        if(name.rfind("flights/",0)!=0)throw std::invalid_argument("Expected a flight recording path");
#ifdef ORBITER_NATIVE_COCKPIT
        const auto suffix=name.substr(8);
        const auto destination=render.scriptSaveDirectory/"Flights"/suffix;
        if(writing)return destination;
        // Once a local recording directory exists, missing optional streams
        // belong to that recording; never mix in similarly named stock data.
        const auto local=localPlaybackRoot/"Flights"/suffix;
        if(std::filesystem::is_directory(local.parent_path()))return local;
#else
        if(writing)unsupported("flight recording yet");
#endif
        if(resources.program.Contains(name))return resources.program.Resolve(name);
        if(std::filesystem::path(name).extension()==".pos")throw std::runtime_error("Missing required flight recording: "+name);
        const auto parent=std::filesystem::path(name).parent_path();
        if(resources.program.ContainsDirectory(parent.generic_string()))
            return resources.program.ResolveDirectory(parent.generic_string())/std::filesystem::path(name).filename();
        return resources.program.Root()/name;
    }
    void PlaybackWarp(double warp,double delay) override {
        if(!std::isfinite(warp) || warp<=0 || !std::isfinite(delay))throw std::runtime_error("Invalid recorded time acceleration");
        if(std::abs(warp-time.Warp())>1e-6)time.SetWarp(std::clamp(warp,.1,100000.),delay);
    }
    void RecallCameraPreset(int index) override {render.camera->RecallPreset(index);}
    void PlaybackNote(char* text) override {
#ifdef ORBITER_NATIVE_COCKPIT
        annotations.PlaybackNote(text);
#else
        unsupported("playback annotations in the external-view build");
#endif
    }
    void EndPlayback() override {
        for(auto* vessel:system->GetVessels())vessel->FRecorder_EndPlayback();
#ifdef ORBITER_NATIVE_COCKPIT
        systemPlayback.close();
        annotations.EndPlayback();
#endif
        playback=false;
        LifetimeEvent("playback.ended");
    }
    Vessel* Focus() const override {return render.focus;}
    void SetFocus(Vessel* vessel) override {orbiter::production::SetFocusObject(*this,vessel,false);}
    PlanetarySystem*& LifetimeWorld() override {RequireWorld();return system;}
    Camera*& LifetimeCamera() override {return render.camera;}
    Vessel*& CurrentFocus() override {return render.focus;}
    Vessel*& PreviousFocus() override {return previousFocus;}
    void SetView(Body* body,int mode) override {render.camera->Attach(body,mode);force=true;LifetimeEvent("camera.target",render.camera->Target()->Name(),render.camera->IsExternal()?"external":"internal");}
    void PaneFocusChanged(Vessel* vessel) override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpit)cockpit->FocusChanged(vessel);
#endif
    }
    void ModuleFocusChanged(Vessel* now,Vessel* previous) override {
        LifetimeEvent("module.focus",now->Name(),previous?previous->Name():"");
#ifdef ORBITER_NATIVE_COCKPIT
        if(settings.CfgRecPlayPrm.bRecordFocus)RecordSystemEvent("FOCUS",now->Name());
#endif
    }
    void DialogFocusChanged(Vessel*) override {} // No dialogs are instantiated.
    void ModuleNewVessel(Vessel* vessel) override {LifetimeEvent("module.create",vessel->Name());}
    void GraphicsNewVessel(Vessel* vessel) override {render.graphics->NewVessel(vessel);LifetimeEvent("graphics.create",vessel->Name());}
    void DialogNewVessel(Vessel*) override {} // No dialogs are instantiated.
    void ModuleDeleteVessel(Vessel* vessel) override {
#ifdef ORBITER_NATIVE_COCKPIT
        scripts.DeleteVessel(vessel);
#endif
        LifetimeEvent("module.delete",vessel->Name());
    }
    void GraphicsDeleteVessel(Vessel* vessel) override {render.graphics->DeleteVessel(vessel);for(auto it=attachments.begin();it!=attachments.end();)if(it->first==vessel->Name() || it->second.parent==vessel)it=attachments.erase(it);else ++it;LifetimeEvent("graphics.delete",vessel->Name());}
    void PaneDeleteVessel(Vessel* vessel) override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpit)cockpit->DelVessel(vessel);
#endif
    }
    void DialogDeleteVessel(Vessel*) override {} // No dialogs are instantiated.
    void ConsoleDeleteVessel(Vessel*) override {} // No console view is instantiated.
    void SetFOV(double value) override {if(render.camera->Aperture()!=value){render.camera->SetAperture(value);force=true;}}
    void IncFOV(double dfov) override {
        auto* g_camera=render.camera;
        auto& g_bForceUpdate=force;
#include "CockpitFovInput.inc"
    }
#ifdef ORBITER_NATIVE_COCKPIT
    bool SetPanelMode(int mode) override {if(!cockpit)throw std::logic_error("Native cockpit is not initialized");return cockpit->SetPanelMode(mode);}
    void SelectPanel(int id) override {if(!cockpit)throw std::logic_error("Native cockpit is not initialized");cockpit->SelectPanel(id);}
    void SelectVC(int id) override {if(!cockpit)throw std::logic_error("Native cockpit is not initialized");cockpit->SelectVC(id);}
#else
    bool SetPanelMode(int) override {unsupported("cockpit panels yet");}
    void SelectPanel(int) override {unsupported("2D panels yet");}
    void SelectVC(int) override {unsupported("virtual cockpits yet");}
#endif
    std::filesystem::path ScenarioPath(const char* name) const override {return name;}
    Camera* CreateCamera() override {
        auto camera=std::make_unique<Camera>();
#ifdef ORBITER_NATIVE_COCKPIT
        const auto point=render.graphics->CursorPosition();
        camera->InitMousePosition(point.x,point.y);
#endif
        return render.camera=camera.release();
    }
    PlanetarySystem* CreateSystem(const char* name) override {
        auto status=[](const char* text,int,void*) {std::clog<<text<<'\n';};
        return render.world=system=new PlanetarySystem(const_cast<char*>(name),&settings,status,nullptr);
    }
    bool HasObjects(const PlanetarySystem* body) const override {return body->nObj()!=0;}
    void DestroyCamera(Camera* camera) noexcept override {delete camera;render.camera=nullptr;}
    void DestroySystem(PlanetarySystem* body) noexcept override {delete body;render.world=system=nullptr;}
    void Observe(const char* event,bool state) override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(std::string(event)=="app.frame.end") {
            if(cockpitObserved)CockpitSnapshot();
            if(playbackTrace.is_open()) playback_observation::Row(playbackTrace,completedTicks);
        }
#endif
        LifetimeEvent(event,"",state?"1":"0");if(lifecycle.is_open())lifecycle<<event<<','<<time.SimT0<<','<<time.MJD0<<','<<state<<'\n';}
    void ModulePreStep() override {LifetimeEvent("module.pre");Commands("pre");
#ifdef ORBITER_NATIVE_COCKPIT
        if(playbackTrace.is_open() && !completedTicks)playback_observation::Row(playbackTrace,0);
        if(!cockpitObserved && render.camera->IsInternal()){CockpitSnapshot();cockpitObserved=true;}
#endif
        for(UInt32 i=0;i<system->nVessel();++i)system->GetVessel(i)->ModulePreStep(time.SimT0,time.SimDT,time.MJD0);}
    void PlaybackStep() override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(!systemPlayback.good())return;
        PlaySystemEvents(systemPlayback,nextPlaybackEvent,time,*render.camera,
            [this](Vessel* v){orbiter::production::SetFocusObject(*this,v);},
            [this](double mjd){Jump(mjd,PROP_ORBITAL_FIXEDSURF);},[this]{active=false;});
        if(!systemPlayback.good())systemPlayback.close();
#else
        unsupported("recorded flights in the external-view build");
#endif
    }
    void UpdateBodies(bool update) override {system->Update(update);}
    void UpdateDialogs() override {} // No dialogs are instantiated in external-view scope.
    void ModulePostStep() override {
        for(UInt32 i=0;i<system->nVessel();++i)system->GetVessel(i)->ModulePostStep(time.SimT1,time.SimDT,time.MJD1);
#ifdef ORBITER_NATIVE_COCKPIT
        scripts.PostStep(time.SimT1,time.SimDT,time.MJD1);
#endif
        LifetimeEvent("module.post");
    }
    bool DeletePendingVessels() override {return orbiter::production::KillVessels(*this);}
    void NoVessels() override {active=false;}
    void FinaliseBodies() override {system->FinaliseUpdate();}
    void AdvanceTime(bool state) override {time.EndStep(state);if(state)++completedTicks;}
    void WriteTrace() override {
        if(thrustTrace.is_open()) {
            auto* v=render.focus->GetModuleInterface();double exhaust=0;unsigned mask=0;
            for(unsigned i=0;i<v->GetExhaustCount();++i)exhaust=std::max(exhaust,v->GetExhaustLevel(i));
            for(int nav=1;nav<=7;++nav)if(v->GetNavmodeState(nav))mask|=1u<<nav;
            thrustTrace<<completedTicks<<','<<inputTick<<','<<time.SimT0<<','<<v->GetName()<<','<<v->GetThrusterGroupLevel(THGROUP_MAIN)<<','
                <<v->GetThrusterGroupLevel(THGROUP_HOVER)<<','<<RcsLevel(*v)<<','<<exhaust<<','<<mask<<'\n';
        }
        if(flightTrace.is_open()) {
            const auto* earth=system->GetGravObj("Earth",true);
            const auto& ep=system->GetGravObj("Earth",true)->GPos();const auto& ev=system->GetGravObj("Earth",true)->GVel();
            auto observed=system->GetVessels();std::sort(observed.begin(),observed.end(),[](const Vessel* a,const Vessel* b){return std::string(a->Name())<b->Name();});
            for(auto* vessel:observed) {
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
                flightTrace<<','<<int(v->GroundContact())<<','<<(dock?static_cast<Vessel*>(dock)->Name():"")<<','<<render.focus->Name()<<','<<mask<<',';
                for(bool parent:{false,true})for(UInt32 i=0;i<v->AttachmentCount(parent);++i)
                    if(auto attached=v->GetAttachmentStatus(v->GetAttachmentHandle(parent,i)))flightTrace<<static_cast<Vessel*>(attached)->Name()<<';';
                flightTrace<<'\n';
                controlTrace<<completedTicks<<','<<time.SimT0<<','<<v->GetName()<<','<<ReadFlightStatus(*v)<<','<<v->GetADCtrlMode()<<','<<v->GetAttitudeMode()
                    <<','<<v->GetControlSurfaceLevel(AIRCTRL_ELEVATOR)<<','<<v->GetControlSurfaceLevel(AIRCTRL_AILERON)<<','<<v->GetControlSurfaceLevel(AIRCTRL_RUDDER)<<'\n';
                for(unsigned index=0;index<256;++index) {
                    const double state=v->GetAnimation(index);if(state<0)break;
                    if(!std::isfinite(state))throw std::runtime_error("Nonfinite production animation state");
                    animationTrace<<completedTicks<<','<<v->GetName()<<','<<index<<','<<state<<'\n';
                }
                if(vessel==render.focus) {
                    MATRIX3 er{},ob{};for(unsigned i=0;i<9;++i){er.data[i]=earth->GRot().data[i];ob.data[i]=earth->RotObliq().data[i];}
                    math_observation::Row(mathTrace,completedTicks,time.SimT0,*v,MakeVECTOR3(earth->GPos()),er,ob,earth->Rotation());
                    if (CompareText(v->GetClassName(),"ShuttlePB")==0)
                        contact_observation::Row(contactTrace,completedTicks,time.SimT0,*v);
                }
            }
        }
        if(!trace.is_open())return;
        std::vector<Body*> bodies;
        for(const char* name:{"Sun","Earth","Moon"}) {
            auto* body=system->GetGravObj(name,true);if(!body)throw std::runtime_error("Required production trace primary missing");bodies.push_back(body);
        }
        auto all=system->GetVessels();std::sort(all.begin(),all.end(),[](const Vessel* a,const Vessel* b){return std::string(a->Name())<b->Name();});
        for(auto* vessel:all)bodies.push_back(vessel);
        for(auto* body:bodies) {
            auto* vessel=body->Type()==OBJTP_VESSEL?static_cast<Vessel*>(body):nullptr;const char* name=body->Name();
            const auto& p=body->GPos();const auto& v=body->GVel();const auto& r=body->GRot();Vector w(0,0,0);if(vessel)w=vessel->AngularVelocity();
            trace<<time.FrameCount()<<','<<time.SimT0<<','<<time.MJD0<<','<<name;
            for(double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,w.x,w.y,w.z,body->Mass(),vessel?vessel->GetModuleInterface()->GetFuelMass():0}) {
                if(!std::isfinite(value))throw std::runtime_error("Nonfinite production state");trace<<','<<value;
            }
            trace<<','<<(vessel && vessel->GetModuleInterface()->GroundContact()?1:0)<<'\n';
        }
    }
    void UpdateCamera() override {render.camera->Update();}
    void UpdatePanels(double simt,double syst) override {
#ifdef ORBITER_NATIVE_COCKPIT
        if(cockpit)cockpit->Update(simt,syst);
#endif
    }
    void UpdateVisuals(bool) override {} // This client updates its visuals in the original Scene::Render phase, as on Windows.
    void CheckSessionLimit() override {}
    std::string Status() const {
        auto* v=render.focus->GetModuleInterface();std::ostringstream text;text.imbue(std::locale::classic());
        text<<"Orbiter | "<<v->GetName()<<" | "<<(running?"RUNNING":"PAUSED")<<" t="<<std::fixed<<std::setprecision(3)<<time.SimT0<<"s"
            <<" | RCS "<<(v->GetAttitudeMode()==1?"ROT":v->GetAttitudeMode()==2?"LIN":"OFF")
            <<' '<<std::setprecision(0)<<RcsLevel(*v)*100<<"%"
            <<" | MAIN "<<std::setprecision(0)<<v->GetThrusterGroupLevel(THGROUP_MAIN)*100<<"% HOV "<<v->GetThrusterGroupLevel(THGROUP_HOVER)*100<<"%"
            <<" | AERO "<<(v->GetADCtrlMode()?"ON":"OFF")<<" | "<<(ReadFlightStatus(*v)==1?"LANDED":v->GroundContact()?"CONTACT":"AIRBORNE")
            <<" AGL "<<std::setprecision(1)<<v->GetAltitude(ALTMODE_GROUND)<<"m SPD "<<v->GetAirspeed()<<"m/s"
            <<" | NAV";
        bool navActive=false;const char* names[]={"","KILLROT","LEVEL","PRO","RETRO","NORMAL","ANTINORMAL","ALT"};
        for(int mode=1;mode<=7;++mode)if(v->GetNavmodeState(mode)){text<<' '<<names[mode];navActive=true;}
        if(!navActive)text<<" none";
        text<<" | fuel "<<std::setprecision(3)<<v->GetFuelMass()<<"kg | x"<<time.Warp();
        if(auto dock=v->DockCount()?v->GetDockStatus(v->GetDockHandle(0)):nullptr)text<<" | DOCKED "<<static_cast<Vessel*>(dock)->Name();
        else if(auto* iss=system->GetVessel("ISS",true))text<<" | ISS "<<std::setprecision(1)<<render.focus->GPos().dist(iss->GPos())<<"m";
        return text.str();
    }
    void Step(double dt) {
        observationTick=completedTicks;Commands("before");Buffered(input);InputRecord();
        const bool wasRunning=running;if(stepOnce){running=true;stepOnce=false;}
        render.paused=!running;
#ifdef ORBITER_NATIVE_COCKPIT
        time.BeginStep(cockpitClock.Step(dt),running);
#else
        time.BeginStep(dt,running);
#endif
#ifdef ORBITER_NATIVE_COCKPIT
        FlightInput snapshot=input;
        for (std::size_t i=0;i<simulatedKeys.size();++i) snapshot.keys[i]|=simulatedKeys[i];
        HandleCockpitSystemKeys(controls.keymap,snapshot.keys.data(),force);
        if(running) {
            simulatedKeys.fill(0);
            controls.Immediate(*render.focus,time,snapshot);
        }
#else
        if(running)controls.Immediate(*render.focus,time,input);
#endif
#ifdef ORBITER_NATIVE_COCKPIT
        render.camera->UpdateMouse();
#endif
        Session::UpdateWorld(*this,time,running,playback,updating,force);
        Session::EndTimeStep(*this,time,running,active,force);
        if(!wasRunning)running=false;
        input.throttle=-1;observationTick=completedTicks;Commands("after");render.paused=!running;if(savePending){Save();savePending=false;}++inputTick;
    }
};
}
int main(int argc,char** argv) {
    try {
        std::map<std::string,std::string> arguments;
        for(int i=1;i<argc;++i) {
            std::string name=argv[i];
            if(name=="--help") {std::cout<<"orbiter-production --assets PATH --data PATH --modules PATH --planets PATH --config PATH --scenario PATH [--keymap PATH --save PATH --replay PATH --evidence PATH --fixed-step S --ticks N --render-every N --frames N --sessions N --frame-delay-ms N --fixed-ui-clock --run]\n";return 0;}
            if(name.rfind("--",0)!=0 || arguments.count(name))throw std::runtime_error("Invalid or duplicate argument: "+name);
            if(name=="--run" || name=="--fixed-ui-clock"){arguments[name]="1";continue;}
            if(i+1==argc || std::string(argv[i+1]).rfind("--",0)==0)throw std::runtime_error("Argument value missing: "+name);
            arguments[name]=argv[++i];
        }
        std::vector<std::string> allowed={"--assets","--data","--modules","--planets","--config","--scenario","--evidence","--frames","--fixed-step","--run","--capture-time","--keymap","--save","--replay","--ticks","--render-every","--sessions","--joystick-throttle-axis","--joystick-twist-axis","--frame-delay-ms","--fixed-ui-clock"};
        allowed.push_back("--fixed-system-step");
        for(const auto& entry:arguments)if(std::find(allowed.begin(),allowed.end(),entry.first)==allowed.end())throw std::runtime_error("Unknown argument: "+entry.first);
        for(const char* name:{"--assets","--data","--modules","--planets","--config","--scenario"})if(!arguments.count(name))throw std::runtime_error(std::string("Required argument missing: ")+name);
        const auto absolute=[&](const char* name){return std::filesystem::absolute(arguments.at(name));};
        auto integer=[&](const char* name,int fallback){if(!arguments.count(name))return fallback;double n=FlightNumber(arguments.at(name));if(n<0 || n>10000000 || n!=int(n))throw std::runtime_error(std::string("Invalid integer: ")+name);return int(n);};
        const int frames=integer("--frames",0),ticks=integer("--ticks",0),renderEvery=integer("--render-every",1),sessions=integer("--sessions",1);
        const int frameDelay=integer("--frame-delay-ms",0);
        if(frameDelay && (!frames || !arguments.count("--replay") || frameDelay>1000))
            throw std::runtime_error("Frame delay requires a bounded frame replay and at most 1000 ms");
        const bool fixedUiClock=arguments.count("--fixed-ui-clock")!=0;
        if(fixedUiClock && (!frames || !arguments.count("--replay")))
            throw std::runtime_error("Fixed GUI clock requires a bounded frame replay");
#ifndef ORBITER_NATIVE_COCKPIT
        if(fixedUiClock)throw std::runtime_error("This build has no cockpit GUI clock");
#endif
        const double fixed=arguments.count("--fixed-step")?FlightNumber(arguments.at("--fixed-step")):1.0/60.0;
        double systemFixed=fixed;
        if(arguments.count("--fixed-system-step")) {
            systemFixed=FlightNumber(arguments.at("--fixed-system-step"));
            if((!frames && !ticks) || !arguments.count("--evidence") || !arguments.count("--replay") || systemFixed<=0 || systemFixed>0.1)
                throw std::runtime_error("Controlled system step requires bounded evidence/replay and an elapsed input in (0,0.1]");
        }
        const double capture=arguments.count("--capture-time")?FlightNumber(arguments.at("--capture-time")):-1;
        if(fixed<=0 || (arguments.count("--capture-time") && capture<0) || !renderEvery || !sessions || (ticks && frames))throw std::runtime_error("Invalid frame/step/capture/session limits");
        std::srand(0);SeedRandom(0);Resources resources(absolute("--assets"),absolute("--data"),absolute("--modules"),absolute("--planets"));
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
#ifdef ORBITER_NATIVE_COCKPIT
            application.render.joystickThrottleAxis=integer("--joystick-throttle-axis",-2);
#else
            application.render.joystickThrottleAxis=integer("--joystick-throttle-axis",-1);
#endif
#ifdef ORBITER_NATIVE_COCKPIT
            application.render.joystickTwistAxis=integer("--joystick-twist-axis",-2);
#else
            application.render.joystickTwistAxis=integer("--joystick-twist-axis",2);
#endif
            if(application.render.joystickThrottleAxis>15 || application.render.joystickTwistAxis>15)throw std::runtime_error("Invalid joystick axis");
            if(arguments.count("--replay"))application.replay.Load(absolute("--replay"));
            application.savePath=save;application.Initialize(absolute("--config"),scenario,output,capture);
            if(arguments.count("--keymap") && (!std::filesystem::is_regular_file(absolute("--keymap")) || !application.controls.keymap.Read(absolute("--keymap").string().c_str())))throw std::runtime_error("Cannot load explicit flight keymap");
#ifdef ORBITER_NATIVE_COCKPIT
            if(fixedUiClock)SetCockpitReplayClock(static_cast<float>(fixed));
#endif
            application.time.SetFixedStep(fixed);application.running=startRunning;application.render.paused=!application.running;
            std::cout<<"Production "<<application.render.focus->GetModuleInterface()->GetClassName()<<" flight. Space/Ctrl-P: pause. T/R: warp. Ctrl-S: save. F5: reload. "
#ifdef ORBITER_NATIVE_COCKPIT
                <<"F6: options. F8: cockpit. "
#else
                <<"F6: step. "
#endif
                <<"Escape: close.\n";
            FlightClock clock(fixed);auto previous=std::chrono::steady_clock::now();
            int presented=0;bool reload=false;
            while(application.active && (!frames || presented<frames) && (!ticks || application.inputTick<unsigned(ticks))) {
                auto input=application.render.graphics->Poll();if(input.close)break;
                if(!frames && !ticks && !arguments.count("--replay")) {
                    application.input.keys=input.flight.keys;
                    application.input.events.insert(application.input.events.end(),input.flight.events.begin(),input.flight.events.end());
                    application.input.x=input.flight.x;application.input.y=input.flight.y;application.input.rz=input.flight.rz;application.input.alternate=input.flight.alternate;
                    if(input.flight.throttle>=0)application.input.throttle=input.flight.throttle;
#ifdef ORBITER_NATIVE_COCKPIT
                    for(const auto& mouse:input.mouse)application.Mouse(mouse);
#else
                    application.render.camera->ShiftPhi(input.yaw);application.render.camera->ShiftTheta(input.pitch);
                    if(input.zoom)application.render.camera->ChangeDist(std::pow(1.1,-input.zoom));
#endif
                }
                if(input.width>0 && input.height>0){application.render.graphics->Resize(input.width,input.height);application.render.camera->ResizeViewport(input.width,input.height);}
                if(frameDelay)std::this_thread::sleep_for(std::chrono::milliseconds(frameDelay));
                if(frames || ticks) {
                    for(int n=0;n<(ticks?renderEvery:1) && application.active && !application.reloadPending && (!ticks || application.inputTick<unsigned(ticks));++n)application.Step(systemFixed);
                } else {
                    auto now=std::chrono::steady_clock::now();clock.Add(std::chrono::duration<double>(now-previous).count());previous=now;
                    int count=0;while(count<256 && application.active && !application.reloadPending && clock.Tick()) {application.Step(fixed);++count;}
                    // Buffered actions remain responsive even without a due physics tick.
                    application.Buffered(application.input);
                    if(application.savePending && !application.stepOnce){application.Save();application.savePending=false;}
                }
                if(application.reloadPending) {if(!std::filesystem::is_regular_file(save)){std::cerr<<"No saved scenario exists: "<<save<<'\n';application.reloadPending=false;}else{scenario=save;reload=true;break;}}
                if(input.width>0 && input.height>0) {
#ifdef ORBITER_NATIVE_COCKPIT
                    application.render.graphics->NewGuiFrame();
                    BeginCockpitGuiFrame();
#endif
                    application.render.paused=!application.running;application.render.graphics->Status(application.Status());application.render.graphics->Render();
#ifdef ORBITER_NATIVE_COCKPIT
                    application.cockpit->Draw();
                    application.render.graphics->RenderGui();
#endif
                    if(!application.render.graphics->Present())throw std::runtime_error("Native frame presentation failed");++presented;
                } else std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            if((ticks || frames) && !application.replay.Empty())throw std::runtime_error("Unconsumed flight replay commands");
            application.Finish();
            if(reload) {startRunning=application.running;--session;continue;}
        }
        return 0;
    }
#ifdef ORBITER_NATIVE_COCKPIT
    catch(const ScriptProcessExit& exit) {return exit.code;}
#endif
    catch(const std::exception& error) {std::cerr<<"Orbiter native production: "<<error.what()<<'\n';return 1;}
}
