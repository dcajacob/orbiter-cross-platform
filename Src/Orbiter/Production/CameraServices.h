// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_CAMERA_SERVICES_H
#define ORBITER_PRODUCTION_CAMERA_SERVICES_H
#include "Export.h"
#include <filesystem>
class Config;class Vessel;
namespace orbiter::production {
// Window/UI policy surrounding the original camera; world and projection math
// remain in Camera. Native external view rejects unavailable cockpit operations.
class CameraServices {
public:
    virtual ~CameraServices()=default;
    virtual Vessel* Focus() const=0;
    virtual Config& Configuration() const=0;
    virtual void SetFocus(Vessel*)=0;
    virtual void SetFOV(double)=0;
    virtual bool SetPanelMode(int)=0;
    virtual void SelectPanel(int)=0;
    virtual void SelectVC(int)=0;
    virtual std::filesystem::path ScenarioPath(const char*) const=0;
};
ORBITER_PRODUCTION_API CameraServices* BindCameraServices(CameraServices*);
ORBITER_PRODUCTION_API CameraServices& GetCameraServices();
}
#endif
