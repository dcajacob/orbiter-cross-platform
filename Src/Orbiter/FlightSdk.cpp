// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original world and vessel SDK methods shared by Windows and native modules.
#ifdef _WIN32
#define OAPI_IMPLEMENTATION
#include "Orbiter.h"
#include "Psys.h"
#else
#include "NativeVesselAPI.h"
#include "PsysCore.h"
#endif
#include "Production/CockpitServices.h"
#include "Production/GeometryConversions.h"
#include "Production/SurfaceNavigation.h"
#include "AstroMath.h"
#include "Vessel.h"
#include "Planet.h"
#include "Nav.h"
#include "TimeData.h"

OBJHANDLE oapiGetObjectByName (char *name)
{
	return (OBJHANDLE)(orbiter::production::CockpitWorld() ? orbiter::production::CockpitWorld()->GetObj (name, true) : 0);
}

OBJHANDLE oapiGetGbodyParent (OBJHANDLE hBody)
{
	return (OBJHANDLE)((CelestialBody*)hBody)->Primary();
}

double oapiGetEmptyMass (OBJHANDLE hVessel)
{
	return ((Vessel*)hVessel)->EmptyMass();
}

double oapiGetFuelMass (OBJHANDLE hVessel)
{
	return ((Vessel*)hVessel)->FuelMass();
}

double oapiGetMaxFuelMass (OBJHANDLE hVessel)
{
	return (((Vessel*)hVessel)->ntank ? ((Vessel*)hVessel)->tank[0]->maxmass : 0.0);
}

double oapiGetPropellantMaxMass (PROPELLANT_HANDLE ph)
{
	return ((TankSpec*)ph)->maxmass;
}

double oapiGetPropellantMass (PROPELLANT_HANDLE ph)
{
	return ((TankSpec*)ph)->mass;
}

PROPELLANT_HANDLE oapiGetPropellantHandle (OBJHANDLE hVessel, oapi::UInt32 idx)
{
	Vessel *vessel = (Vessel*)hVessel;
	return (idx < vessel->ntank ? (PROPELLANT_HANDLE)vessel->tank[idx] : 0);
}

DOCKHANDLE oapiGetDockHandle (OBJHANDLE hVessel, oapi::UInt n)
{
	Vessel *vessel = (Vessel*)hVessel;
	if (n < vessel->nDock()) return (DOCKHANDLE)vessel->GetDockParams(n);
	else return 0;
}

OBJHANDLE oapiGetDockStatus (DOCKHANDLE dock)
{
	return (OBJHANDLE)((PortSpec*)dock)->mate;
}

void oapiSetAutoCapture(DOCKHANDLE hDock, bool enable)
{
	((PortSpec*)hDock)->autodock = enable;
}

OBJHANDLE oapiGetDockOwner(DOCKHANDLE hDock)
{
	return (OBJHANDLE)((PortSpec*)hDock)->owner;
}

void oapiSetEmptyMass (OBJHANDLE hVessel, double mass)
{
	if ((Vessel*)hVessel) ((Vessel*)hVessel)->SetEmptyMass (mass);
}

void oapiGetGlobalVel (OBJHANDLE hObj, VECTOR3 *vel)
{
	if (((Body*)hObj)->s0) {
		Vector gv(((Body*)hObj)->GVel());
		vel->x = gv.x, vel->y = gv.y, vel->z = gv.z;
	}
}

void oapiGetFocusGlobalPos (VECTOR3 *pos)
{
	Vector gp(orbiter::production::CockpitFocus()->GPos());
	pos->x = gp.x, pos->y = gp.y, pos->z = gp.z;
}

void oapiGetFocusGlobalVel (VECTOR3 *vel)
{
	Vector gv(orbiter::production::CockpitFocus()->GVel());
	vel->x = gv.x, vel->y = gv.y, vel->z = gv.z;
}

void oapiGetRelativePos (OBJHANDLE hObj, OBJHANDLE hRef, VECTOR3 *pos)
{
	if (((Body*)hObj)->s0 && ((Body*)hRef)->s0) {
		Vector dp(((Body*)hObj)->GPos()-((Body*)hRef)->GPos());
		pos->x = dp.x, pos->y = dp.y, pos->z = dp.z;
	}
}

void oapiGetRelativeVel (OBJHANDLE hObj, OBJHANDLE hRef, VECTOR3 *vel)
{
	if (((Body*)hObj)->s0 && ((Body*)hRef)->s0) {
		Vector dv(((Body*)hObj)->GVel() - ((Body*)hRef)->GVel());
		vel->x = dv.x, vel->y = dv.y, vel->z = dv.z;
	}
}

