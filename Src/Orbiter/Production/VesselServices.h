// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_VESSEL_SERVICES_H
#define ORBITER_PRODUCTION_VESSEL_SERVICES_H
#include "Export.h"
#include <filesystem>
class MeshManager;
namespace oapi {class ParticleStream;}
namespace orbiter::production {
// Application policy and file access used by the original vessel state code.
// Numerical state and scenario interpretation remain owned by Vessel.
class VesselServices {
public:
    virtual ~VesselServices()=default;
    virtual std::filesystem::path ConfigFile(const char* name,bool extension=true)=0;
    virtual void Fatal(const char* message)=0;
    virtual void Check(bool valid,const char* message)=0;
    virtual MeshManager& Meshes()=0;
    virtual const char* PlaybackDirectory() const=0;
    virtual void SetWarpFactor(double)=0;
    virtual double TimejumpDelta() const=0;
    virtual void RedrawCockpitAreas(int)=0;
    virtual const double* ParticleLevel(const oapi::ParticleStream*) const=0;
};
ORBITER_PRODUCTION_API VesselServices* BindVesselServices(VesselServices*);
ORBITER_PRODUCTION_API VesselServices& GetVesselServices();
}
#endif
