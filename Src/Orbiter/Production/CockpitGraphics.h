// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#define ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#ifdef _WIN32
#include "GraphicsAPI.h"
namespace oapi {using CockpitClient=GraphicsClient;}
#else
#include "NativeGraphics.h"
namespace oapi {using CockpitClient=orbiter::production::NativeGraphics;}
#endif
#endif
