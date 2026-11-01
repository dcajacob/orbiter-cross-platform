// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_CELESTIAL_SERVICES_H
#define ORBITER_PRODUCTION_CELESTIAL_SERVICES_H
#include "Export.h"
#include <filesystem>
#include <fstream>
#include <string>
class CelestialBody;
class TimeData;
namespace orbiter::production {
// The host owns module/OS services. Calls address the actual production body;
// the shared numerical implementation neither loads DLLs nor invents ephemerides.
class CelestialServices {
public:
    virtual ~CelestialServices() = default;
    virtual void RegisterModule(CelestialBody&, const char* name) = 0;
    virtual void ClearModule(CelestialBody&) = 0;
    virtual bool HasModule(const CelestialBody&) const = 0;
    virtual void InitializeModule(CelestialBody&, std::ifstream&) = 0;
    virtual bool HasEphemeris(const CelestialBody&) const = 0;
    virtual int Ephemeris(const CelestialBody&, double mjd, int request, double* result) const = 0;
    virtual int FastEphemeris(const CelestialBody&, double seconds, int request, double* result) const = 0;
    virtual std::filesystem::path GravityModelPath(const char* name) const = 0;
    virtual void ConfigFailure(const std::filesystem::path&) = 0;
    virtual bool RequireGravityModel() const = 0;
    virtual void Log(const std::string&) = 0;
};
ORBITER_PRODUCTION_API CelestialServices* BindCelestialServices(CelestialServices* services);
ORBITER_PRODUCTION_API CelestialServices& GetCelestialServices();
ORBITER_PRODUCTION_API TimeData& CelestialClock();
class WindowsCelestialServices;
}
#endif
