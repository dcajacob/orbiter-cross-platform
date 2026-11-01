// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_WINDOWS_WORLD_H
#define ORBITER_WINDOWS_WORLD_H
#include "WorldOwner.h"
class Orbiter;
namespace orbiter::production {
class WindowsWorldFactory final : public WorldFactory {
public:
    explicit WindowsWorldFactory(Orbiter& application) : app(application) {}
    Camera* CreateCamera() override;
    PlanetarySystem* CreateSystem(const char* name) override;
    bool HasObjects(const PlanetarySystem* system) const override;
    void DestroyCamera(Camera* camera) noexcept override;
    void DestroySystem(PlanetarySystem* system) noexcept override;
private:
    Orbiter& app;
};
}
#endif
