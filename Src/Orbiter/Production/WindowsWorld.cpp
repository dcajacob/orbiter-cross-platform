// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "WindowsWorld.h"
#include "Orbiter.h"
#include "Psys.h"
#include "Camera.h"
#include "Log.h"
extern Camera* g_camera;
extern PlanetarySystem* g_psys;
extern double g_nearplane, g_farplane;
namespace orbiter::production {
Camera* WindowsWorldFactory::CreateCamera()
{
    g_camera = new Camera(g_nearplane, g_farplane); TRACENEW
    g_camera->ResizeViewport(app.viewW, app.viewH);
    return g_camera;
}
PlanetarySystem* WindowsWorldFactory::CreateSystem(const char* name)
{
    auto status = [](const char* message, int line, void* context) {
        static_cast<Orbiter*>(context)->OutputLoadStatus(message, line);
    };
    g_psys = new PlanetarySystem(const_cast<char*>(name), app.pConfig, status, &app); TRACENEW
    return g_psys;
}
bool WindowsWorldFactory::HasObjects(const PlanetarySystem* system) const { return system->nObj() != 0; }
void WindowsWorldFactory::DestroyCamera(Camera* camera) noexcept
{
    delete camera;
    g_camera = nullptr;
}
void WindowsWorldFactory::DestroySystem(PlanetarySystem* system) noexcept
{
    delete system;
    g_psys = nullptr;
}
}
