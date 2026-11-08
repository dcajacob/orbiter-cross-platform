// Licensed under the MIT License
// Read-only observations at the original session boundaries; every argument is forwarded.
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "Vessel.h"
#include "Production/NativeRenderApi.h"
#include "../StockVessels/Observation.h"
#include "../RemainingStock/Details.h"
#include <chrono>
#include <cstdlib>
#include <dlfcn.h>
#include <thread>
#include <limits>
#ifdef ORBITER_NATIVE_INSTRUMENT_CONTROL
#include "../NativeInstrumentTarget/Control.h"
#endif

namespace {
struct Preload {Preload(){unsetenv("LD_PRELOAD");}} preload;
std::ofstream state,docks;
remaining_stock::Details details;
unsigned frames=0;
bool initialized=false;
bool capabilitiesOpened=false;
struct Complete {
    ~Complete(){if(initialized)std::ofstream("stock-vessel-complete.txt")<<frames<<'\n';}
} complete;
}
extern "C" unsigned OrbiterRemainingStockFinalizedTickV2(unsigned abi) {
    return abi==2?frames:std::numeric_limits<unsigned>::max();
}
// Preserve real module capabilities and contemporaneous mappings before the
// session's qualification check. An early failure can otherwise unload the DSO
// before LSan reports its allocation PCs. Forward the original call unchanged.
void Vessel::SetClassCaps(std::ifstream& config) {
    using Function=void(*)(Vessel*,std::ifstream&);
    static auto original=reinterpret_cast<Function>(dlsym(RTLD_NEXT,
        "_ZN6Vessel12SetClassCapsERSt14basic_ifstreamIcSt11char_traitsIcEE"));
    stock_vessels::require(original!=nullptr,"Original remaining-stock SetClassCaps missing");
    original(this,config);
    auto* vessel=GetModuleInterface();stock_vessels::require(vessel!=nullptr,"Actual class-capability interface missing");
    std::ofstream caps("initial-module-capabilities.csv",std::ios::app);
    caps.exceptions(std::ios::badbit|std::ios::failbit);caps<<std::setprecision(17);
    if(!capabilitiesOpened){caps<<"object,class,version,empty_mass,size,meshes,thrusters,propellants,docks\n";capabilitiesOpened=true;}
    caps<<stock_vessels::csv(vessel->GetName())<<','<<stock_vessels::csv(vessel->GetClassName())<<','
        <<vessel->Version()<<','<<vessel->GetEmptyMass()<<','<<vessel->GetSize()<<','<<vessel->GetMeshCount()<<','
        <<vessel->GetThrusterCount()<<','<<vessel->GetPropellantCount()<<','<<vessel->DockCount()<<'\n';
    std::ifstream maps("/proc/self/maps");std::ofstream loaded("initial-module-loaded-maps.txt");loaded<<maps.rdbuf();
}
void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    stock_vessels::require(original!=nullptr,"Original remaining-stock UpdateWorld missing");
#ifndef ORBITER_NATIVE_FAST_CAPABILITY_DIAGNOSTIC
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
#endif
    if(!initialized) {
#ifdef ORBITER_NATIVE_INSTRUMENT_CONTROL
        native_instrument_target::run();
#endif
        stock_vessels::headers(state,docks);details.open();
        stock_vessels::snapshot(state,docks,0);details.snapshot(0);
        std::ifstream maps("/proc/self/maps");std::ofstream loaded("observer-loaded-maps.txt");loaded<<maps.rdbuf();
        initialized=true;
    }
    details.beginStep(frames+1);
    original(services,time,running,playback,updating,force);
}
void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,
    bool running,const bool& active,bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    stock_vessels::require(original!=nullptr,"Original remaining-stock EndTimeStep missing");
    original(services,time,running,active,force);
    stock_vessels::snapshot(state,docks,++frames);details.snapshot(frames);
}
