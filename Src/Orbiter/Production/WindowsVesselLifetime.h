// Licensed under the MIT License
#pragma once
#include "VesselLifetime.h"
class Orbiter;
namespace orbiter::production {
class WindowsVesselLifetime final:public VesselLifetimeServices {
    Orbiter& app;
public:
    explicit WindowsVesselLifetime(Orbiter& value):app(value) {}
    PlanetarySystem*& LifetimeWorld() override;
    Camera*& LifetimeCamera() override;
    Vessel*& CurrentFocus() override;
    Vessel*& PreviousFocus() override;
    void SetView(Body*,int) override;
    void PaneFocusChanged(Vessel*) override;
    void ModuleFocusChanged(Vessel*,Vessel*) override;
    void DialogFocusChanged(Vessel*) override;
    void ModuleNewVessel(Vessel*) override;
    void GraphicsNewVessel(Vessel*) override;
    void DialogNewVessel(Vessel*) override;
    void ModuleDeleteVessel(Vessel*) override;
    void GraphicsDeleteVessel(Vessel*) override;
    void PaneDeleteVessel(Vessel*) override;
    void DialogDeleteVessel(Vessel*) override;
    void ConsoleDeleteVessel(Vessel*) override;
};
}
