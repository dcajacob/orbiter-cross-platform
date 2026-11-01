// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "WorldOwner.h"
#include <stdexcept>
namespace orbiter::production {
WorldOwner::WorldOwner(WorldFactory& services) noexcept : factory(services) {}
WorldOwner::~WorldOwner() { Reset(); }
void WorldOwner::ResetCamera() noexcept
{
    if (camera) { factory.DestroyCamera(camera); camera = nullptr; }
}
void WorldOwner::ResetSystem() noexcept
{
    if (system) { factory.DestroySystem(system); system = nullptr; }
}
void WorldOwner::Reset() noexcept
{
    // Camera destructors may still consult the world. Vessel destructors see
    // the camera already released, as in the original DestroyWorld function.
    ResetCamera();
    ResetSystem();
}
bool WorldOwner::Initialize(const char* name)
{
    try {
        // Preserve the original replacement order: new camera, then new world.
        ResetCamera();
        camera = factory.CreateCamera();
        if (!camera) throw std::runtime_error("Production camera factory returned no object");
        ResetSystem();
        system = factory.CreateSystem(name);
        if (!system) throw std::runtime_error("Production world factory returned no object");
        if (!factory.HasObjects(system)) { Reset(); return false; }
        return true;
    } catch (...) {
        Reset();
        throw;
    }
}
}
