// Licensed under the MIT License
// Test-only observer at the native session boundaries. Both original session
// methods execute once and their live flags and TimeData pass through unchanged.
#include "Production/NativeGraphics.h"
#include "Production/Session.h"
#include "NativeVesselAPI.h"
#include "TimeData.h"
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition,const char *message)
{
    if(!condition) throw std::runtime_error(message);
}
class Probe {
    unsigned frames=0;
    INTERPRETERHANDLE script=nullptr,secondary=nullptr;
    std::string target,profile;
    std::ofstream controls,air;
    void recordLibraries()
    {
        std::ifstream maps("/proc/self/maps");
        std::ofstream loaded("lua-loaded.txt");
        for(const char *name:{"LuaInline.so","LuaInterpreter.so","liblua.so"}) {
            bool found=false;
            maps.clear();maps.seekg(0);
            std::string line;
            while(std::getline(maps,line)) {
                auto pos=line.find('/');
                if(pos!=std::string::npos && std::filesystem::path(line.substr(pos)).filename()==name) {
                    loaded<<line.substr(pos)<<'\n';found=true;break;
                }
            }
            require(found,"Native runtime did not load the original Lua stack");
        }
    }
    void sample()
    {
        VESSEL *v=oapiGetFocusInterface();
        controls<<frames<<','<<v->GetControlSurfaceLevel(AIRCTRL_ELEVATOR)<<','<<v->GetControlSurfaceLevel(AIRCTRL_AILERON)<<','<<v->GetThrusterGroupLevel(THGROUP_MAIN)<<'\n';
        air<<frames<<','<<v->GetAtmDensity()<<','<<v->GetDynPressure()<<','<<v->GetAirspeed()<<'\n';
    }
public:
    Probe()
    {
        std::ifstream input("lua-case.txt");
        require(bool(input>>target>>profile),"Missing native Lua observer case");
        for(auto *file:{&controls,&air}) {file->imbue(std::locale::classic());file->exceptions(std::ios::badbit|std::ios::failbit);}
        controls.open("lua-controls.csv");controls<<std::setprecision(17)<<"tick,elevator,aileron,main\n";
        air.open("lua-air.csv");air<<std::setprecision(17)<<"tick,density,dynamic_pressure,airspeed\n";
    }
    void pre()
    {
        if(!frames)sample();
#include "ScriptSchedule.inc"
    }
    void end()
    {
        ++frames;sample();
        if(frames==60) {controls.close();air.close();}
    }
};
Probe& probe() {static Probe observer;return observer;}
}

void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,const bool& running,
                                              const bool& playback,bool& updating,const bool& force)
{
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(
        dlsym(RTLD_NEXT,"_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    require(original && running,"Missing live native UpdateWorld");
    probe().pre();
    original(services,time,running,playback,updating,force);
}

void orbiter::production::Session::EndTimeStep(SessionServices& services,TimeData& time,bool running,
                                               const bool& active,bool& force)
{
    static auto original=reinterpret_cast<decltype(&Session::EndTimeStep)>(
        dlsym(RTLD_NEXT,"_ZN7orbiter10production7Session11EndTimeStepERNS0_15SessionServicesER8TimeDatabRKbRb"));
    require(original,"Missing native EndTimeStep");
    original(services,time,running,active,force);
    probe().end();
}