void oapiGetFocusRelativePos (OBJHANDLE hRef, VECTOR3 *pos)
{
	if (((Body*)hRef)->s0) {
		Vector dp(orbiter::production::CockpitFocus()->GPos() - ((Body*)hRef)->GPos());
		pos->x = dp.x, pos->y = dp.y, pos->z = dp.z;
	}
}

void oapiGetFocusRelativeVel (OBJHANDLE hRef, VECTOR3 *vel)
{
	if (((Body*)hRef)->s0) {
		Vector dv(orbiter::production::CockpitFocus()->GVel() - ((Body*)hRef)->GVel());
		vel->x = dv.x, vel->y = dv.y, vel->z = dv.z;
	}
}

void oapiGlobalToLocal (OBJHANDLE hObj, const VECTOR3 *glob, VECTOR3 *loc)
{
	if (((Body*)hObj)->s0) {
		Vector vloc;
		((Body*)hObj)->GlobalToLocal(Vector(glob->x, glob->y, glob->z), vloc);
		loc->x = vloc.x, loc->y = vloc.y, loc->z = vloc.z;
	}
}

void oapiEquToGlobal (OBJHANDLE hObj, double lng, double lat, double rad, VECTOR3 *glob)
{
	if (((Body*)hObj)->s0) {
		Vector vglob;
		((Body*)hObj)->EquatorialToGlobal(lng, lat, rad, vglob);
		glob->x = vglob.x, glob->y = vglob.y, glob->z = vglob.z;
	}
}

double oapiOrthodome (double lng1, double lat1, double lng2, double lat2)
{
	return Orthodome (lng1, lat1, lng2, lat2);
}

