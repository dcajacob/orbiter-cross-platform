// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NAVIGATION_SERVICES_H
#define ORBITER_PRODUCTION_NAVIGATION_SERVICES_H
#include "CoreTypes.h"
#include "Export.h"
class Body;
class CelestialBody;
class Planet;
class Base;
class Vessel;
class Vector;
struct PortSpec;
namespace orbiter::production {
// Queries address the existing production objects. This keeps radio math and
// parsing independent of the still application-owned planet/vessel/UI headers.
class NavigationServices {
public:
    virtual ~NavigationServices() = default;
    virtual const CelestialBody& PlanetState(const Planet*) const = 0;
    virtual double TerrainHeight(const Planet*, double longitude, double latitude) const = 0;
    virtual const Planet* BasePlanet(const Base*) const = 0;
    virtual const Body& BaseState(const Base*) const = 0;
    virtual const Body& VesselState(const Vessel*) const = 0;
    virtual UInt32 DockCount(const Vessel*) const = 0;
    virtual const PortSpec* Dock(const Vessel*, UInt32 index) const = 0;
    virtual Vector DockPosition(const Vessel*, const PortSpec*) const = 0;
};
ORBITER_PRODUCTION_API NavigationServices* BindNavigationServices(NavigationServices* services);
ORBITER_PRODUCTION_API NavigationServices& GetNavigationServices();
}
#endif
