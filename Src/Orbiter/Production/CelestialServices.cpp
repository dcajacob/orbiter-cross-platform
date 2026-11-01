// Licensed under the MIT License
#include "CelestialServices.h"
#include "RigidBodyServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { CelestialServices* bound = nullptr; }
CelestialServices* BindCelestialServices(CelestialServices* services)
{ auto* previous = bound; bound = services; return previous; }
CelestialServices& GetCelestialServices()
{
    if (!bound) throw std::logic_error("Production celestial services are not bound to a world");
    return *bound;
}
TimeData& CelestialClock() { return GetRigidBodyServices().Time(); }
}