int oapiGetAltitude (OBJHANDLE hVessel, double *alt)
{
	if ((Vessel*)hVessel) {
		const SurfParam *sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*alt = sp->alt0;
			return true;
		}
		else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetAltitude (OBJHANDLE hVessel, AltitudeMode mode, double *alt)
{
	if ((Vessel*)hVessel) {
		const SurfParam* sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*alt = (mode == ALTMODE_MEANRAD ? sp->alt0 : sp->alt);
			return true;
		}
		else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetPitch (OBJHANDLE hVessel, double *pitch)
{
	if ((Vessel*)hVessel) {
		const SurfParam *sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*pitch = sp->pitch;
			return true;
		} else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetBank (OBJHANDLE hVessel, double *bank)
{
	if ((Vessel*)hVessel) {
		const SurfParam *sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*bank = sp->bank;
			return true;
		}
		else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetHeading (OBJHANDLE hVessel, double *heading)
{
	if ((Vessel*)hVessel) {
		const SurfParam *sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*heading = sp->dir;
			return true;
		} else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetEquPos (OBJHANDLE hVessel, double *longitude, double *latitude, double *radius)
{
	if ((Vessel*)hVessel) {
		const SurfParam *sp = ((Vessel*)hVessel)->GetSurfParam();
		if (sp) {
			*longitude = sp->lng;
			*latitude  = sp->lat;
			*radius    = sp->rad;
			return true;
		} else {
			return false;
		}
	} else {
		return false;
	}
}

int oapiGetGroundspeed (OBJHANDLE hVessel, double *groundspeed)
{
	Vessel *v = (hVessel ? (Vessel*)hVessel : orbiter::production::CockpitFocus());
	const SurfParam *sp = v->GetSurfParam();
	if (sp) {
		*groundspeed = sp->groundspd;
		return true;
	} else {
		return false;
	}
}

bool oapiGetGroundspeedVector (OBJHANDLE hVessel, REFFRAME frame, VECTOR3 *vel)
{
	Vessel *v = (hVessel ? (Vessel*)hVessel : orbiter::production::CockpitFocus());
	const SurfParam *sp = v->GetSurfParam();
	if (sp) {
		switch (frame) {
		case FRAME_GLOBAL:
			vel->x = sp->groundvel_glob.x, vel->y = sp->groundvel_glob.y, vel->z = sp->groundvel_glob.z;
			return true;
		case FRAME_LOCAL:
			vel->x = sp->groundvel_ship.x, vel->y = sp->groundvel_ship.y, vel->z = sp->groundvel_ship.z;
			return true;
		case FRAME_REFLOCAL: {
			Vector hvel (tmul (sp->ref->GRot(), sp->groundvel_glob));
			vel->x = hvel.x, vel->y = hvel.y, vel->z = hvel.z;
			} return true;
		case FRAME_HORIZON: {
			Vector hvel (tmul (sp->ref->GRot(), sp->groundvel_glob));
			hvel.Set (mul (sp->L2H, hvel));
			vel->x = hvel.x, vel->y = hvel.y, vel->z = hvel.z;
			} return true;
		default:
			vel->x = vel->y = vel->z = 0.0;
			return false;
		}
	} else {
		vel->x = vel->y = vel->z = 0.0;
		return false;
	}
}

int oapiGetAirspeed (OBJHANDLE hVessel, double *airspeed)
{
	Vessel *v = (hVessel ? (Vessel*)hVessel : orbiter::production::CockpitFocus());
	const SurfParam *sp = v->GetSurfParam();
	if (sp) {
		*airspeed = sp->airspd;
		return true;
	} else {
		return false;
	}
}

bool oapiGetAirspeedVector (OBJHANDLE hVessel, REFFRAME frame, VECTOR3 *vel)
{
	Vessel *v = (hVessel ? (Vessel*)hVessel : orbiter::production::CockpitFocus());
	const SurfParam *sp = v->GetSurfParam();
	if (sp) {
		switch (frame) {
		case FRAME_GLOBAL:
			vel->x = sp->airvel_glob.x, vel->y = sp->airvel_glob.y, vel->z = sp->airvel_glob.z;
			return true;
		case FRAME_LOCAL:
			vel->x = sp->airvel_ship.x, vel->y = sp->airvel_ship.y, vel->z = sp->airvel_ship.z;
			return true;
		case FRAME_REFLOCAL: {
			Vector hvel (tmul (sp->ref->GRot(), sp->airvel_glob));
			vel->x = hvel.x, vel->y = hvel.y, vel->z = hvel.z;
			} return true;
		case FRAME_HORIZON: {
			Vector hvel (tmul (sp->ref->GRot(), sp->airvel_glob));
			hvel.Set (mul (sp->L2H, hvel));
			vel->x = hvel.x, vel->y = hvel.y, vel->z = hvel.z;
			} return true;
		default:
			vel->x = vel->y = vel->z = 0.0;
			return false;
		}
	} else {
		vel->x = vel->y = vel->z = 0.0;
		return false;
	}
}

void oapiGetAtm (OBJHANDLE hVessel, ATMPARAM *prm, OBJHANDLE *hAtmRef)
{
	Vessel *v = (hVessel ? (Vessel*)hVessel : orbiter::production::CockpitFocus());
	bool bAtm;

	if (!(bAtm = v->AtmPressureAndDensity (prm->p, prm->rho)))
		prm->p = prm->rho = 0.0;
	if (!v->AtmTemperature (prm->T))
		prm->T = 0.0;

	if (hAtmRef)
		*hAtmRef = (bAtm ? (OBJHANDLE)v->ProxyBody() : NULL);
}

VECTOR3 oapiGetGroundVector (OBJHANDLE hPlanet, double lng, double lat, int frame)
{
	return MakeVECTOR3 (((Planet*)hPlanet)->GroundVelocity (lng, lat, 0, frame));
}

double oapiGetSysStep ()
{
	return orbiter::production::CockpitTime().SysDT;
}

double oapiGetSimMJD ()
{
	return orbiter::production::CockpitTime().MJD0;
}

double oapiTime2MJD (double t)
{
	return orbiter::production::CockpitTime().MJD_ref + Day(t);
}

double oapiGetTimeAcceleration ()
{
	return orbiter::production::CockpitTime().Warp();
}

double oapiGetPlanetPeriod (OBJHANDLE hPlanet)
{
	return ((Planet*)hPlanet)->RotT();
}

void oapiGetPlanetObliquityMatrix (OBJHANDLE hPlanet, MATRIX3 *mat)
{
	const Matrix m = ((CelestialBody*)hPlanet)->RotObliq();
	for (int i = 0; i < 9; i++) mat->data[i] = m.data[i];
}

double oapiGetPlanetCurrentRotation (OBJHANDLE hPlanet)
{
	return ((CelestialBody*)hPlanet)->Rotation();
}

oapi::UInt32 oapiGetPlanetJCoeffCount (OBJHANDLE hPlanet)
{
	return ((CelestialBody*)hPlanet)->nJcoeff();
}

double oapiGetPlanetJCoeff (OBJHANDLE hPlanet, oapi::UInt32 n)
{
	CelestialBody *cb = (CelestialBody*)hPlanet;
	return (n < cb->nJcoeff() ? cb->Jcoeff(n) : 0.0);
}

oapi::UInt32 oapiGetNavChannel (NAVHANDLE hNav)
{
	return ((Nav*)hNav)->GetStep();
}

double oapiGetNavSignal (NAVHANDLE hNav, const VECTOR3 &gpos)
{
	return ((Nav*)hNav)->FieldStrength (MakeVector(gpos));
}

float oapiGetNavRange (NAVHANDLE hNav)
{
	return ((Nav*)hNav)->GetRange();
}

int oapiGetNavDescr (NAVHANDLE hNav, char *descr, int maxlen)
{
	return ((Nav*)hNav)->IdString (descr, maxlen);
}
