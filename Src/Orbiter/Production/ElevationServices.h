// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_ELEVATION_SERVICES_H
#define ORBITER_PRODUCTION_ELEVATION_SERVICES_H
#include "CoreTypes.h"
#include "Export.h"
#include <cstdint>
#include <filesystem>
#include <memory>
class CelestialBody;
class ZTreeMgr;
namespace orbiter::production {
struct ElevationSetup {
    int mode;
    UInt32 tileSources;
    int maximumLevel;
    double resolution;
};
// Original terrain calculations use explicit configuration, paths, cache clock
// and optional filter dispatch. Tile visibility and graphics LOD are absent.
class ElevationServices {
public:
    virtual ~ElevationServices() = default;
    virtual ElevationSetup Setup(const CelestialBody&) const = 0;
    virtual std::unique_ptr<ZTreeMgr> OpenArchive(const CelestialBody&,bool modified) = 0;
    virtual bool HasLooseLayer(const CelestialBody&,bool modified) const = 0;
    virtual std::filesystem::path LooseTile(const CelestialBody&,bool modified,int level,int latitude,int longitude) const = 0;
    virtual double SystemTime() const = 0;
    virtual void Filter(const CelestialBody&,int latitude,int longitude,int level,double resolution,std::int16_t* data) = 0;
};
ORBITER_PRODUCTION_API ElevationServices* BindElevationServices(ElevationServices* services);
ORBITER_PRODUCTION_API ElevationServices& GetElevationServices();
}
#endif
