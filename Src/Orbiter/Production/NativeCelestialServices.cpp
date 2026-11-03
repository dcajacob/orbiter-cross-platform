// Licensed under the MIT License
#include "NativeCelestialServices.h"
#include "Celbody.h"
#include "ConfigFile.h"
#include "TimeData.h"
#include "AstroMath.h"
#include <iostream>
#include <stdexcept>
namespace orbiter::production {
namespace {
#ifdef _WIN32
constexpr const char* extension=".dll";
#else
constexpr const char* extension=".so";
#endif
std::string moduleName(const char* name)
{
    if (!name || !*name) throw std::runtime_error("Empty native module name");
    std::string value=name;
    if (value.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")!=std::string::npos)
        throw std::runtime_error("Invalid native module name: "+value);
    return value;
}
}
NativeCelestialServices::NativeCelestialServices(const ResourceResolver& c,const ResourceResolver& d,const ResourceResolver& m)
    :config(c),data(d),modules(m) {}
void NativeCelestialServices::RegisterModule(CelestialBody& body,const char* name)
{
    if (loaded.count(&body)) throw std::runtime_error("Celestial module already registered: "+std::string(body.Name()));
    auto entry=std::make_unique<Loaded>();entry->context.body=&body;entry->context.host=this;
    entry->module=std::make_unique<NativeModule>(modules.Resolve("Celbody/"+moduleName(name)+extension),ORBITER_NATIVE_CELESTIAL,&entry->context);
    if (!entry->module->Instance()) throw std::runtime_error("Native celestial module returned no interface");
    Log("Native celestial "+std::string(body.Name())+": "+entry->module->Info().name);
    loaded.emplace(&body,std::move(entry));
}
void NativeCelestialServices::ClearModule(CelestialBody& body) {loaded.erase(&body);}
bool NativeCelestialServices::HasModule(const CelestialBody& body) const {return loaded.count(&body)!=0;}
native::CelestialModule& NativeCelestialServices::Interface(const CelestialBody& body) const
{
    const auto it=loaded.find(&body);
    if (it==loaded.end()) throw std::runtime_error("No native celestial interface: "+std::string(body.Name()));
    return *static_cast<native::CelestialModule*>(it->second->module->Instance());
}
void NativeCelestialServices::InitializeModule(CelestialBody& body,std::ifstream& stream) {Interface(body).clbkInit(&stream);}
bool NativeCelestialServices::HasEphemeris(const CelestialBody& body) const {return Interface(body).bEphemeris();}
int NativeCelestialServices::Ephemeris(const CelestialBody& body,double time,int request,double* result) const
{return Interface(body).clbkEphemeris(time,request,result);}
int NativeCelestialServices::FastEphemeris(const CelestialBody& body,double time,int request,double* result) const
{return Interface(body).clbkFastEphemeris(time,request,result);}
const char* NativeCelestialServices::AtmosphereName(const CelestialBody& body) const {
    auto* atmosphere=HasModule(body) ? Interface(body).GetAtmosphere() : nullptr;
    return atmosphere ? atmosphere->clbkName() : nullptr;
}
int NativeCelestialServices::AtmosphereModel(const CelestialBody& body,ATMCONST& result) const
{
    if (!HasModule(body)) return 0;
    if (auto* atmosphere=Interface(body).GetAtmosphere()) {
        native::AtmosphereConstants value{};
        atmosphere->clbkConstants(&value);
        result={value.p0,value.rho0,value.R,value.gamma,value.C,value.O2pp,value.altlimit,value.radlimit,value.horizonalt,value.color0};
        return 4;
    }
    return 0; // Stock SPICE explicitly selects the advanced atmosphere interface.
}
void NativeCelestialServices::AtmosphereParameters(const CelestialBody& body,int model,double altitude,double longitude,double latitude,ATMPARAM& result) const
{
    if (model!=4 || !Interface(body).GetAtmosphere())
        throw std::runtime_error("Unsupported native atmosphere interface for "+std::string(body.Name()));
    native::AtmosphereInput input;
    native::AtmosphereOutput output;
    input.alt=altitude; input.lng=longitude; input.lat=latitude;
    input.flag=native::Atmosphere::PRM_ALT|native::Atmosphere::PRM_LNG|native::Atmosphere::PRM_LAT;
    Interface(body).GetAtmosphere()->clbkParams(&input,&output);
    result.p=output.p;result.rho=output.rho;result.T=output.T;
}
std::filesystem::path NativeCelestialServices::GravityModelPath(const char* name) const {return data.Resolve("GravityModels/"+std::string(name));}
void NativeCelestialServices::ConfigFailure(const std::filesystem::path& path) {throw std::runtime_error("Missing celestial configuration: "+path.string());}
void NativeCelestialServices::Log(const std::string& message) {std::clog<<message<<'\n';}
double NativeCelestialServices::SimulationMJD() const {return CelestialClock().MJD0;}
double NativeCelestialServices::TimeToMJD(double seconds) const {return CelestialClock().MJD_ref+Day(seconds);}
std::filesystem::path NativeCelestialServices::Resource(const std::string& name) const {return data.Resolve(name);}
double NativeCelestialServices::RotationPeriod(const CelestialBody& body) const {return body.RotT();}
VECTOR3 NativeCelestialServices::GlobalPosition(const CelestialBody& body) const
{const auto& p=body.GPos();return {p.x,p.y,p.z};}
void NativeCelestialServices::GlobalToEquatorial(const CelestialBody& body,const VECTOR3& p,double& longitude,double& latitude,double& radius) const
{body.GlobalToEquatorial(Vector(p.x,p.y,p.z),longitude,latitude,radius);}
std::string NativeCelestialServices::AtmosphereSelection(const CelestialBody& body,std::ifstream& original) const
{
    char name[512]={};
    const std::string path=std::string(body.Name())+"/Atmosphere.cfg";
    bool selected=false;
    if (config.Contains(path)) {
        std::ifstream stream(config.Resolve(path));
        if (!stream) throw std::runtime_error("Cannot read native atmosphere selection: "+path);
        selected=GetItemString(stream,"MODULE_ATM",name);
    }
    if (!selected) selected=GetItemString(original,"MODULE_ATM",name);
    if (!selected || ResourceResolver::Normalize(name)=="[none]") return {};
    return name;
}
std::unique_ptr<NativeModule> NativeCelestialServices::LoadAtmosphere(native::CelestialModule& body,const char* name)
{
    const auto path=modules.Resolve("Celbody/"+std::string(body.GetHandle()->Name())+"/Atmosphere/"+moduleName(name)+extension);
    return std::make_unique<NativeModule>(path,ORBITER_NATIVE_ATMOSPHERE,&body);
}
}
