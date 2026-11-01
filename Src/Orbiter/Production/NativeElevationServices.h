// Licensed under the MIT License
#ifndef ORBITER_NATIVE_ELEVATION_SERVICES_H
#define ORBITER_NATIVE_ELEVATION_SERVICES_H
#include "ElevationServices.h"
#include "ResourceResolver.h"
#include <functional>
#include <string>
#include <vector>
class TimeData;
namespace orbiter::production {
class ORBITER_PRODUCTION_API NativeElevationServices final : public ElevationServices {
public:
    using SetupQuery=std::function<ElevationSetup(const CelestialBody&)>;
    NativeElevationServices(const ResourceResolver& textures,const TimeData& time,SetupQuery setup,
        const std::vector<std::string>& requiredArchives);
    NativeElevationServices(const NativeElevationServices&)=delete;
    NativeElevationServices& operator=(const NativeElevationServices&)=delete;
    ElevationSetup Setup(const CelestialBody&) const override;
    std::unique_ptr<ZTreeMgr> OpenArchive(const CelestialBody&,bool modified) override;
    bool HasLooseLayer(const CelestialBody&,bool modified) const override;
    std::filesystem::path LooseTile(const CelestialBody&,bool modified,int level,int latitude,int longitude) const override;
    double SystemTime() const override;
    // No filter is installed by this source-built stock external-view host.
    // Windows retains the existing optional client callback in its adapter.
    void Filter(const CelestialBody&,int,int,int,double,std::int16_t*) override {}
private:
    const ResourceResolver& textures;
    const TimeData& time;
    SetupQuery query;
};
}
#endif
