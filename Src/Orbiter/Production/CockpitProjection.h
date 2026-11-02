// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_PROJECTION_H
#define ORBITER_PRODUCTION_COCKPIT_PROJECTION_H
#ifdef _WIN32
#include <d3d.h>
namespace orbiter::production {using CockpitPoint=D3DVECTOR;}
#else
#include "Export.h"
class Camera;class Vector;
namespace orbiter::production {
struct CockpitPoint {float x,y,z;};
ORBITER_PRODUCTION_API bool ProjectCockpitDirection(const Camera&,const Vector&,CockpitPoint&);
}
#endif
#endif
