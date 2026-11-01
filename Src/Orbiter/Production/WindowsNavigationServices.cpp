// Licensed under the MIT License
#include "WindowsNavigationServices.h"
#include "Planet.h"
#include "Base.h"
#include "Vessel.h"
namespace orbiter::production {
namespace {
class WindowsNavigationServices final : public NavigationServices {
public:
    const CelestialBody& PlanetState(const Planet* planet) const override {return *planet;}
    double TerrainHeight(const Planet* planet,double longitude,double latitude) const override
    {return planet->Elevation(longitude,latitude);}
    const Planet* BasePlanet(const Base* base) const override {return base->RefPlanet();}
    const Body& BaseState(const Base* base) const override {return *base;}
    const Body& VesselState(const Vessel* vessel) const override {return *vessel;}
    UInt32 DockCount(const Vessel* vessel) const override {return vessel->nDock();}
    const PortSpec* Dock(const Vessel* vessel,UInt32 index) const override {return vessel->GetDockParams(index);}
    Vector DockPosition(const Vessel* vessel,const PortSpec* port) const override {return vessel->GetDockGPos(port);}
};
}
NavigationServices& GetWindowsNavigationServices()
{
    static WindowsNavigationServices services;return services;
}
}
