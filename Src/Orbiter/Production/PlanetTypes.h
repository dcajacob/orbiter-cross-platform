// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_PLANET_TYPES_H
#define ORBITER_PRODUCTION_PLANET_TYPES_H
#ifdef _WIN32
struct IDirectDrawSurface7;
#endif
namespace orbiter::production {
#ifdef _WIN32
using PlanetLegacyTexture=IDirectDrawSurface7*;
#else
// Unused legacy texture slots are opaque; native GPU resources belong to clients.
using PlanetLegacyTexture=void*;
#endif
}
#endif
