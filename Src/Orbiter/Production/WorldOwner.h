// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_WORLD_OWNER_H
#define ORBITER_PRODUCTION_WORLD_OWNER_H
#include "Export.h"

class PlanetarySystem;
class Camera;
namespace orbiter::production {
// Factories create the authoritative engine objects. Windows additionally
// publishes the legacy application aliases, at their original lifecycle points.
// The factory and all module/platform services must outlive the owner.
class WorldFactory {
public:
    virtual ~WorldFactory() = default;
    virtual Camera* CreateCamera() = 0;
    virtual PlanetarySystem* CreateSystem(const char* name) = 0;
    virtual bool HasObjects(const PlanetarySystem* system) const = 0;
    virtual void DestroyCamera(Camera* camera) noexcept = 0;
    virtual void DestroySystem(PlanetarySystem* system) noexcept = 0;
};

// Internal, single-owner world lifetime. No UI objects or SDK interfaces are
// owned here. Numerical initialization and callbacks remain in the real classes.
class ORBITER_PRODUCTION_API WorldOwner {
public:
    explicit WorldOwner(WorldFactory& factory) noexcept;
    ~WorldOwner();
    WorldOwner(const WorldOwner&) = delete;
    WorldOwner& operator=(const WorldOwner&) = delete;
    bool Initialize(const char* systemName);
    void Reset() noexcept;
    Camera* Observer() const noexcept { return camera; }
    PlanetarySystem* System() const noexcept { return system; }
private:
    void ResetCamera() noexcept;
    void ResetSystem() noexcept;
    WorldFactory& factory;
    Camera* camera = nullptr;
    PlanetarySystem* system = nullptr;
};
}
#endif
