// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
namespace orbiter::production {
// The camera/session binds configuration before creating instrumentation on
// either host. Preserve the original live Config object, including UI writes.
inline Config* CockpitConfiguration() {return &GetCameraServices().Configuration();}
}
#endif
