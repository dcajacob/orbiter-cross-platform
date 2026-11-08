// Licensed under the MIT License
// Diagnostic-only startup reads. No vessel, time, input or exit setters.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <string>
#include <xmmintrin.h>
namespace {
using Callback=void(*)(const char*,const char*,double,double,int);
using SetObserver=int(*)(unsigned,Callback,double);
class Observer;
Observer* observer=nullptr;
void Observe(const char*,const char*,double,double,int);
class Observer final : public oapi::Module {
    std::ofstream events,objects;
    SetObserver setter=nullptr;
    int previous=-1;
public:
    explicit Observer(HINSTANCE instance) : Module(instance),
        events("api-startup-events.csv",std::ios::binary),objects("api-startup-objects.csv",std::ios::binary) {
        events.imbue(std::locale::classic());objects.imbue(std::locale::classic());
        events<<std::setprecision(17)<<"phase,event_object,seconds,mjd,running,vessel_count\n";
        objects<<std::setprecision(17)<<"phase,seconds,mjd,index,name,class,version,size,empty_mass,mass,meshes,docks\n";
        events.flush();objects.flush();
        previous=_get_FMA3_enable();
        if(std::getenv("ORBITER_TEST_OBSERVER_SSE2"))_set_FMA3_enable(0);
        const auto active=_get_FMA3_enable();
        const bool enabled=std::getenv("ORBITER_TEST_DISABLE_API_OBSERVER")==nullptr;
        HMODULE provider=nullptr;wchar_t providerPath[32768]{};
        if(!GetModuleHandleExW(6,reinterpret_cast<LPCWSTR>(&_get_FMA3_enable),&provider) ||
           !GetModuleFileNameW(provider,providerPath,32768))std::exit(42);
        std::ofstream identity("api-observer.json",std::ios::binary);
        identity<<"{\"actual_pid\":"<<GetCurrentProcessId()<<",\"initial_fma3\":"<<previous
            <<",\"active_fma3\":"<<active<<",\"mxcsr_control\":"<<(_mm_getcsr()&0xffc0u)
            <<",\"observation_enabled\":"<<(enabled?"true":"false")
            <<",\"dispatch_provider\":"<<std::quoted(std::filesystem::path(providerPath).generic_u8string())<<"}\n";
        if(!enabled)return;
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));
        if(!setter || !setter(1,Observe,std::numeric_limits<double>::quiet_NaN()))std::exit(42);
    }
    ~Observer() override {
        if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());
        if(previous>=0)_set_FMA3_enable(previous);
    }
    void Event(const char* phase,const char* object,double seconds,double mjd,int running) {
        const unsigned count=oapiGetVesselCount();
        events<<phase<<','<<(object?object:"")<<','<<seconds<<','<<mjd<<','<<running<<','<<count<<'\n';events.flush();
        // load.after precedes insertion into the world vessel list. Read the
        // completed roster after postcreation, before the startup script exits.
        if(std::string(phase)!="vessel.postcreation.after")return;
        for(unsigned index=0;index<count;++index) {
            const auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(index));
            if(!vessel)std::exit(42);
            objects<<phase<<','<<seconds<<','<<mjd<<','<<index<<','<<vessel->GetName()<<','<<vessel->GetClassName()
                <<','<<vessel->Version()<<','<<vessel->GetSize()<<','<<vessel->GetEmptyMass()<<','<<vessel->GetMass()
                <<','<<vessel->GetMeshCount()<<','<<vessel->DockCount()<<'\n';
        }
        objects.flush();if(!events || !objects)std::exit(42);
    }
};
void Observe(const char* phase,const char* object,double seconds,double mjd,int running) {
    if(observer)observer->Event(phase,object,seconds,mjd,running);
}
}
DLLCLBK void InitModule(HINSTANCE instance) { observer=new Observer(instance);oapiRegisterModule(observer); }
DLLCLBK void ExitModule(HINSTANCE) { delete observer;observer=nullptr; }
