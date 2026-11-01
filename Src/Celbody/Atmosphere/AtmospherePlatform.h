// Licensed under the MIT License
#ifndef ORBITER_ATMOSPHERE_PLATFORM_H
#define ORBITER_ATMOSPHERE_PLATFORM_H
#include <cmath>
#ifdef ORBITER_NATIVE_MODULE
#include "Production/NativeCelestialApi.h"
using AtmosphereBase=orbiter::native::Atmosphere;
using AtmosphereCelestial=orbiter::native::CelestialModule;
using AtmosphereBodyHandle=CelestialBody*;
using AtmosphereConstants=orbiter::native::AtmosphereConstants;
inline double AtmosphereSimMJD(AtmosphereCelestial* body) {return body->Host().SimulationMJD();}
inline void AtmosphereGlobalPosition(AtmosphereCelestial* body,AtmosphereBodyHandle handle,VECTOR3* result)
{*result=body->Host().GlobalPosition(*handle);}
inline void AtmosphereGlobalToEquatorial(AtmosphereCelestial* body,AtmosphereBodyHandle handle,const VECTOR3& p,double* lng,double* lat,double* radius)
{body->Host().GlobalToEquatorial(*handle,p,*lng,*lat,*radius);}
#else
#include "OrbiterAPI.h"
#include "CelbodyAPI.h"
using AtmosphereBase=ATMOSPHERE;
using AtmosphereCelestial=CELBODY2;
using AtmosphereBodyHandle=OBJHANDLE;
using AtmosphereConstants=ATMCONST;
inline double AtmosphereSimMJD(AtmosphereCelestial*) {return oapiGetSimMJD();}
inline void AtmosphereGlobalPosition(AtmosphereCelestial*,AtmosphereBodyHandle handle,VECTOR3* result)
{oapiGetGlobalPos(handle,result);}
inline void AtmosphereGlobalToEquatorial(AtmosphereCelestial*,AtmosphereBodyHandle handle,const VECTOR3& p,double* lng,double* lat,double* radius)
{oapiGlobalToEqu(handle,p,lng,lat,radius);}
#endif
inline VECTOR3 AtmosphereNegate(const VECTOR3& value) {return {-value.x,-value.y,-value.z};}
#endif
