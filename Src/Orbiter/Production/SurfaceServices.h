// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SURFACE_SERVICES_H
#define ORBITER_PRODUCTION_SURFACE_SERVICES_H
#include "Export.h"
#include "CoreTypes.h"
#include "Vecmat.h"
#include "OrbiterHandles.h"
#include <filesystem>
#include <string>
class Config;
class Vessel;
class VesselBase;
namespace orbiter::production {
// Application services used by the original planet/base implementation. All
// object and camera queries refer to the owning production world.
class SurfaceServices {
public:
    virtual ~SurfaceServices() = default;
    virtual Config& Configuration() const = 0;
    virtual const char* Context() const = 0;
    virtual std::filesystem::path ConfigDirectory(const char*) const = 0;
    virtual std::filesystem::path MarkerDirectory(const char* body,const char* overridePath) const = 0;
    virtual void DeallocationProgress() = 0;
    virtual bool HasGraphics() const = 0;
    virtual SURFHANDLE LoadTexture(const char*,bool applicationSurface) = 0;
    virtual void ReleaseTexture(SURFHANDLE,bool applicationSurface) = 0;
    virtual VesselBase* VesselState(Vessel*) const = 0;
    virtual void Refuel(VesselBase&) = 0;
    virtual Vector CameraPosition() const = 0;
    virtual Vector CameraDirection() const = 0;
    virtual double CameraAperture() const = 0;
    virtual void Log(const std::string&) = 0;
};
ORBITER_PRODUCTION_API SurfaceServices* BindSurfaceServices(SurfaceServices*);
ORBITER_PRODUCTION_API SurfaceServices& GetSurfaceServices();
ORBITER_PRODUCTION_API void TraceSurfaceAllocation(const char* file,int line);
}
#endif
