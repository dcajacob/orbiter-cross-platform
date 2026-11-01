// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_VESSEL_SERVICES_H
#define ORBITER_PRODUCTION_VESSEL_SERVICES_H
#include "Export.h"
#include "CoreTypes.h"
#include "OrbiterVesselData.h"
#include <filesystem>
class MeshManager;
class Vessel;
class Vector;
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
    virtual void InsertVessel(Vessel*)=0;
    virtual double ManualControl(THGROUP_TYPE,UInt32 device) const=0;
    virtual void NotifyJump(const Vessel&,const Vector&)=0;
    virtual void ShiftCockpit(const Vessel&,const Vector&)=0;
    virtual std::filesystem::path RecorderFile(const char*,bool writing)=0;
    virtual void PlaybackWarp(double warp,double delay)=0;
    virtual void RecallCameraPreset(int)=0;
    virtual void PlaybackNote(char*)=0;
    virtual void EndPlayback()=0;
};
ORBITER_PRODUCTION_API VesselServices* BindVesselServices(VesselServices*);
ORBITER_PRODUCTION_API VesselServices& GetVesselServices();
}
#endif
