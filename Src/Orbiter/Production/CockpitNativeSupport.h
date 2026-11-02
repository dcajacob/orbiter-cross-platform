// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#define ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#include "RigidBodyServices.h"
#include "CockpitServices.h"
#include "OrbiterScalar.h"
#include "OrbiterGeometry.h"
#include "FlightKeys.h"
#include "ConfigFile.h"
#include "Config.h"
#include "Text.h"
#include <algorithm>
inline double normangle(double angle) {double a=fmod(angle,PI2);return a>=PI?a-PI2:a< -PI?a+PI2:a;}
inline double posangle(double angle) {return orbiter::math::PositiveAngle(angle,PI2);}
#define TRACENEW orbiter::production::GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
#endif
