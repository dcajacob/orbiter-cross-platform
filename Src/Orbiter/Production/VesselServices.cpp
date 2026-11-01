// Licensed under the MIT License
#include "VesselServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace {VesselServices* services=nullptr;}
VesselServices* BindVesselServices(VesselServices* next)
{auto* previous=services;services=next;return previous;}
VesselServices& GetVesselServices()
{if (!services) throw std::logic_error("Production vessel services are not bound");return *services;}
}
