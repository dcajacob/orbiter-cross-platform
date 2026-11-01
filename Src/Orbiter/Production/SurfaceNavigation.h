// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SURFACE_NAVIGATION_H
#define ORBITER_PRODUCTION_SURFACE_NAVIGATION_H
#include "Export.h"
#include "OrbiterCelestialData.h"
#include "OrbiterScalar.h"
ORBITER_PRODUCTION_API double Orthodome(double lng1,double lat1,double lng2,double lat2);
ORBITER_PRODUCTION_API void Orthodome(double lng1,double lat1,double lng2,double lat2,double& dist,double& dir);
ORBITER_PRODUCTION_API void Equ2Ecl(double cosob,double sinob,double ra,double dc,double& longitude,double& latitude);
ORBITER_PRODUCTION_API void Ecl2Equ(double cosob,double sinob,double longitude,double latitude,double& ra,double& dc);
namespace orbiter::production {
inline double SurfacePositiveAngle(double a)
{
    return orbiter::math::PositiveAngle(a,PI2);
}
}
#endif
