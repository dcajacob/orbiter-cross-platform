// Licensed under the MIT License
#include "NativeCelestialApi.h"
#include <stdexcept>
namespace orbiter::native {
CelestialModule::CelestialModule(const CelestialInit& init):context(init)
{
    if (context.size!=sizeof(context) || !context.body || !context.host)
        throw std::runtime_error("Invalid native celestial module context");
}
CelestialModule::~CelestialModule()=default;
void CelestialModule::clbkInit(std::ifstream* config)
{
    if (!config) throw std::runtime_error("Missing native celestial configuration stream");
    if (!atm) {
        const auto name=Host().AtmosphereSelection(*context.body,*config);
        if (!name.empty()) LoadAtmosphereModule(name.c_str());
    }
}
bool CelestialModule::LoadAtmosphereModule(const char* name)
{
    auto loaded=Host().LoadAtmosphere(*this,name);
    if (!loaded || !loaded->Instance()) throw std::runtime_error("Native atmosphere initialization returned no instance");
    auto* instance=static_cast<Atmosphere*>(loaded->Instance());
    atmosphere=std::move(loaded);atm=instance;
    return true;
}
double CelestialModule::SidRotPeriod() const {return Host().RotationPeriod(*context.body);}
Atmosphere::Atmosphere(CelestialModule* body):cbody(body)
{if (!body) throw std::runtime_error("Missing native atmosphere parent");}
bool Atmosphere::clbkConstants(AtmosphereConstants* constants) const
{
    if (!constants) throw std::runtime_error("Missing native atmosphere constants output");
    // Original ATMOSPHERE default values and return behavior.
    constants->R=286.91;constants->gamma=1.4;return false;
}
}
