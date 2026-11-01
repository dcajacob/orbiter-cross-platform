// Licensed under the MIT License
#ifndef ORBITER_NATIVE_CELESTIAL_SERVICES_H
#define ORBITER_NATIVE_CELESTIAL_SERVICES_H
#include "CelestialServices.h"
#include "NativeCelestialApi.h"
#include "ResourceResolver.h"
#include <map>
namespace orbiter::production {
// Loads real, same-build celestial and atmosphere modules. The owning production
// world must destroy its bodies before releasing these services/resource roots.
class ORBITER_PRODUCTION_API NativeCelestialServices final : public CelestialServices,public native::CelestialHost {
public:
    NativeCelestialServices(const ResourceResolver& config,const ResourceResolver& data,const ResourceResolver& modules);
    NativeCelestialServices(const NativeCelestialServices&)=delete;
    NativeCelestialServices& operator=(const NativeCelestialServices&)=delete;
    void RegisterModule(CelestialBody&,const char* name) override;
    void ClearModule(CelestialBody&) override;
    bool HasModule(const CelestialBody&) const override;
    void InitializeModule(CelestialBody&,std::ifstream&) override;
    bool HasEphemeris(const CelestialBody&) const override;
    int Ephemeris(const CelestialBody&,double,int,double*) const override;
    int FastEphemeris(const CelestialBody&,double,int,double*) const override;
    int AtmosphereModel(const CelestialBody&,ATMCONST&) const override;
    void AtmosphereParameters(const CelestialBody&,int,double,double,double,ATMPARAM&) const override;
    std::filesystem::path GravityModelPath(const char*) const override;
    void ConfigFailure(const std::filesystem::path&) override;
    bool RequireGravityModel() const override {return true;}
    void Log(const std::string&) override;
    double SimulationMJD() const override;
    double TimeToMJD(double seconds) const override;
    std::filesystem::path Resource(const std::string&) const override;
    double RotationPeriod(const CelestialBody&) const override;
    VECTOR3 GlobalPosition(const CelestialBody&) const override;
    void GlobalToEquatorial(const CelestialBody&,const VECTOR3&,double&,double&,double&) const override;
    std::string AtmosphereSelection(const CelestialBody&,std::ifstream&) const override;
    std::unique_ptr<NativeModule> LoadAtmosphere(native::CelestialModule&,const char*) override;
    native::CelestialModule& Interface(const CelestialBody&) const;
private:
    const ResourceResolver& config;
    const ResourceResolver& data;
    const ResourceResolver& modules;
    struct Loaded {
        native::CelestialInit context;
        std::unique_ptr<NativeModule> module;
    };
    std::map<const CelestialBody*,std::unique_ptr<Loaded>> loaded;
};
}
#endif
