// Licensed under the MIT License
#ifndef ORBITER_NATIVE_WORLD_VESSEL_SERVICES_H
#define ORBITER_NATIVE_WORLD_VESSEL_SERVICES_H
#include "WorldVesselServices.h"
#include <memory>
namespace orbiter::production {
std::unique_ptr<WorldVesselServices> CreateNativeWorldVesselServices(bool& forceUpdate);
}
#endif
