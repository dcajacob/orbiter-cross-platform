// Licensed under the MIT License
// Read the actual configured planet properties without changing world state.
#include "Production/Session.h"
#include "Production/NativeRenderApi.h"
#include "NativeVesselAPI.h"
#include <dlfcn.h>
#include <fstream>
#include <stdexcept>
#include <string>

void orbiter::production::Session::UpdateWorld(SessionServices& services,const TimeData& time,
    const bool& running,const bool& playback,bool& updating,const bool& force) {
    static auto original=reinterpret_cast<decltype(&Session::UpdateWorld)>(dlsym(RTLD_NEXT,
        "_ZN7orbiter10production7Session11UpdateWorldERNS0_15SessionServicesERK8TimeDataRKbS8_RbS8_"));
    if(!original)throw std::runtime_error("Original UpdateWorld missing");
    static std::ofstream output("planet-defaults.csv");
    static unsigned tick=0;
    if(!tick)output<<"tick,planet,cloud_microtexture\n";
    for(const auto& name:{"Earth","Venus","Triton","Moon"}) {
        auto object=oapiGetObjectByName(const_cast<char*>(name));
        if(!object)throw std::runtime_error("Configured planet missing");
        auto parameter=static_cast<const bool*>(oapiGetObjectParam(object,OBJPRM_PLANET_CLOUDMICROTEX));
        if(!parameter)throw std::runtime_error("Cloud-microtexture parameter missing");
        const bool value=*parameter;
        const bool expected=std::string(name)=="Earth" || std::string(name)=="Venus";
        if(value!=expected)throw std::runtime_error("Configured cloud-microtexture default differs");
        output<<tick<<','<<name<<','<<int(value)<<'\n';
    }
    output.flush();++tick;
    original(services,time,running,playback,updating,force);
}
