// Licensed under the MIT License
#include "WorldVesselServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace {WorldVesselServices* bound=nullptr;}
WorldVesselServices* BindWorldVesselServices(WorldVesselServices* value)
{auto* previous=bound;bound=value;return previous;}
WorldVesselServices& GetWorldVesselServices()
{
    if (!bound) throw std::logic_error("Production world vessel services are not bound");
    return *bound;
}
}
