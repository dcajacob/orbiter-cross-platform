// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifdef _WIN32
#define OAPI_IMPLEMENTATION
#include "OrbiterAPI.h"
#include "Log.h"
#else
#define LOGOUT_OBSOLETE {static bool once=true; if(once) {orbiter::production::VesselLog("Obsolete vessel API: %s",__func__);once=false;}}
#endif
#include "Vessel.h"
#include "SuperVessel.h"
#include "Config.h"
#include "Element.h"
#include "PsysCore.h"
#include "Planet.h"
#include "Star.h"
#include "Base.h"
#include "Nav.h"
#include "Mesh.h"
#include "Production/RigidBodyServices.h"
#include "Production/SurfaceServices.h"
#include "Production/GeometryConversions.h"
#include "Production/VesselCoreSupport.h"
#include <algorithm>
#include <cstring>
using namespace std;
using namespace orbiter::production;
static VECTOR3 DefExhaustDir[4] = {{0,0,-1}, {0,0,1}, {0,-1,0}, {0,0,-1}};

VESSEL::VESSEL (OBJHANDLE hvessel, int fmodel)
{
	vessel = (Vessel*)hvessel;
	flightmodel = (short)fmodel;
	version = 0;
}

OBJHANDLE VESSEL::Create (const char *name, const char *classname, const VESSELSTATUS &status)
{
	Vessel *vessel = new Vessel (GetRigidBodyServices().World(), name, classname, status); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	GetVesselServices().InsertVessel (vessel);
	return (OBJHANDLE)vessel;
}

const OBJHANDLE VESSEL::GetHandle () const
{
	return (OBJHANDLE)vessel;
}

char *VESSEL::GetName () const
{
	return (char*)vessel->Name();
}

char *VESSEL::GetClassName () const
{
	return vessel->classname;
}

int VESSEL::GetFlightModel () const
{
	return vessel->flightmodel;
}

int VESSEL::GetDamageModel () const
{
	return GetSurfaceServices().Configuration().CfgLogicPrm.DamageSetting;
}

bool VESSEL::GetEnableFocus () const
{
	return vessel->GetEnableFocus ();
}

double VESSEL::GetSize () const
{
	return vessel->Size();
}

double VESSEL::GetClipRadius () const
{
	return vessel->ClipRadius();
}

void VESSEL::SetClipRadius (double rad) const
{
	vessel->SetClipRadius (rad);
}

double VESSEL::GetMass () const
{
	return vessel->Mass();
}

double VESSEL::GetEmptyMass () const
{
	return vessel->EmptyMass();
}

double VESSEL::GetMaxFuelMass () const
{
	TankSpec *ts = vessel->DefaultPropellantHandle();
	return (ts ? ts->maxmass : 0.0);
}

double VESSEL::GetFuelMass () const
{
	TankSpec *ts = vessel->DefaultPropellantHandle();
	return (ts ? ts->mass : 0.0);
}

double VESSEL::GetFuelRate () const
{
	TankSpec *ts = vessel->DefaultPropellantHandle();
	return (ts ? vessel->GetPropellantFlowrate (ts) : 0.0);
}

double VESSEL::GetISP () const
{
	return vessel->m_defaultIsp;
}

double VESSEL::GetMaxThrust (ENGINETYPE eng) const
{
	switch (eng) {
	case ENGINE_MAIN:     return vessel->GetThrusterGroupMaxth (THGROUP_MAIN);
	case ENGINE_RETRO:    return vessel->GetThrusterGroupMaxth (THGROUP_RETRO);
	case ENGINE_HOVER:    return vessel->GetThrusterGroupMaxth (THGROUP_HOVER);
	case ENGINE_ATTITUDE: return vessel->GetThrusterGroupMaxth (THGROUP_ATT_PITCHUP);
		// assuming all attitude thruster groups are defined with the same maxth
	default:              return 0.0;
	}
}

double VESSEL::GetEngineLevel (ENGINETYPE eng) const
{
	switch (eng) {
	case ENGINE_MAIN:	  return vessel->GetThrusterGroupLevel (THGROUP_MAIN);
	case ENGINE_RETRO:	  return vessel->GetThrusterGroupLevel (THGROUP_RETRO);
	case ENGINE_HOVER:	  return vessel->GetThrusterGroupLevel (THGROUP_HOVER);
	default:              return 0.0;
	}
}

double *VESSEL::GetMainThrustModPtr (void) const
{
	static double dummy = 0.0;
	return &dummy;
}

int VESSEL::GetAttitudeMode () const
{
	return vessel->AttMode();
}

bool VESSEL::SetAttitudeMode (int mode) const
{
	return vessel->SetAttMode (mode);
}

oapi::UInt32 VESSEL::GetADCtrlMode () const
{
	return vessel->ctrlsurfmode;
}

void VESSEL::SetADCtrlMode (oapi::UInt32 mode) const
{
	vessel->SetADCtrlMode (mode);
}

void VESSEL::GetAttitudeRotLevel (VECTOR3 &th) const
{
	th.x = GetThrusterGroupLevel (THGROUP_ATT_PITCHUP) - GetThrusterGroupLevel (THGROUP_ATT_PITCHDOWN);
	th.y = GetThrusterGroupLevel (THGROUP_ATT_YAWLEFT) - GetThrusterGroupLevel (THGROUP_ATT_YAWRIGHT);
	th.z = GetThrusterGroupLevel (THGROUP_ATT_BANKRIGHT) - GetThrusterGroupLevel (THGROUP_ATT_BANKLEFT);
}

void VESSEL::GetAttitudeLinLevel (VECTOR3 &th) const
{
	th.x = GetThrusterGroupLevel (THGROUP_ATT_RIGHT) - GetThrusterGroupLevel (THGROUP_ATT_LEFT);
	th.y = GetThrusterGroupLevel (THGROUP_ATT_UP) - GetThrusterGroupLevel (THGROUP_ATT_DOWN);
	th.z = GetThrusterGroupLevel (THGROUP_ATT_FORWARD) - GetThrusterGroupLevel (THGROUP_ATT_BACK);
}

int VESSEL::ToggleAttitudeMode () const
{
	return vessel->ToggleAttMode();
}

double VESSEL::GetManualControlLevel (THGROUP_TYPE thgt, oapi::UInt32 mode, oapi::UInt32 device) const
{
	static int revmode[3] = {0,2,1};

	double lvl = GetVesselServices().ManualControl (thgt, device);
	int md;
	switch (mode) {
	case MANCTRL_ATTMODE: md = vessel->attmode; break;
	case MANCTRL_REVMODE: md = revmode[vessel->attmode]; break;
	case MANCTRL_ROTMODE: md = 1; break;
	case MANCTRL_LINMODE: md = 2; break;
	case MANCTRL_ANYMODE: md = 3; break;
	}
	if (thgt >= THGROUP_ATT_PITCHUP && thgt <= THGROUP_ATT_BANKRIGHT)
		return ((md & 1) ? lvl : 0);
	if (thgt >= THGROUP_ATT_RIGHT && thgt <= THGROUP_ATT_BACK)
		return ((md & 2) ? lvl : 0);
	return 0;
}


double VESSEL::GetCOG_elev () const
{
	return vessel->cog_elev;
}

void VESSEL::GetCrossSections (VECTOR3 &cs) const
{
	cs.x = vessel->cs.x;
	cs.y = vessel->cs.y;
	cs.z = vessel->cs.z;
}

void VESSEL::GetCW (double &cw_z_pos, double &cw_z_neg, double &cw_x, double &cw_y) const
{
	cw_z_pos = vessel->CWz[0];
	cw_z_neg = vessel->CWz[1];
	cw_x     = vessel->CWx;
	cw_y     = vessel->CWy;
}

double VESSEL::GetWingAspect () const
{
	return vessel->wingaspect;
}

double VESSEL::GetWingEffectiveness () const
{
	return vessel->wingeff;
}

void VESSEL::GetRotDrag (VECTOR3 &rd) const
{
	rd.x = vessel->rdrag.x;
	rd.y = vessel->rdrag.y;
	rd.z = vessel->rdrag.z;
}

void VESSEL::GetPMI (VECTOR3 &pmi) const
{
	pmi.x = vessel->pmi.x;
	pmi.y = vessel->pmi.y;
	pmi.z = vessel->pmi.z;
}

void VESSEL::GetCameraOffset (VECTOR3 &co) const
{
	co.x = vessel->campos.x;
	co.y = vessel->campos.y;
	co.z = vessel->campos.z;
}

void VESSEL::GetCameraDefaultDirection (VECTOR3 &cd) const
{
	cd.x = vessel->camdir0.x;
	cd.y = vessel->camdir0.y;
	cd.z = vessel->camdir0.z;
}

double VESSEL::GetAtmTemperature () const
{
	return (vessel->sp.is_in_atm ? vessel->sp.atmT : 0.0);
}

double VESSEL::GetAtmDensity () const
{
	return (vessel->sp.is_in_atm ? vessel->sp.atmrho : 0.0);
}

double VESSEL::GetAtmPressure () const
{
	return (vessel->sp.is_in_atm ? vessel->sp.atmp : 0.0);
}

double VESSEL::GetDynPressure () const
{
	return (vessel->sp.is_in_atm ? vessel->sp.dynp : 0.0);
}

double VESSEL::GetMachNumber () const
{
	return (vessel->sp.is_in_atm ? vessel->sp.atmM : 0.0);
}

void VESSEL::GetStatus (VESSELSTATUS &status) const
{
	vessel->GetState (status);
}

void VESSEL::GetStatusEx (void *status) const
{
	vessel->GetStateEx (status);
}

oapi::UInt32 VESSEL::GetFlightStatus () const
{
	oapi::UInt32 status = (vessel->fstatus == FLIGHTSTATUS_LANDED ? 0x1:0x0);
	if (vessel->supervessel) status |= 0x2;
	return status;
}

const OBJHANDLE VESSEL::GetGravityRef () const
{
	return (OBJHANDLE)vessel->cbody;
}

const OBJHANDLE VESSEL::GetSurfaceRef () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp)	return (OBJHANDLE)sp->ref;
	else return NULL;
}

const OBJHANDLE VESSEL::GetAtmRef () const
{
	return (vessel->sp.is_in_atm ? (OBJHANDLE)vessel->GetSurfParam()->ref : 0);
}

void VESSEL::GetGlobalPos (VECTOR3 &pos) const
{
	pos.x = vessel->s0->pos.x;
	pos.y = vessel->s0->pos.y;
	pos.z = vessel->s0->pos.z;
}

void VESSEL::GetGlobalVel (VECTOR3 &vel) const
{
	vel.x = vessel->s0->vel.x;
	vel.y = vessel->s0->vel.y;
	vel.z = vessel->s0->vel.z;
}

void VESSEL::GetRelativePos (OBJHANDLE hRef, VECTOR3 &pos) const
{
	Vector dp (vessel->GPos() - ((Body*)hRef)->GPos());
	pos.x = dp.x;
	pos.y = dp.y;
	pos.z = dp.z;
}

void VESSEL::GetRelativeVel (OBJHANDLE hRef, VECTOR3 &vel) const
{
	Vector dv (vessel->GVel() - ((Body*)hRef)->GVel());
	vel.x = dv.x;
	vel.y = dv.y;
	vel.z = dv.z;
}

void VESSEL::GetLinearMoment (VECTOR3 &F) const
{
	F.x = vessel->Flin.x;
	F.y = vessel->Flin.y;
	F.z = vessel->Flin.z;
}

void VESSEL::GetAngularVel (VECTOR3 &avel) const
{
	avel.x = vessel->s0->omega.x;
	avel.y = vessel->s0->omega.y;
	avel.z = vessel->s0->omega.z;
}

void VESSEL::SetAngularVel (const VECTOR3 &avel) const
{
	vessel->SetAngVel (MakeVector (avel));
}

void VESSEL::GetAngularAcc (VECTOR3 &aacc) const
{
	aacc.x = vessel->arot.x;
	aacc.y = vessel->arot.y;
	aacc.z = vessel->arot.z;
}

void VESSEL::GetAngularMoment (VECTOR3 &amom) const
{
	amom.x = vessel->Amom.x;
	amom.y = vessel->Amom.y;
	amom.z = vessel->Amom.z;
}

void VESSEL::GetGlobalOrientation (VECTOR3 &arot) const
{
	EulerAngles (vessel->s0->R, arot);
}

void VESSEL::SetGlobalOrientation (const VECTOR3 &arot) const
{
	vessel->SetGlobalOrientation (MakeVector (arot));
}

OBJHANDLE VESSEL::GetEquPos (double &longitude, double &latitude, double &radius) const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		longitude = sp->lng;
		latitude  = sp->lat;
		radius    = sp->rad;
		return (OBJHANDLE)sp->ref;
	} else {
		return NULL;
	}
}

double VESSEL::GetAltitude (void) const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) return sp->alt0;
	else    return 0.0;
}

double VESSEL::GetAltitude (AltitudeMode mode, int *reslvl)
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		if (mode == ALTMODE_MEANRAD) {
			if (reslvl) *reslvl = 0;
			return sp->alt0;
		} else {
			if (reslvl) *reslvl = sp->elev_lvl;
			return sp->alt;
		}
	} else {
		if (reslvl) *reslvl = 0;
		return 0.0;
	}
}

double VESSEL::GetGroundspeed () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) return sp->groundspd;
	else    return 0.0;
}

bool VESSEL::GetGroundspeedVector (REFFRAME frame, VECTOR3 &v) const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		switch (frame) {
		case FRAME_GLOBAL:
			v.x = sp->groundvel_glob.x, v.y = sp->groundvel_glob.y, v.z = sp->groundvel_glob.z;
			return true;
		case FRAME_LOCAL:
			v.x = sp->groundvel_ship.x, v.y = sp->groundvel_ship.y, v.z = sp->groundvel_ship.z;
			return true;
		case FRAME_REFLOCAL: {
			Vector hvel (tmul (sp->ref->GRot(), sp->groundvel_glob));
			v.x = hvel.x, v.y = hvel.y, v.z = hvel.z;
			} return true;
		case FRAME_HORIZON: {
			Vector hvel (tmul (sp->ref->GRot(), sp->groundvel_glob));
			hvel.Set (mul (sp->L2H, hvel));
			v.x = hvel.x, v.y = hvel.y, v.z = hvel.z;
			} return true;
		default:
			v.x = v.y = v.z = 0.0;
			return false;
		}
	} else {
		v.x = v.y = v.z = 0.0;
		return false;
	}
}

double VESSEL::GetAirspeed (void) const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) return sp->airspd;
	else    return 0.0;
}

bool VESSEL::GetAirspeedVector (REFFRAME frame, VECTOR3 &v) const
{
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		switch (frame) {
		case FRAME_GLOBAL:
			v.x = sp->airvel_glob.x, v.y = sp->airvel_glob.y, v.z = sp->airvel_glob.z;
			return true;
		case FRAME_LOCAL:
			v.x = sp->airvel_ship.x, v.y = sp->airvel_ship.y, v.z = sp->airvel_ship.z;
			return true;
		case FRAME_REFLOCAL: {
			Vector hvel (tmul (sp->ref->GRot(), sp->airvel_glob));
			v.x = hvel.x, v.y = hvel.y, v.z = hvel.z;
			} return true;
		case FRAME_HORIZON: {
			Vector hvel (tmul (sp->ref->GRot(), sp->airvel_glob));
			hvel.Set (mul (sp->L2H, hvel));
			v.x = hvel.x, v.y = hvel.y, v.z = hvel.z;
			} return true;
		default:
			v.x = v.y = v.z = 0.0;
			return false;
		}
	} else {
		v.x = v.y = v.z = 0.0;
		return false;
	}
}

bool VESSEL::GetShipAirspeedVector (VECTOR3 &v) const
{
	LOGOUT_OBSOLETE;
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		v.x = sp->airvel_ship.x, v.y = sp->airvel_ship.y, v.z = sp->airvel_ship.z;
		return true;
	} else {
		v.x = v.y = v.z = 0.0;
		return false;
	}
}

bool VESSEL::GetHorizonAirspeedVector (VECTOR3 &v) const
{
	LOGOUT_OBSOLETE;
	const SurfParam *sp = vessel->GetSurfParam();
	if (sp) {
		Vector hvel (tmul (sp->ref->GRot(), sp->airvel_glob));
		hvel.Set (mul (sp->L2H, hvel));
		v.x = hvel.x, v.y = hvel.y, v.z = hvel.z;
		return true;
	} else {
		v.x = v.y = v.z = 0.0;
		return false;
	}
}

double VESSEL::GetAOA () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? -atan2 (sp->airvel_ship.y, sp->airvel_ship.z): 0.0;
}

double VESSEL::GetSlipAngle () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? -atan2 (sp->airvel_ship.x, sp->airvel_ship.z): 0.0;
}

double VESSEL::GetPitch () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? sp->pitch: 0.0;
}

double VESSEL::GetBank () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? sp->bank: 0.0;
}

double VESSEL::GetYaw () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? sp->dir: 0.0;
}

double VESSEL::GetSurfaceElevation () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? sp->elev: 0.0;
}

VECTOR3 VESSEL::GetSurfaceNormal () const
{
	const SurfParam *sp = vessel->GetSurfParam();
	return sp ? _V(sp->surfnml.x, sp->surfnml.y, sp->surfnml.z): _V(0,0,0);
}

double VESSEL::GetLift (void) const
{
	return vessel->Lift;
}

double VESSEL::GetDrag (void) const
{
	return vessel->Drag;
}

double VESSEL::GetSideForce() const
{
	return vessel->SideForce;
}

bool VESSEL::GetWeightVector (VECTOR3 &G) const
{
	static Vector F;
	bool bWeight = vessel->GetWeightVector (F);
	CopyVector (F, G);
	return bWeight;
}

bool VESSEL::GetThrustVector (VECTOR3 &T) const
{
	static Vector F;
	bool bThrust = vessel->GetThrustVector (F);
	CopyVector (F, T);
	return bThrust;
}

bool VESSEL::GetLiftVector (VECTOR3 &L) const
{
	static Vector F;
	bool bLift = vessel->GetLiftVector (F);
	CopyVector (F, L);
	return bLift;
}

bool VESSEL::GetDragVector (VECTOR3 &D) const
{
	static Vector F;
	bool bDrag = vessel->GetDragVector (F);
	CopyVector (F, D);
	return bDrag;
}

bool VESSEL::GetSideForceVector(VECTOR3 &SF) const
{
	static Vector F;
	bool bSideForce = vessel->GetSideForceVector(F);
	CopyVector(F, SF);
	return bSideForce;
}

bool VESSEL::GetForceVector (VECTOR3 &F) const
{
	static Vector FF;
	bool bForce = vessel->GetForceVector (FF);
	CopyVector (FF, F);
	return bForce;
}

bool VESSEL::GetTorqueVector (VECTOR3 &M) const
{
	static Vector F;
	bool bTorque = vessel->GetTorqueVector (F);
	CopyVector (F, M);
	return bTorque;
}

OBJHANDLE VESSEL::GetElements (ELEMENTS &el, double &mjd_ref) const
{
	const Elements *els = vessel->Els();
	if (els) {
		el.a      = els->a;
		el.e      = els->e;
		el.i      = els->i;
		el.theta  = els->theta;
		el.omegab = els->omegab;
		el.L      = els->L;
		mjd_ref   = els->MJDepoch();
		return (OBJHANDLE)vessel->cbody;
	} else {
		return NULL;
	}
}

bool VESSEL::GetElements (OBJHANDLE hRef, ELEMENTS &el, ORBITPARAM *prm, double mjd_ref, int frame) const
{
	const CelestialBody *ref = (hRef ? (CelestialBody*)hRef : vessel->cbody);
	Elements els (1, 0, 0, 0, 0, 0, mjd_ref ? mjd_ref : GetRigidBodyServices().Time().MJD0, GetRigidBodyServices().Time().MJD_ref);
	els.SetMasses (0, ref->Mass());
	Vector p (vessel->GPos()-ref->GPos());
	Vector v (vessel->GVel()-ref->GVel());

	// rotate ecliptic -> equatorial frame
	if (frame == FRAME_EQU) {
		p = tmul (ref->RotObliq(), p);
		v = tmul (ref->RotObliq(), v);
	}
	// calculate primary elements
	els.Calculate (p, v, GetRigidBodyServices().Time().SimT0);
	el.a      = els.a;
	el.e      = els.e;
	el.i      = els.i;
	el.theta  = els.theta;
	el.omegab = els.omegab;
	el.L      = els.L;

	// retrieve additional parameters, if requested
	if (prm) {
		prm->SMi = els.SMi();
		prm->PeD = els.PeDist();
		prm->ApD = (els.e < 1.0 ? els.ApDist() : 0.0);
		prm->MnA = els.MeanAnm();
		prm->TrA = els.TrueAnm();
		prm->MnL = els.MeanLng();
		prm->TrL = els.TrueLng();
		prm->EcA = els.EccAnm();
		prm->Lec = els.LinEcc();
		prm->T = (els.e < 1.0 ? els.OrbitT() : 0.0);
		prm->PeT = els.PeT();
		prm->ApT = (els.e < 1.0 ? els.ApT() : 0.0);
	}
	return true;
}

bool VESSEL::SetElements (OBJHANDLE hRef, const ELEMENTS &el, ORBITPARAM *prm, double mjd_ref, int frame) const
{
	const CelestialBody *ref = (hRef ? (CelestialBody*)hRef : vessel->cbody);
	Elements els(GetRigidBodyServices().Time().MJD_ref);
	if (!mjd_ref) mjd_ref = GetRigidBodyServices().Time().MJD0;
	els.Set (el.a, el.e, el.i, el.theta, el.omegab, el.L, mjd_ref, GetRigidBodyServices().Time().MJD_ref);
	els.Setup (0, ref->Mass(), mjd_ref, GetRigidBodyServices().Time().MJD_ref);
	Vector p, v;
	if (prm) {
		els.Update (p, v, GetRigidBodyServices().Time().SimT1);
		prm->SMi = els.SMi();
		prm->PeD = els.PeDist();
		prm->ApD = (els.e < 1.0 ? els.ApDist() : 0.0);
		prm->MnA = els.MeanAnm();
		prm->TrA = els.TrueAnm();
		prm->MnL = els.MeanLng();
		prm->TrL = els.TrueLng();
		prm->EcA = els.EccAnm();
		prm->Lec = els.LinEcc();
		prm->T = (els.e < 1.0 ? els.OrbitT() : 0.0);
		prm->PeT = els.PeT();
		prm->ApT = (els.e < 1.0 ? els.ApT() : 0.0);
	} else {
		els.PosVel (p, v, GetRigidBodyServices().Time().SimT0);
	}
	if (frame == FRAME_EQU) { // rotate equatorial -> ecliptic frame
		p = mul (ref->RotObliq(), p);
		v = mul (ref->RotObliq(), v);
	}
	if (p.length() < ref->Size())
		return false; // don't allow vessel below planet surface

	vessel->RPlace (p + ref->GPos(), v + ref->GVel());

	return true;
}

OBJHANDLE VESSEL::GetArgPer (double &arg) const
{
	const Elements *els = vessel->Els();
	if (els) {
		arg = els->ArgPer();
		return (OBJHANDLE)vessel->cbody;
	} else return NULL;
}

OBJHANDLE VESSEL::GetSMi (double &smi) const
{
	const Elements *els = vessel->Els();
	if (els) {
		smi = els->SMi();
		return (OBJHANDLE)vessel->cbody;
	} else return NULL;
}

OBJHANDLE VESSEL::GetApDist (double &apdist) const
{
	const Elements *els = vessel->Els();
	if (els) {
		apdist = els->ApDist();
		return (OBJHANDLE)vessel->cbody;
	} else return NULL;
}

OBJHANDLE VESSEL::GetPeDist (double &pedist) const
{
	const Elements *els = vessel->Els();
	if (els) {
		pedist = els->PeDist();
		return (OBJHANDLE)vessel->cbody;
	} else return NULL;
}

void VESSEL::SetEnableFocus (bool enable) const
{
	vessel->SetEnableFocus (enable);
}

void VESSEL::SetSize (double size) const
{
	vessel->SetSize (size);
}

void VESSEL::SetVisibilityLimit (double vislimit, double spotlimit) const
{
	vessel->vislimit = vislimit;
	vessel->spotlimit = (spotlimit >= 0 ? spotlimit : vislimit);
}

void VESSEL::SetEmptyMass (double m) const
{
	vessel->SetEmptyMass (m);
}

void VESSEL::SetMaxFuelMass (double mass) const
{
	TankSpec *ts = vessel->DefaultPropellantHandle();
	if (ts) vessel->SetPropellantMaxMass (ts, mass);
	else    vessel->CreatePropellantResource (mass);
}

void VESSEL::SetFuelMass (double mass) const
{
	TankSpec *ts = vessel->DefaultPropellantHandle();
	if (ts) vessel->SetPropellantMass (ts, mass);
}

bool VESSEL::SetGravityGradientDamping (double damp) const
{
	return vessel->SetGravityGradientDamping (damp);
}

double VESSEL::GetGravityGradientDamping () const
{
	return vessel->GetGravityGradientDamping ();
}

void VESSEL::SetISP (double isp) const
{
	vessel->m_defaultIsp = isp;
}

void VESSEL::SetMaxThrust (ENGINETYPE eng, double th) const
{
	// obsolete; we are translating this into the new thruster interface
	// for backward compatibility

	switch (eng) {
	case ENGINE_MAIN:
	case ENGINE_RETRO:
	case ENGINE_HOVER:
		vessel->SetMaxThrust_old (eng, th);
		break;
	case ENGINE_ATTITUDE:
		vessel->CreateDefaultAttitudeSet (th);
		break;
	}
}

void VESSEL::SetEngineLevel (ENGINETYPE eng, double level) const
{
	// OBSOLETE: replaced by SetThrusterGroupLevel

	switch (eng) {
	case ENGINE_RETRO:
		level = -level; // fall through
	case ENGINE_MAIN:
		if (level >= 0) {
			vessel->SetThrusterGroupLevel (THGROUP_MAIN, level);
			vessel->SetThrusterGroupLevel (THGROUP_RETRO, 0.0);
		} else {
			vessel->SetThrusterGroupLevel (THGROUP_MAIN, 0.0);
			vessel->SetThrusterGroupLevel (THGROUP_RETRO, -level);
		}
		break;
	case ENGINE_HOVER:
		vessel->SetThrusterGroupLevel (THGROUP_HOVER, level);
		break;
	}
}

void VESSEL::IncEngineLevel (ENGINETYPE eng, double dlevel) const
{
	// OBSOLETE: replaced by IncThrusterGroupLevel

	if (eng <= ENGINE_HOVER)
		vessel->IncThrusterGroupLevel ((THGROUP_TYPE)eng, dlevel);
	// relying on the fact that for main, retro and hover engines
	// ENGINETYPE and THGROUP_TYPE enums are equivalent
}

void VESSEL::SetAttitudeRotLevel (const VECTOR3 &th) const
{
	// First, zero all attitude thruster levels
	for (THGROUP_TYPE thg = THGROUP_ATT_PITCHUP; thg <= THGROUP_ATT_BANKRIGHT; thg = (THGROUP_TYPE)(thg+1))
		SetThrusterGroupLevel (thg, 0.0);

	// Then add the commanded levels
	if (th.x >= 0.0) IncThrusterGroupLevel (THGROUP_ATT_PITCHUP,    th.x);
	else             IncThrusterGroupLevel (THGROUP_ATT_PITCHDOWN, -th.x);
	if (th.y >= 0.0) IncThrusterGroupLevel (THGROUP_ATT_YAWLEFT,    th.y);
	else             IncThrusterGroupLevel (THGROUP_ATT_YAWRIGHT,  -th.y);
	if (th.z >= 0.0) IncThrusterGroupLevel (THGROUP_ATT_BANKRIGHT,  th.z);
	else             IncThrusterGroupLevel (THGROUP_ATT_BANKLEFT,  -th.z);
}

void VESSEL::SetAttitudeRotLevel (int axis, double th) const
{
	switch (axis) {
	case 0: vessel->SetAttitudeRotX (th); break;
	case 1: vessel->SetAttitudeRotY (th); break;
	case 2: vessel->SetAttitudeRotZ (th); break;
	}
}

void VESSEL::SetAttitudeLinLevel (int axis, double th) const
{
	switch (axis) {
	case 0: vessel->SetAttitudeLinX (th); break;
	case 1: vessel->SetAttitudeLinY (th); break;
	case 2: vessel->SetAttitudeLinZ (th); break;
	}
}

void VESSEL::SetAttitudeLinLevel (const VECTOR3 &th) const
{
	vessel->SetAttitudeLinX (th.x);
	vessel->SetAttitudeLinY (th.y);
	vessel->SetAttitudeLinZ (th.z);
}

bool VESSEL::ActivateNavmode (int mode)
{
	return vessel->SetNavMode (mode);
}

bool VESSEL::DeactivateNavmode (int mode)
{
	return vessel->ClrNavMode (mode);
}

bool VESSEL::ToggleNavmode (int mode)
{
	return vessel->TglNavMode (mode);
}

bool VESSEL::GetNavmodeState (int mode)
{
	return vessel->NavModeActive (mode);
}

bool VESSEL::GetHoverHoldAltitude (double &alt, bool &terrainalt)
{
	bool active = vessel->NavModeActive (NAVMODE_HOLDALT);
	if (active) {
		alt = vessel->hoverhold.alt;
		terrainalt = vessel->hoverhold.terrain;
	}
	return active;
}

void VESSEL::SetHoverHoldAltitude (double alt, bool terrainalt)
{
	vessel->SetHoverHoldAltitude (alt, terrainalt);
}

void VESSEL::SetCOG_elev (double cog) const
{
	vessel->cog_elev = cog;
}

void VESSEL::SetCrossSections (const VECTOR3 &cs) const
{
	vessel->cs.Set (cs.x, cs.y, cs.z);
	vessel->vd_forw = cs.z * 0.5*vessel->CWz[0];
	vessel->vd_back = cs.z * 0.5*vessel->CWz[1];
	vessel->vd_vert = cs.y * 0.5*vessel->CWy;
	vessel->vd_side = cs.x * 0.5*vessel->CWx;
}

void VESSEL::SetCW (double cw_z_pos, double cw_z_neg, double cw_x, double cw_y) const
{
	vessel->CWz[0] = cw_z_pos;
	vessel->CWz[1] = cw_z_neg;
	vessel->CWx    = cw_x;
	vessel->CWy    = cw_y;
	vessel->bCWexplicit = true;

	vessel->vd_forw = vessel->cs.z * 0.5*vessel->CWz[0];
	vessel->vd_back = vessel->cs.z * 0.5*vessel->CWz[1];
	vessel->vd_vert = vessel->cs.y * 0.5*vessel->CWy;
	vessel->vd_side = vessel->cs.x * 0.5*vessel->CWx;
}

void VESSEL::SetWingAspect (double aspect) const
{
	vessel->wingaspect = aspect;
	vessel->wingfactor = aspect * vessel->wingeff;
}

void VESSEL::SetWingEffectiveness (double eff) const
{
	vessel->wingeff = eff;
	vessel->wingfactor = vessel->wingaspect * eff;
}

void VESSEL::SetRotDrag (const VECTOR3 &rd) const
{
	vessel->rdrag.Set (rd.x, rd.y, rd.z);
}

double VESSEL::GetPitchMomentScale () const
{
	return vessel->pitch_moment_scale;
}

void VESSEL::SetPitchMomentScale (double scale) const
{
	vessel->pitch_moment_scale = scale;
}

double VESSEL::GetYawMomentScale () const
{
	return vessel->bank_moment_scale;
}

void VESSEL::SetYawMomentScale (double scale) const
{
	vessel->bank_moment_scale = scale;
}

double VESSEL::GetBankMomentScale () const
{
	LOGOUT_OBSOLETE;
	return vessel->bank_moment_scale;
}

void VESSEL::SetBankMomentScale (double scale) const
{
	LOGOUT_OBSOLETE;
	vessel->bank_moment_scale = scale;
}

void VESSEL::SetPMI (const VECTOR3 &pmi) const
{
	vessel->pmi.Set (pmi.x, pmi.y, pmi.z);
}

void VESSEL::SetAlbedoRGB (const VECTOR3 &albedo) const
{
	vessel->albedo.Set(albedo.x, albedo.y, albedo.z);
}

double VESSEL::GetTrimScale () const
{
	return vessel->trim_scale;
}

void VESSEL::SetTrimScale (double scale) const
{
	vessel->trim_scale = scale;
	vessel->bElevTrim = (scale > 0);
}

void VESSEL::SetCameraOffset (const VECTOR3 &co) const
{
	vessel->campos.Set (co.x, co.y, co.z);
}





void VESSEL::SetCameraRotationRange (double left, double right, double up, double down) const
{
	vessel->camdp_left = left;
	vessel->camdp_right = right;
	vessel->camdt_up = up;
	vessel->camdt_down = down;
}



void VESSEL::SetCameraShiftRange (const VECTOR3 &forward, const VECTOR3 &left, const VECTOR3 &right) const
{
	vessel->SetCameraShiftRange (forward, left, right);
}

void VESSEL::SetCameraMovement (const VECTOR3 &fwdpos, double fwdphi, double fwdtht,
	const VECTOR3 &lpos, double lphi, double ltht,
	const VECTOR3 &rpos, double rphi, double rtht) const
{
	vessel->SetCameraMovement (fwdpos, fwdphi, fwdtht, lpos, lphi, ltht, rpos, rphi, rtht);
}





void VESSEL::SetLiftCoeffFunc (LiftCoeffFunc lcf) const
{
	vessel->LiftCoeff = lcf;
}

DOCKHANDLE VESSEL::CreateDock (const VECTOR3 &pos, const VECTOR3 &dir, const VECTOR3 &rot) const
{
	return (DOCKHANDLE)vessel->CreateDock (MakeVector (pos), MakeVector (dir), MakeVector (rot));
}

bool VESSEL::DelDock (DOCKHANDLE hDock) const
{
	return vessel->DelDock ((PortSpec*)hDock);
}

void VESSEL::ClearDockDefinitions () const
{
	vessel->ClearDockDefinitions();
}

void VESSEL::SetDockParams (const VECTOR3 &pos, const VECTOR3 &dir, const VECTOR3 &rot) const
{
	if (!vessel->ndock)
		vessel->CreateDock (MakeVector (pos), MakeVector (dir), MakeVector (rot));
	else
		vessel->SetDockParams (vessel->dock[0], MakeVector (pos), MakeVector (dir), MakeVector (rot));
}

void VESSEL::SetDockParams (DOCKHANDLE dock, const VECTOR3 &pos, const VECTOR3 &dir, const VECTOR3 &rot) const
{
	vessel->SetDockParams ((PortSpec*)dock, MakeVector (pos), MakeVector (dir), MakeVector (rot));
}

void VESSEL::GetDockParams (DOCKHANDLE dock, VECTOR3 &pos, VECTOR3 &dir, VECTOR3 &rot) const
{
	PortSpec *ps = (PortSpec*)dock;
	pos.x = ps->ref.x, pos.y = ps->ref.y, pos.z = ps->ref.z;
	dir.x = ps->dir.x, dir.y = ps->dir.y, dir.z = ps->dir.z;
	rot.x = ps->rot.x, rot.y = ps->rot.y, rot.z = ps->rot.z;
}

oapi::UInt VESSEL::DockCount () const
{
	return vessel->ndock;
}

DOCKHANDLE VESSEL::GetDockHandle (oapi::UInt n) const
{
	return (DOCKHANDLE)(n < vessel->ndock ? vessel->GetDockParams(n) : 0);
}

OBJHANDLE VESSEL::GetDockStatus (DOCKHANDLE dock) const
{
	return (OBJHANDLE)((PortSpec*)dock)->mate;
}

oapi::UInt VESSEL::DockingStatus (oapi::UInt port) const
{
	if (port >= vessel->ndock) return 0;
	return (vessel->GetDockParams(port)->mate ? 1 : 0);
}

void VESSEL::MoveDock(DOCKHANDLE hDock, const VECTOR3& pos, const VECTOR3& dir, const VECTOR3& rot)
{
	vessel->MoveDock((PortSpec*)hDock, MakeVector(pos), MakeVector(dir), MakeVector(rot));
}

DOCKHANDLE VESSEL::GetProxyDock(DOCKHANDLE hDock) const
{
	return (DOCKHANDLE)vessel->GetProxyDock((PortSpec*)hDock);
}

int VESSEL::GetDockIndex(DOCKHANDLE hDock) const
{
	for (int i = 0; i < vessel->ndock; i++) if (vessel->dock[i] == hDock) return i;
	return -1;
}

bool VESSEL::GetTargetDockAlignment(DOCKHANDLE pD, DOCKHANDLE pT, VECTOR3* ofs, VECTOR3* dir, VECTOR3* rot, VECTOR3* vel) const
{
	Vector o, d, r, v;
	Vector* op = ofs ? &o : nullptr; Vector* dp = dir ? &d : nullptr;
	Vector* rp = rot ? &r : nullptr; Vector* vp = vel ? &v : nullptr;
	if (vessel->GetTargetDockAlignment((PortSpec*)pD, (PortSpec*)pT, op, dp, rp, vp)) {
		if (ofs) { ofs->x = o.x; ofs->y = o.y; ofs->z = o.z; }
		if (dir) { dir->x = d.x; dir->y = d.y; dir->z = d.z; }
		if (rot) { rot->x = r.x; rot->y = r.y; rot->z = r.z; }
		if (vel) { vel->x = v.x; vel->y = v.y; vel->z = v.z; }
		return true;
	}
	return false;
}

int VESSEL::Dock (OBJHANDLE target, oapi::UInt n, oapi::UInt tgtn, oapi::UInt mode) const
{
	return vessel->Dock ((Vessel*)target, n, tgtn, mode);
}

int VESSEL::Dock(DOCKHANDLE hSrc, DOCKHANDLE hTgt, oapi::UInt32 mode) const
{
	Vessel* pS = ((PortSpec*)hSrc)->owner;
	Vessel* pT = ((PortSpec*)hTgt)->owner;
	int n = -1, t = -1;
	for (int i = 0; i < pS->ndock; i++) if (pS->dock[i] == ((PortSpec*)hSrc)) { n = i; break; }
	for (int i = 0; i < pT->ndock; i++) if (pT->dock[i] == ((PortSpec*)hTgt)) { t = i; break; }
	if (n >= 0 && t >= 0) return vessel->Dock(pT, n, t, mode);
	return -4;
}

bool VESSEL::Undock (oapi::UInt n, const OBJHANDLE exclude) const
{
	return vessel->Undock (n, (Vessel*)exclude);
}

void VESSEL::SetDockMode (int mode) const
{
	vessel->SetDockMode (mode);
}

ATTACHMENTHANDLE VESSEL::CreateAttachment (bool toparent, const VECTOR3 &pos, const VECTOR3 &dir, const VECTOR3 &rot, const char *id, bool loose) const
{
	return (ATTACHMENTHANDLE)vessel->CreateAttachment (toparent, MakeVector (pos), MakeVector (dir), MakeVector (rot), id, loose);
}

bool VESSEL::DelAttachment (ATTACHMENTHANDLE attachment) const
{
	return vessel->DelAttachment ((AttachmentSpec*)attachment);
}

void VESSEL::ClearAttachments () const
{
	vessel->ClearAttachments();
}

void VESSEL::SetAttachmentParams (ATTACHMENTHANDLE attachment, const VECTOR3 &pos, const VECTOR3 &dir, const VECTOR3 &rot) const
{
	vessel->SetAttachmentParams ((AttachmentSpec*)attachment, MakeVector (pos), MakeVector (dir), MakeVector (rot));
}

void VESSEL::GetAttachmentParams (ATTACHMENTHANDLE attachment, VECTOR3 &pos, VECTOR3 &dir, VECTOR3 &rot) const
{
	AttachmentSpec *as = (AttachmentSpec*)attachment;
	pos.x = as->ref.x, pos.y = as->ref.y, pos.z = as->ref.z;
	dir.x = as->dir.x, dir.y = as->dir.y, dir.z = as->dir.z;
	rot.x = as->rot.x, rot.y = as->rot.y, rot.z = as->rot.z;
}

const char *VESSEL::GetAttachmentId (ATTACHMENTHANDLE attachment) const
{
	return ((AttachmentSpec*)attachment)->id;
}

OBJHANDLE VESSEL::GetAttachmentStatus (ATTACHMENTHANDLE attachment) const
{
	return (OBJHANDLE)((AttachmentSpec*)attachment)->mate;
}

bool VESSEL::AttachChild (OBJHANDLE child, ATTACHMENTHANDLE attachment, ATTACHMENTHANDLE child_attachment) const
{
	return vessel->AttachChild ((Vessel*)child, (AttachmentSpec*)attachment, (AttachmentSpec*)child_attachment);
}

bool VESSEL::DetachChild (ATTACHMENTHANDLE attachment, double vel) const
{
	return vessel->DetachChild ((AttachmentSpec*)attachment, vel);
}

oapi::UInt32 VESSEL::AttachmentCount (bool toparent) const
{
	return (toparent ? vessel->npattach : vessel->ncattach);
}

oapi::UInt32 VESSEL::GetAttachmentIndex (ATTACHMENTHANDLE attachment) const
{
	return vessel->GetAttachmentIndex ((AttachmentSpec*)attachment);
}

ATTACHMENTHANDLE VESSEL::GetAttachmentHandle (bool toparent, oapi::UInt32 i) const
{
	if (toparent) {
		return (i < vessel->npattach ? (ATTACHMENTHANDLE)vessel->pattach[i] : 0);
	} else {
		return (i < vessel->ncattach ? (ATTACHMENTHANDLE)vessel->cattach[i] : 0);
	}
}

void VESSEL::AddBeacon (BEACONLIGHTSPEC *bs)
{
	vessel->AddBeacon (bs);
}

bool VESSEL::DelBeacon (BEACONLIGHTSPEC *bs)
{
	return vessel->DelBeacon (bs);
}

void VESSEL::ClearBeacons ()
{
	vessel->ClearBeacons ();
}

const BEACONLIGHTSPEC *VESSEL::GetBeacon (oapi::UInt32 idx) const
{
	return vessel->GetBeacon (idx);
}

LightEmitter *VESSEL::AddPointLight (const VECTOR3 &pos, double range, double att0, double att1, double att2, COLOUR4 diffuse, COLOUR4 specular, COLOUR4 ambient) const
{
	return vessel->AddPointLight (pos, range, att0, att1, att2, diffuse, specular, ambient);
}

LightEmitter *VESSEL::AddSpotLight (const VECTOR3 &pos, const VECTOR3 &dir, double range, double att0, double att1, double att2, double umbra, double penumbra, COLOUR4 diffuse, COLOUR4 specular, COLOUR4 ambient) const
{
	return vessel->AddSpotLight (pos, dir, range, att0, att1, att2, umbra, penumbra, diffuse, specular, ambient);
}

oapi::UInt32 VESSEL::LightEmitterCount () const
{
	return vessel->LightEmitterCount();
}

const LightEmitter *VESSEL::GetLightEmitter (oapi::UInt32 i) const
{
	return (i < vessel->LightEmitterCount() ? vessel->GetLightEmitter(i) : NULL);
}

bool VESSEL::DelLightEmitter (LightEmitter *le) const
{
	return vessel->DelLightEmitter (le);
}

void VESSEL::ClearLightEmitters () const
{
	vessel->ClearLightEmitters();
}

bool VESSEL::GetSuperstructureCG (VECTOR3 &cg) const
{
	Vector vcg;
	bool ok = vessel->GetSuperStructCG (vcg);
	cg.x = vcg.x;
	cg.y = vcg.y;
	cg.z = vcg.z;
	return ok;
}

void VESSEL::SetTouchdownPoints (const VECTOR3 &pt1, const VECTOR3 &pt2, const VECTOR3 &pt3) const
{
	TOUCHDOWNVTX tdvtx[3];
	tdvtx[0].pos = pt1;
	tdvtx[1].pos = pt2;
	tdvtx[2].pos = pt3;
	for (oapi::UInt32 i = 0; i < 3; i++) {
		tdvtx[i].stiffness = (vessel->emass == 1e3 ? 1e6 : vessel->emass*20.0);
		tdvtx[i].damping   = tdvtx[i].stiffness*0.1;
		tdvtx[i].mu        = vessel->mu;
		tdvtx[i].mu_lng    = vessel->mu_lng;
	}
	vessel->SetTouchdownPoints (tdvtx, 3);
}

void VESSEL::SetTouchdownPoints (const TOUCHDOWNVTX *tdvtx, oapi::UInt32 ntdvtx) const
{
	GetVesselServices().Check(bool(ntdvtx >= 3), "VESSEL::SetTouchdownPoints: at least 3 points must be provided");
	vessel->SetTouchdownPoints (tdvtx, ntdvtx);
}

void VESSEL::GetTouchdownPoints (VECTOR3 &pt1, VECTOR3 &pt2, VECTOR3 &pt3) const
{
	CopyVector (vessel->touchdown_vtx[0].pos, pt1);
	CopyVector (vessel->touchdown_vtx[1].pos, pt2);
	CopyVector (vessel->touchdown_vtx[2].pos, pt3);
}

bool VESSEL::GetTouchdownPoint (TOUCHDOWNVTX &tdvtx, oapi::UInt32 idx) const
{
	if (idx < vessel->ntouchdown_vtx) {
		memcpy(&tdvtx, vessel->touchdown_vtx+idx, sizeof(TOUCHDOWNVTX));
		return true;
	} else return false;
}

oapi::UInt32 VESSEL::GetTouchdownPointCount () const
{
	return vessel->ntouchdown_vtx;
}

void VESSEL::DefSetState (const VESSELSTATUS *status) const
{
	vessel->SetState (*status);
}

void VESSEL::DefSetStateEx (const void *status) const
{
	vessel->SetStateEx (status);
}

void VESSEL::ParseScenarioLine (char *line, VESSELSTATUS *status) const
{
	vessel->ParseScenarioLine (line, *status);
}

void VESSEL::ParseScenarioLineEx (char *line, void *status) const
{
	vessel->ParseScenarioLineEx (line, status);
}

void VESSEL::ClearMeshes () const
{
	vessel->ClearMeshes (true);
}

void VESSEL::ClearMeshes (bool retain_anim) const
{
	vessel->ClearMeshes (retain_anim);
}

oapi::UInt VESSEL::AddMesh (const char *meshname, const VECTOR3 *ofs) const
{
	if (ofs) {
		return vessel->AddMesh (meshname, ofs);
	} else
		return vessel->AddMesh (meshname);
}

oapi::UInt VESSEL::AddMesh (MESHHANDLE hMesh, const VECTOR3 *ofs) const
{
	if (ofs) {
		return vessel->AddMesh (hMesh, ofs);
	} else
		return vessel->AddMesh (hMesh);
}

oapi::UInt VESSEL::InsertMesh (const char *meshname, oapi::UInt idx, const VECTOR3 *ofs) const
{
	if (ofs) {
		return vessel->InsertMesh (meshname, idx, ofs);
	} else
		return vessel->InsertMesh (meshname, idx);
}

oapi::UInt VESSEL::InsertMesh (MESHHANDLE hMesh, oapi::UInt idx, const VECTOR3 *ofs) const
{
	if (ofs) {
		return vessel->InsertMesh (hMesh, idx, ofs);
	} else
		return vessel->InsertMesh (hMesh, idx);
}

bool VESSEL::DelMesh (oapi::UInt idx, bool retain_anim) const
{
	return vessel->DelMesh (idx, retain_anim);
}

bool VESSEL::ShiftMesh (oapi::UInt idx, const VECTOR3 &ofs) const
{
	return vessel->ShiftMesh (idx, ofs);
}

void VESSEL::ShiftMeshes (const VECTOR3 &ofs) const
{
	for (oapi::UInt i = 0; i < vessel->nmesh; i++)
		vessel->ShiftMesh (i, ofs);
}

bool VESSEL::GetMeshOffset (oapi::UInt idx, VECTOR3 &ofs) const
{
	if (idx >= vessel->nmesh || !vessel->meshlist[idx]) return false;
	memcpy (&ofs, &vessel->meshlist[idx]->meshofs, sizeof(VECTOR3));
	return true;
}

oapi::UInt VESSEL::GetMeshCount () const
{
	return vessel->nmesh;
}

MESHHANDLE VESSEL::GetMesh (VISHANDLE vis, oapi::UInt idx) const
{
	return NULL;
}



const MESHHANDLE VESSEL::GetMeshTemplate (oapi::UInt idx) const
{
	return vessel->GetMeshTemplate (idx);
}

const char *VESSEL::GetMeshName (oapi::UInt idx) const
{
	return vessel->GetMeshName (idx);
}

MESHHANDLE VESSEL::CopyMeshFromTemplate (oapi::UInt idx) const
{
	return (MESHHANDLE)vessel->CopyMeshFromTemplate (idx);
}

oapi::UInt16 VESSEL::GetMeshVisibilityMode (oapi::UInt idx) const
{
	return (idx < vessel->nmesh && vessel->meshlist[idx] ? vessel->meshlist[idx]->vismode : 0);
}

void VESSEL::SetMeshVisibilityMode (oapi::UInt idx, oapi::UInt16 mode) const
{
	vessel->SetMeshVisibilityMode (idx, mode);
}

void VESSEL::SetMeshVisibleInternal (oapi::UInt idx, bool visible) const
{
	vessel->SetMeshVisibilityMode (idx, visible ? MESHVIS_ALWAYS : MESHVIS_EXTERNAL);
}

int VESSEL::MeshModified (MESHHANDLE hMesh, oapi::UInt grp, oapi::UInt32 modflag)
{
	return vessel->MeshModified (hMesh, grp, modflag);
}

oapi::UInt VESSEL::AddExhaustRef (EXHAUSTTYPE exh, VECTOR3 &pos, double lscale, double wscale, VECTOR3 *dir) const
{
	ThrustSpec *th;
	oapi::UInt iexh = (oapi::UInt)exh;

	switch (exh) {
	case EXHAUST_MAIN:
		if (!vessel->m_thrusterGroupDef[THGROUP_MAIN].ts.size()) return 0; // not defined
		th = vessel->m_thrusterGroupDef[THGROUP_MAIN].ts[0];
		break;
	case EXHAUST_RETRO:
		if (!vessel->m_thrusterGroupDef[THGROUP_RETRO].ts.size()) return 0; // not defined
		th = vessel->m_thrusterGroupDef[THGROUP_RETRO].ts[0];
		break;
	case EXHAUST_HOVER:
		if (!vessel->m_thrusterGroupDef[THGROUP_HOVER].ts.size()) return 0; // not defined
		th = vessel->m_thrusterGroupDef[THGROUP_HOVER].ts[0];
		break;
	default: return 0;
	}
	//VECTOR3 p = {pos.x, pos.y, pos.z};
	//Vector d = -(dir ? Vector(dir->x, dir->y, dir->z) : DefExhaustDir[iexh]);

	EXHAUSTSPEC es = {(THRUSTER_HANDLE)th, NULL, &pos, dir ? dir : DefExhaustDir+iexh, lscale, wscale, 0, 0, NULL, EXHAUST_CONSTANTPOS|EXHAUST_CONSTANTDIR};
	return vessel->AddExhaust (&es);
	//return vessel->AddExhaust (th, lscale, wscale, 0, &p, &d);
}

void VESSEL::DelExhaustRef (EXHAUSTTYPE exh, oapi::UInt16 id) const
{
#ifdef UNDEF
	oapi::UInt i, j, iexh = (oapi::UInt)exh;
	oapi::UInt &neng = vessel->neng[iexh];
	ExhaustSpec *spec = vessel->eng_spec[iexh];
	for (i = 0; i < neng; i++) {
		if (spec[i].id == id) {
			for (j = i+1; j < neng; j++)
				spec[j-1] = spec[j];
			neng--;
			return;
		}
	}
	MessageBeep (-1); // should not get here!
#endif
}

void VESSEL::ClearExhaustRefs (void) const
{
	vessel->ClearExhaustDefinitions();
}

void VESSEL::SetExhaustScales (EXHAUSTTYPE exh, oapi::UInt16 id, double lscale, double wscale) const
{
#ifdef UNDEF
	int i, iexh = (int)exh;
	int neng = vessel->neng[iexh];
	ExhaustSpec *spec = vessel->eng_spec[iexh];
	for (i = 0; i < neng; i++) {
		if (spec[i].id == id) {
			spec[i].lscale = lscale;
			spec[i].wscale = wscale;
			return;
		}
	}
#endif
}

void VESSEL::SetReentryTexture (SURFHANDLE tex, double plimit, double lscale, double wscale) const
{
	vessel->reentry.plimit = (float)plimit;
	vessel->reentry.lscale = (float)lscale;
	vessel->reentry.wscale = (float)wscale;
	vessel->reentry.tex = tex;
	vessel->reentry.do_render = (tex != NULL);
}

oapi::UInt VESSEL::AddAttExhaustRef (const VECTOR3 &pos, const VECTOR3 &dir, double wscale, double lscale) const
{
	oapi::UInt32 n = vessel->noexhaust;
	OldExhaustSpec **tmp = new OldExhaustSpec*[n+1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	if (n) {
		memcpy (tmp, vessel->oexhaust, n*sizeof(OldExhaustSpec*));
		delete []vessel->oexhaust;
		vessel->oexhaust = NULL;
	}
	tmp[n] = new OldExhaustSpec; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	tmp[n]->ref = MakeVector(pos);
	tmp[n]->dir = -MakeVector(dir);
	tmp[n]->lscale = 3.0*lscale;
	tmp[n]->wscale = 0.387*wscale;
	vessel->oexhaust = tmp;
	return vessel->noexhaust++;
}

void VESSEL::AddAttExhaustMode (oapi::UInt idx, ATTITUDEMODE mode, int axis, int dir) const
{
	ThrustGroupSpec *tgs;
	switch (mode) {
	case ATTMODE_ROT:
		switch (axis) {
		case 0:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_PITCHDOWN : THGROUP_ATT_PITCHUP];
			break;
		case 1:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_YAWRIGHT : THGROUP_ATT_YAWLEFT];
			break;
		case 2:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_BANKLEFT : THGROUP_ATT_BANKRIGHT];
			break;
		}
		break;
	case ATTMODE_LIN:
		switch (axis) {
		case 0:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_LEFT : THGROUP_ATT_RIGHT];
			break;
		case 1:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_DOWN : THGROUP_ATT_UP];
			break;
		case 2:
			tgs = &vessel->m_thrusterGroupDef[dir ? THGROUP_ATT_BACK : THGROUP_ATT_FORWARD];
			break;
		}
		break;
	}
	if (idx >= vessel->noexhaust) return;
	OldExhaustSpec *oes = vessel->oexhaust[idx];
	if (tgs->ts.size()) {
		VECTOR3 ref = {oes->ref.x, oes->ref.y, oes->ref.z};
		VECTOR3 dir = {oes->dir.x, oes->dir.y, oes->dir.z};
		EXHAUSTSPEC es = {(THRUSTER_HANDLE)tgs->ts[0], NULL, &ref, &dir, oes->lscale, oes->wscale, 0, 0, NULL, EXHAUST_CONSTANTPOS|EXHAUST_CONSTANTDIR};
		vessel->AddExhaust (&es);
		//vessel->AddExhaust (tgs->ts[0], oes->lscale, oes->wscale, 0, &oes->ref, &oes->dir, 0);
	}
}

void VESSEL::ClearAttExhaustRefs (void) const
{
#ifdef UNDEF
	vessel->ClearAttExhaustRefs();
#endif
}

void VESSEL::ShiftCentreOfMass (const VECTOR3 &shift)
{
	if (vessel->bFRrecord) vessel->FRecorder_Save (true);
	Vector dr (shift.x, shift.y, shift.z);
	Vector gdr (mul (vessel->GRot(), dr));
	vessel->FlushRPos ();
	if (!vessel->bFRplayback) {  // ignore during playback
		vessel->AddRPos (gdr);
		if (vessel->supervessel) vessel->supervessel->NotifyShiftVesselOrigin (vessel, dr);
	}
	GetVesselServices().NotifyJump (*vessel, gdr);
	if (vessel->bFRrecord) vessel->FRecorder_Save (true);
}

void VESSEL::ShiftCG (const VECTOR3 &shift)
{
	VECTOR3 nshift = -shift;
	Vector vs = MakeVector (nshift);
	ShiftMeshes (nshift);
	vessel->ShiftThrusters (vs);
	vessel->ShiftAttachments (vs);
	vessel->ShiftDocks (vs);
	vessel->ShiftLightEmitters (nshift);
	vessel->campos.Set (vessel->campos+vs);
	// only shift the vc of this vessel
	GetVesselServices().ShiftCockpit (*vessel, vs);
	ShiftCentreOfMass (shift);
}

void VESSEL::GetRotationMatrix (MATRIX3 &R) const
{
	memcpy (R.data, vessel->s0->R.data, 9*sizeof(double));
}

void VESSEL::SetRotationMatrix (const MATRIX3 &R) const
{
	Matrix r;
	memcpy (r.data, R.data, 9*sizeof(double));
	vessel->SetRotationMatrix (r);
}

void VESSEL::GlobalRot (const VECTOR3 &rloc, VECTOR3 &rglob) const
{
	Vector loc(rloc.x, rloc.y, rloc.z);
	Vector glob (mul (vessel->GRot(), loc));
	rglob.x = glob.x;
	rglob.y = glob.y;
	rglob.z = glob.z;
}

void VESSEL::HorizonRot (const VECTOR3 &rloc, VECTOR3 &rhorizon) const
{
	if (!vessel->proxyplanet) return;
	Vector h (mul (vessel->sp.L2H, tmul (vessel->proxyplanet->GRot(), mul (vessel->GRot(), MakeVector(rloc)))));
	rhorizon = _V(h.x, h.y, h.z);
}

void VESSEL::HorizonInvRot (const VECTOR3 &rhorizon, VECTOR3 &rloc) const
{
	if (!vessel->proxyplanet) return;
	Vector r (tmul (vessel->GRot(), mul (vessel->proxyplanet->GRot(), tmul (vessel->sp.L2H, MakeVector (rhorizon)))));
	rloc = _V(r.x, r.y, r.z);
}

void VESSEL::Local2Global (const VECTOR3 &local, VECTOR3 &global) const
{
	Vector loc(local.x, local.y, local.z);
	Vector glob (mul (vessel->GRot(), loc) + vessel->GPos());
	global.x = glob.x;
	global.y = glob.y;
	global.z = glob.z;
}

void VESSEL::Global2Local (const VECTOR3 &global, VECTOR3 &local) const
{
	Vector glob(global.x, global.y, global.z);
	Vector loc (tmul (vessel->GRot(), glob - vessel->GPos()));
	local.x = loc.x;
	local.y = loc.y;
	local.z = loc.z;
}

void VESSEL::Local2Rel (const VECTOR3 &local, VECTOR3 &rel) const
{
	Vector loc(local.x, local.y, local.z);
	Vector r (mul (vessel->GRot(), loc) + vessel->GPos() - vessel->cbody->GPos());
	rel.x = r.x;
	rel.y = r.y;
	rel.z = r.z;
}

void VESSEL::RegisterAnimation (void) const
{
	vessel->animcount++;
}

void VESSEL::UnregisterAnimation (void) const
{
	if (vessel->animcount > 0)
		vessel->animcount--;
}

oapi::UInt VESSEL::RegisterAnimSequence (double defmeshstate) const
{
	return vessel->AddAnimSeq (defmeshstate);
}

bool VESSEL::AddAnimComp (oapi::UInt seq, ANIMCOMP *comp)
{
	return vessel->AddAnimSeqComp (seq, comp);
}

bool VESSEL::SetAnimState (oapi::UInt seq, double state)
{
	return vessel->SetAnimState (seq, state);
}

oapi::UInt VESSEL::CreateAnimation (double initial_state) const
{
	return vessel->CreateAnimation (initial_state);
}

bool VESSEL::DelAnimation (oapi::UInt anim) const
{
	return vessel->DelAnimation (anim);
}

ANIMATIONCOMPONENT_HANDLE VESSEL::AddAnimationComponent (oapi::UInt anim, double state0, double state1, MGROUP_TRANSFORM *trans, ANIMATIONCOMPONENT_HANDLE parent) const
{
	return (ANIMATIONCOMPONENT_HANDLE)vessel->AddAnimationComponent (anim, state0, state1, trans, (ANIMATIONCOMP*)parent);
}

bool VESSEL::DelAnimationComponent (oapi::UInt anim, ANIMATIONCOMPONENT_HANDLE hAC)
{
	return vessel->DelAnimationComponent (anim, (ANIMATIONCOMP*)hAC);
}

bool VESSEL::SetAnimation (oapi::UInt anim, double state) const
{
	return vessel->SetAnimation (anim, state);
}

double VESSEL::GetAnimation (oapi::UInt anim) const
{
	return vessel->GetAnimation (anim);
}

oapi::UInt VESSEL::GetAnimPtr (ANIMATION **anim) const
{
	*anim = vessel->anim;
	return vessel->nanim;
}

SUPERVESSELHANDLE VESSEL::GetSupervessel () const
{
	return (SUPERVESSELHANDLE)vessel->supervessel;
}

VECTOR3 VESSEL::GetSupervesselCG () const
{
	VECTOR3 cg = _V(0,0,0);
	if (vessel->supervessel) {
		Vector vcg;
		if (vessel->supervessel->GetCG (vessel, vcg))
			cg = MakeVECTOR3 (vcg);
	}
	return cg;
}

bool VESSEL::Recording (void) const
{
	return vessel->bFRrecord;
}

bool VESSEL::Playback (void) const
{
	return vessel->bFRplayback;
}

void VESSEL::RecordEvent (const char *event_type, const char *event) const
{
	if (vessel->bFRrecord) vessel->FRecorder_SaveEvent (event_type, event);
}

void VESSEL::SaveDefaultState (FILEHANDLE scn) const
{
	vessel->WriteDefault (*(ostream*)scn);
}

void VESSEL::AddForce (const VECTOR3 &F, const VECTOR3 &r) const
{
	vessel->AddForce (MakeVector(F), MakeVector(r));
}

bool VESSEL::GetCollisionDebugData (VECTOR3 &contactPt, VECTOR3 &normal, VECTOR3 &impulseDir, VECTOR3 &leverArm, double &depth, double &impulseMag) const
{
	if (GetRigidBodyServices().Time().SimT1 >= vessel->m_colDebug.showTime && !vessel->m_colDebug.active) return false;

	contactPt = vessel->m_colDebug.contactPt;
	normal = vessel->m_colDebug.normal;
	impulseDir = vessel->m_colDebug.impulseDir;
	leverArm = vessel->m_colDebug.leverArm;
	depth = vessel->m_colDebug.depth;
	impulseMag = vessel->m_colDebug.impulseMag;
	return true;
}

const VECTOR3 *VESSEL::GetCollisionPointCloud (oapi::UInt32 &nPts) const
{
	vessel->RebuildHullCache();
	vessel->ApplyAnimationToHullCache();
	if (vessel->m_hullCache.empty()) {
		nPts = 0;
		return NULL;
	}
	nPts = (oapi::UInt32)vessel->m_hullCache.size();
	return &(vessel->m_hullCache[0]);
}

const oapi::UInt16 *VESSEL::GetCollisionHullIndices (oapi::UInt32 &nIdx) const
{
	vessel->RebuildHullCache();
	vessel->ApplyAnimationToHullCache();
	if (!vessel->m_hullVisualValid) vessel->RebuildConvexHullVisual();
	if (vessel->m_convexHullIdx.empty()) {
		nIdx = 0;
		return NULL;
	}
	nIdx = (oapi::UInt32)vessel->m_convexHullIdx.size();
	return &(vessel->m_convexHullIdx[0]);
}

const VECTOR3 *VESSEL::GetCollisionClearZones (oapi::UInt32 &nBoxes) const
{
	vessel->RebuildHullCache();
	vessel->ApplyAnimationToHullCache();

	vessel->m_clearZoneCache.clear();
	for (const auto& slice : vessel->m_hullGroupSlices) {
		if (slice.isDockClearZone) {
			vessel->m_clearZoneCache.push_back({slice.minP.x, slice.minP.y, slice.minP.z});
			vessel->m_clearZoneCache.push_back({slice.maxP.x, slice.maxP.y, slice.maxP.z});
		}
	}

	if (vessel->m_clearZoneCache.empty()) {
		nBoxes = 0;
		return NULL;
	}

	nBoxes = (oapi::UInt32)(vessel->m_clearZoneCache.size() / 2);
	return &(vessel->m_clearZoneCache[0]);
}

bool VESSEL::IsConvexCollider () const
{
	return vessel->bIsConvexCollider;
}

PROPELLANT_HANDLE VESSEL::CreatePropellantResource (double maxmass, double mass, double efficiency) const
{
	return (PROPELLANT_HANDLE)vessel->CreatePropellantResource (maxmass, mass, efficiency);
}

void VESSEL::DelPropellantResource (PROPELLANT_HANDLE &ph) const
{
	vessel->DelPropellantResource ((TankSpec*)ph);
	ph = NULL;
}

void VESSEL::ClearPropellantResources () const
{
	vessel->ClearPropellantResources();
}

PROPELLANT_HANDLE VESSEL::GetPropellantHandleByIndex (oapi::UInt32 idx) const
{
	if (idx >= vessel->ntank) return 0;
	return (PROPELLANT_HANDLE) vessel->tank[idx];
}

oapi::UInt32 VESSEL::GetPropellantCount () const
{
	return vessel->ntank;
}

void VESSEL::SetDefaultPropellantResource (PROPELLANT_HANDLE ph) const
{
	vessel->SetDefaultPropellant ((TankSpec*)ph);
}

PROPELLANT_HANDLE VESSEL::GetDefaultPropellantResource () const
{
	return (PROPELLANT_HANDLE)vessel->DefaultPropellantHandle();
}

void VESSEL::SetPropellantMaxMass (PROPELLANT_HANDLE ph, double maxmass) const
{
	vessel->SetPropellantMaxMass ((TankSpec*)ph, maxmass);
}

void VESSEL::SetPropellantEfficiency (PROPELLANT_HANDLE ph, double efficiency) const
{
	((TankSpec*)ph)->efficiency = efficiency;
}

void VESSEL::SetPropellantMass (PROPELLANT_HANDLE ph, double mass) const
{
	((TankSpec*)ph)->mass = mass;
	vessel->UpdateMass ();
}

double VESSEL::GetPropellantMaxMass (PROPELLANT_HANDLE ph) const
{
	return ((TankSpec*)ph)->maxmass;
}

double VESSEL::GetPropellantEfficiency (PROPELLANT_HANDLE ph) const
{
	return ((TankSpec*)ph)->efficiency;
}

double VESSEL::GetPropellantMass (PROPELLANT_HANDLE ph) const
{
	return ((TankSpec*)ph)->mass;
}

double VESSEL::GetPropellantFlowrate (PROPELLANT_HANDLE ph) const
{
	return vessel->GetPropellantFlowrate ((TankSpec*)ph);
}

double VESSEL::GetTotalPropellantMass () const
{
	return vessel->fmass;
}

double VESSEL::GetTotalPropellantFlowrate () const
{
	return (vessel->pfmass-vessel->fmass)*GetRigidBodyServices().Time().iSimDT0;
}

THRUSTER_HANDLE VESSEL::CreateThruster (const VECTOR3 &pos, const VECTOR3 &dir, double maxth0,
	PROPELLANT_HANDLE hp, double isp0, double isp_ref, double p_ref) const
{
	return (THRUSTER_HANDLE)vessel->CreateThruster (MakeVector(pos), MakeVector(dir),
		maxth0, (TankSpec*)hp, isp0, isp_ref, p_ref);
}

bool VESSEL::DelThruster (THRUSTER_HANDLE &th) const
{
	bool ok = vessel->DelThruster ((ThrustSpec*)th);
	th = NULL;
	return ok;
}

void VESSEL::ClearThrusterDefinitions () const
{
	vessel->ClearThrusterDefinitions ();
}

THRUSTER_HANDLE VESSEL::GetThrusterHandleByIndex (oapi::UInt32 idx) const
{
	return (THRUSTER_HANDLE)(idx < vessel->m_thruster.size() ? vessel->m_thruster[idx] : nullptr);
}

oapi::UInt32 VESSEL::GetThrusterCount (void) const
{
	return (oapi::UInt32)vessel->m_thruster.size();
}

void VESSEL::SetThrusterRef (THRUSTER_HANDLE th, const VECTOR3 &pos) const
{
	((ThrustSpec*)th)->ref = pos;
}

void VESSEL::GetThrusterRef (THRUSTER_HANDLE th, VECTOR3 &pos) const
{
	pos.x = ((ThrustSpec*)th)->ref.x;
	pos.y = ((ThrustSpec*)th)->ref.y;
	pos.z = ((ThrustSpec*)th)->ref.z;
}

void VESSEL::SetThrusterDir (THRUSTER_HANDLE th, const VECTOR3 &dir) const
{
	((ThrustSpec*)th)->dir = dir;
}

void VESSEL::GetThrusterDir (THRUSTER_HANDLE th, VECTOR3 &dir) const
{
	dir.x = ((ThrustSpec*)th)->dir.x;
	dir.y = ((ThrustSpec*)th)->dir.y;
	dir.z = ((ThrustSpec*)th)->dir.z;
}

void VESSEL::SetThrusterMax0 (THRUSTER_HANDLE th, double maxth0) const
{
	vessel->SetThrusterMax0 ((ThrustSpec*)th, maxth0);
	//((ThrustSpec*)th)->maxth0 = maxth0;
}

double VESSEL::GetThrusterMax0 (THRUSTER_HANDLE th) const
{
	return ((ThrustSpec*)th)->maxth0;
}

double VESSEL::GetThrusterMax (THRUSTER_HANDLE th) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	return ts->maxth0 * vessel->ThrusterAtmScale (ts, vessel->sp.atmp);
}

double VESSEL::GetThrusterMax (THRUSTER_HANDLE th, double p_ref) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	return ts->maxth0 * vessel->ThrusterAtmScale (ts, p_ref);
}

void VESSEL::SetThrusterIsp (THRUSTER_HANDLE th, double isp) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->isp0 = isp;
	ts->pfac = 0.0;  // no pressure dependence
}

void VESSEL::SetThrusterIsp (THRUSTER_HANDLE th, double isp0, double isp_ref, double p_ref) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->isp0 = isp0;
	ts->pfac = (isp0-isp_ref)/(p_ref*isp0);
}

double VESSEL::GetThrusterIsp (THRUSTER_HANDLE th) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	return ts->isp0 * vessel->ThrusterAtmScale (ts, vessel->sp.atmp);
}

double VESSEL::GetThrusterIsp (THRUSTER_HANDLE th, double p_ref) const
{
	ThrustSpec *ts = (ThrustSpec*)th;
	return ts->isp0 * vessel->ThrusterAtmScale (ts, p_ref);
}

double VESSEL::GetThrusterIsp0 (THRUSTER_HANDLE th) const
{
	return ((ThrustSpec*)th)->isp0;
}

void VESSEL::SetThrusterResource (THRUSTER_HANDLE th, PROPELLANT_HANDLE ph) const
{
	((ThrustSpec*)th)->tank = (TankSpec*)ph;
	if (!ph) SetThrusterLevel (th, 0);
}

PROPELLANT_HANDLE VESSEL::GetThrusterResource (THRUSTER_HANDLE th) const
{
	return (PROPELLANT_HANDLE)((ThrustSpec*)th)->tank;
}

void VESSEL::SetThrusterLevel (THRUSTER_HANDLE th, double level) const
{
	if (vessel->bFRplayback) return;
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->level_permanent = level;
	if (ts->tank && ts->tank->mass)
		ts->level = min (1.0, ts->level_permanent + ts->level_override);
}

void VESSEL::IncThrusterLevel (THRUSTER_HANDLE th, double dlevel) const
{
	if (vessel->bFRplayback) return;
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->level_permanent += dlevel;
	ts->level_permanent = max (0.0, min (1.0, ts->level_permanent));
	if (ts->tank && ts->tank->mass)
		ts->level = max (0.0, min (1.0, ts->level_permanent + ts->level_override));
}

void VESSEL::SetThrusterLevel_SingleStep (THRUSTER_HANDLE th, double level) const
{
	if (vessel->bFRplayback) return;
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->level_override = ts->level = max (0.0, min (1.0, level));
}

void VESSEL::IncThrusterLevel_SingleStep (THRUSTER_HANDLE th, double dlevel) const
{
	if (vessel->bFRplayback) return;
	ThrustSpec *ts = (ThrustSpec*)th;
	ts->level_override += dlevel;
	if (ts->tank && ts->tank->mass)
		ts->level = min (1.0, ts->level_permanent + ts->level_override);
}

double VESSEL::GetThrusterLevel (THRUSTER_HANDLE th) const
{
	return ((ThrustSpec*)th)->level;
}

void VESSEL::GetThrusterMoment (THRUSTER_HANDLE th, VECTOR3 &F, VECTOR3 &T) const
{
	Vector f, t;
	vessel->GetThrusterMoment ((ThrustSpec*)th, f, t);
	F.x = f.x;
	F.y = f.y;
	F.z = f.z;
	T.x = t.x;
	T.y = t.y;
	T.z = t.z;
}

THGROUP_HANDLE VESSEL::CreateThrusterGroup (THRUSTER_HANDLE *th, int nth, THGROUP_TYPE thgt) const
{
	return (THGROUP_HANDLE)vessel->CreateThrusterGroup ((ThrustSpec**)th, nth, thgt);
}

// OBSOLETE
bool VESSEL::DelThrusterGroup (THGROUP_HANDLE &thg, THGROUP_TYPE thgt, bool delth) const
{
	if (thg != (THGROUP_HANDLE)vessel->GetThrusterGroup(thgt)) return false;
	return DelThrusterGroup(thg);
}

bool VESSEL::DelThrusterGroup (THGROUP_HANDLE thg, bool delth) const
{
	return vessel->DeleteThrusterGroup ((ThrustGroupSpec*)thg, delth);
}

bool VESSEL::DelThrusterGroup (THGROUP_TYPE thgt, bool delth) const
{
	return vessel->DeleteThrusterGroup (thgt, delth);
}

THGROUP_HANDLE VESSEL::GetThrusterGroupHandle (THGROUP_TYPE thgt) const
{
	ThrustGroupSpec* tgs = vessel->GetThrusterGroup(thgt);
	return (THGROUP_HANDLE)tgs;
}

THGROUP_HANDLE VESSEL::GetUserThrusterGroupHandleByIndex (oapi::UInt32 idx) const
{
	if (idx >= vessel->m_thrusterGroupUsr.size()) return 0;
	return (THGROUP_HANDLE)vessel->m_thrusterGroupUsr[idx];
}

oapi::UInt32 VESSEL::GetGroupThrusterCount (THGROUP_HANDLE thg) const
{
	return ((ThrustGroupSpec*)thg)->ts.size();
}

oapi::UInt32 VESSEL::GetGroupThrusterCount (THGROUP_TYPE thgt) const
{
	const ThrustGroupSpec* tgs = vessel->GetThrusterGroup(thgt);
	return (tgs ? tgs->ts.size() : 0);
}

THRUSTER_HANDLE VESSEL::GetGroupThruster (THGROUP_HANDLE thg, oapi::UInt32 idx) const
{
	const ThrustGroupSpec *tgs = (const ThrustGroupSpec*)thg;
	GetVesselServices().Check(bool(tgs), "Invalid thruster group handle.");
	return (THRUSTER_HANDLE)(idx < tgs->ts.size() ? tgs->ts[idx] : nullptr);
}

THRUSTER_HANDLE VESSEL::GetGroupThruster (THGROUP_TYPE thgt, oapi::UInt32 idx) const
{
	const ThrustGroupSpec* tgs = vessel->GetThrusterGroup(thgt);
	return (THRUSTER_HANDLE)(tgs && idx < tgs->ts.size() ? tgs->ts[idx] : nullptr);
}

oapi::UInt32 VESSEL::GetUserThrusterGroupCount () const
{
	return vessel->m_thrusterGroupUsr.size();
}

bool VESSEL::ThrusterGroupDefined (THGROUP_TYPE thgt) const
{
	const ThrustGroupSpec* tgs = vessel->GetThrusterGroup(thgt);
	return (tgs && tgs->ts.size());
}

void VESSEL::SetThrusterGroupLevel (THGROUP_HANDLE thg, double level) const
{
	if      (level < 0.0) level = 0.0;
	else if (level > 1.0) level = 1.0;
	vessel->SetThrusterGroupLevel ((ThrustGroupSpec*)thg, level);
}

void VESSEL::SetThrusterGroupLevel (THGROUP_TYPE thgt, double level) const
{
	if      (level < 0.0) level = 0.0;
	else if (level > 1.0) level = 1.0;
	vessel->SetThrusterGroupLevel (thgt, level);
}

void VESSEL::IncThrusterGroupLevel (THGROUP_HANDLE thg, double dlevel) const
{
	vessel->IncThrusterGroupLevel ((ThrustGroupSpec*)thg, dlevel);
}

void VESSEL::IncThrusterGroupLevel (THGROUP_TYPE thgt, double dlevel) const
{
	vessel->IncThrusterGroupLevel (thgt, dlevel);
}

void VESSEL::IncThrusterGroupLevel_SingleStep (THGROUP_HANDLE thg, double dlevel) const
{
	vessel->IncThrusterGroupOverride ((ThrustGroupSpec*)thg, dlevel);
}

void VESSEL::IncThrusterGroupLevel_SingleStep (THGROUP_TYPE thgt, double dlevel) const
{
	vessel->IncThrusterGroupOverride (thgt, dlevel);
}

double VESSEL::GetThrusterGroupLevel (THGROUP_HANDLE thg) const
{
	return vessel->GetThrusterGroupLevel ((ThrustGroupSpec*)thg);
}

double VESSEL::GetThrusterGroupLevel (THGROUP_TYPE thgt) const
{
	return vessel->GetThrusterGroupLevel (thgt);
}

oapi::UInt VESSEL::AddExhaust (THRUSTER_HANDLE th, double lscale, double wscale, SURFHANDLE tex) const
{
	EXHAUSTSPEC es = {th, NULL, NULL, NULL, lscale, wscale, 0, 0, tex, 0};
	return vessel->AddExhaust (&es);
}

oapi::UInt VESSEL::AddExhaust (THRUSTER_HANDLE th, double lscale, double wscale, double lofs, SURFHANDLE tex) const
{
	EXHAUSTSPEC es = {th, NULL, NULL, NULL, lscale, wscale, lofs, 0, tex, 0};
	return vessel->AddExhaust (&es);
}

oapi::UInt VESSEL::AddExhaust (THRUSTER_HANDLE th, double lscale, double wscale, const VECTOR3 &pos, const VECTOR3 &dir, SURFHANDLE tex) const
{
	VECTOR3 p = {pos.x, pos.y, pos.z};
	VECTOR3 d = {-dir.x, -dir.y, -dir.z};
	EXHAUSTSPEC es = {th, NULL, &p, &d, lscale, wscale, 0, 0, tex, EXHAUST_CONSTANTPOS|EXHAUST_CONSTANTDIR};
	return vessel->AddExhaust (&es);
}

oapi::UInt VESSEL::AddExhaust (EXHAUSTSPEC *spec)
{
	return vessel->AddExhaust (spec);
}

bool VESSEL::DelExhaust (oapi::UInt idx) const
{
	return vessel->DelExhaust (idx);
}

oapi::UInt32 VESSEL::GetExhaustCount () const
{
	return vessel->nexhaust;
}

bool VESSEL::GetExhaustSpec (oapi::UInt idx, double *lscale, double *wscale, VECTOR3 *pos, VECTOR3 *dir, SURFHANDLE *tex) const
{
	if (idx < 0 || idx >= vessel->nexhaust) return false;
	EXHAUSTSPEC *es = vessel->exhaust[idx];
	*lscale = es->lsize;
	*wscale = es->wsize;
	*pos = *es->lpos;
	*dir = *es->ldir;
	if (es->lofs) {
		pos->x -= dir->x*es->lofs;
		pos->y -= dir->y*es->lofs;
		pos->z -= dir->z*es->lofs;
	}
	*tex = es->tex;
	return true;
}

bool VESSEL::GetExhaustSpec (oapi::UInt idx, EXHAUSTSPEC *spec)
{
	if (idx < 0 || idx >= vessel->nexhaust) return false;
	memcpy (spec, vessel->exhaust[idx], sizeof(EXHAUSTSPEC));
	return true;
}

double VESSEL::GetExhaustLevel (oapi::UInt idx) const
{
	if (idx < 0 || idx >= vessel->nexhaust) return 0.0;
	return *vessel->exhaust[idx]->level;
}

PSTREAM_HANDLE VESSEL::AddParticleStream (PARTICLESTREAMSPEC *pss, const VECTOR3 &pos, const VECTOR3 &dir, double *lvl) const
{
	Vector p (pos.x, pos.y, pos.z);
	Vector d (dir.x, dir.y, dir.z);
	return (PSTREAM_HANDLE)vessel->AddParticleStream (pss, p, d, lvl);
}

PSTREAM_HANDLE VESSEL::AddExhaustStream (THRUSTER_HANDLE th, PARTICLESTREAMSPEC *pss) const
{
	return (PSTREAM_HANDLE)vessel->AddExhaustStream ((ThrustSpec*)th, pss);
}

PSTREAM_HANDLE VESSEL::AddExhaustStream (THRUSTER_HANDLE th, const VECTOR3 &pos, PARTICLESTREAMSPEC *pss) const
{
	Vector p (pos.x, pos.y, pos.z);
	return (PSTREAM_HANDLE)vessel->AddExhaustStream ((ThrustSpec*)th, pss, &p);
}

bool VESSEL::DelExhaustStream (PSTREAM_HANDLE ch) const
{
	return vessel->DelExhaustStream ((oapi::ParticleStream*)ch);
}

PSTREAM_HANDLE VESSEL::AddReentryStream (PARTICLESTREAMSPEC *pss) const
{
	return (PSTREAM_HANDLE)vessel->AddReentryStream (pss);
}

// Airfoil functions

void VESSEL::CreateAirfoil (AIRFOIL_ORIENTATION align, const VECTOR3 &ref, AirfoilCoeffFunc cf, double c, double S, double A) const
{
	Vector r(MakeVector(ref));
	vessel->CreateAirfoil (align, r, cf, c, S, A);
}

AIRFOILHANDLE VESSEL::CreateAirfoil2 (AIRFOIL_ORIENTATION align, const VECTOR3 &ref, AirfoilCoeffFunc cf, double c, double S, double A) const
{
	Vector r(MakeVector(ref));
	return (AIRFOILHANDLE)vessel->CreateAirfoil (align, r, cf, c, S, A);
}

AIRFOILHANDLE VESSEL::CreateAirfoil3 (AIRFOIL_ORIENTATION align, const VECTOR3 &ref, AirfoilCoeffFuncEx cf, void *context, double c, double S, double A) const
{
	Vector r(MakeVector(ref));
	return (AIRFOILHANDLE)vessel->CreateAirfoil (align, r, cf, context, c, S, A);
}

AIRFOILHANDLE VESSEL::CreateAirfoil4 (const VECTOR3& ref, AirfoilCoeffFuncEx2 cf, void* context, double c, double S, double A) const
{
	Vector r(MakeVector(ref));
	return (AIRFOILHANDLE)vessel->CreateAirfoil(FORCE_AND_MOMENT, r, cf, context, c, S, A);
}

bool VESSEL::GetAirfoilParam (AIRFOILHANDLE hAirfoil, VECTOR3 *ref, AirfoilCoeffFunc *cf, void **context, double *c, double *S, double *A) const
{
	return vessel->GetAirfoilParam ((AirfoilSpec*)hAirfoil, ref, cf, context, c, S, A);
}

void VESSEL::EditAirfoil (AIRFOILHANDLE hAirfoil, oapi::UInt32 flag, const VECTOR3 &ref, AirfoilCoeffFunc cf, double c, double S, double A) const
{
	vessel->EditAirfoil ((AirfoilSpec*)hAirfoil, flag, MakeVector(ref), cf, c, S, A);
}

bool VESSEL::DelAirfoil (AIRFOILHANDLE hAirfoil) const
{
	return vessel->DelAirfoil ((AirfoilSpec*)hAirfoil);
}

void VESSEL::ClearAirfoilDefinitions () const
{
	vessel->ClearAirfoilDefinitions();
}

void VESSEL::CreateControlSurface (AIRCTRL_TYPE type, double area, double dCl, const VECTOR3 &ref, int axis, oapi::UInt anim) const
{
	vessel->CreateControlSurface (type, area, dCl, MakeVector(ref), axis, 1.0, anim);
}

CTRLSURFHANDLE VESSEL::CreateControlSurface2 (AIRCTRL_TYPE type, double area, double dCl, const VECTOR3 &ref, int axis, oapi::UInt anim) const
{
	return vessel->CreateControlSurface (type, area, dCl, MakeVector(ref), axis, 1.0, anim);
}

CTRLSURFHANDLE VESSEL::CreateControlSurface3 (AIRCTRL_TYPE type, double area, double dCl, const VECTOR3 &ref, int axis, double delay, oapi::UInt anim) const
{
	return vessel->CreateControlSurface (type, area, dCl, MakeVector(ref), axis, delay, anim);
}

bool VESSEL::DelControlSurface (CTRLSURFHANDLE hCtrlSurf) const
{
	return vessel->DelControlSurface ((CtrlsurfSpec*)hCtrlSurf);
}

void VESSEL::ClearControlSurfaceDefinitions () const
{
	vessel->ClearControlSurfaceDefinitions();
}

void VESSEL::SetControlSurfaceLevel (AIRCTRL_TYPE type, double level) const
{
	vessel->SetControlSurfaceLevel (type, min (1.0, max (-1.0, level)), false);
}

void VESSEL::SetControlSurfaceLevel (AIRCTRL_TYPE type, double level, bool direct) const
{
	vessel->SetControlSurfaceLevel (type, min (1.0, max (-1.0, level)), false, direct);
}

double VESSEL::GetControlSurfaceLevel (AIRCTRL_TYPE type) const
{
	return vessel->GetControlSurfaceLevel (type);
}

void VESSEL::CreateVariableDragElement (double *drag, double factor, const VECTOR3 &ref) const
{
	LOGOUT_OBSOLETE;
	vessel->CreateVariableDragElement (drag, factor, MakeVector(ref));
}

void VESSEL::CreateVariableDragElement (const double *drag, double factor, const VECTOR3 &ref) const
{
	vessel->CreateVariableDragElement (drag, factor, MakeVector(ref));
}

void VESSEL::ClearVariableDragElements () const
{
	vessel->ClearVariableDragElements ();
}

void VESSEL::SetNosewheelSteering (bool activate) const
{
	vessel->nosesteering = activate;
}

bool VESSEL::GetNosewheelSteering () const
{
	return vessel->nosesteering;
}

void VESSEL::SetSurfaceFrictionCoeff (double mu_lng, double mu_lat) const
{
	vessel->SetSurfaceFrictionCoeff (mu_lng, mu_lat);
}

void VESSEL::SetMaxWheelbrakeForce (double f) const
{
	vessel->max_wbrake_F = f;
}

void VESSEL::SetWheelbrakeLevel (double level, int which, bool permanent) const
{
	vessel->SetWBrakeLevel (level, which, permanent);
}

double VESSEL::GetWheelbrakeLevel (int which) const
{
	if (!which) {
		double w1 = vessel->wbrake[0]; //(vessel->wbrake_override[0] ? vessel->wbrake_override[0] : vessel->wbrake_permanent[0]);
		double w2 = vessel->wbrake[1]; //(vessel->wbrake_override[1] ? vessel->wbrake_override[0] : vessel->wbrake_permanent[1]);
		return 0.5*(w1+w2);
	} else {
		which--;
		return vessel->wbrake[which]; //(vessel->wbrake_override[which] ? vessel->wbrake_override[which] : vessel->wbrake_permanent[which]);
	}
}

void VESSEL::InitNavRadios (oapi::UInt32 nnav) const
{
	vessel->InitNavRadios (nnav);
}

oapi::UInt32 VESSEL::GetNavCount () const
{
	return vessel->nnav;
}

bool VESSEL::SetNavChannel (oapi::UInt32 n, oapi::UInt32 step) const
{
	return vessel->SetNavChannel (n, step);
}

oapi::UInt32 VESSEL::GetNavChannel (oapi::UInt32 n) const
{
	return vessel->GetNavChannel (n);
}

float VESSEL::GetNavRecvFreq (oapi::UInt32 n) const
{
	return vessel->GetNavFreq (n);
}

bool VESSEL::SetTransponderChannel (oapi::UInt32 ch) const
{
	return vessel->SetXpdrChannel (ch);
}

bool VESSEL::SetIDSChannel (DOCKHANDLE hDock, oapi::UInt32 ch) const
{
	return vessel->SetIDSChannel ((PortSpec*)hDock, ch);
}

void VESSEL::EnableTransponder (bool enable) const
{
	if (enable) {
		if (!vessel->xpdr) { vessel->xpdr = new Nav_XPDR (vessel, NAV_RADIO_FREQ_MIN); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__); }
	} else {
		if (vessel->xpdr) delete vessel->xpdr, vessel->xpdr = 0;
	}
}

void VESSEL::EnableIDS (DOCKHANDLE hDock, bool bEnable) const
{
	PortSpec *ps = (PortSpec*)hDock;
	if (bEnable) {
		if (!ps->ids) { ps->ids = new Nav_IDS (vessel, ps, NAV_RADIO_FREQ_MIN); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__); }
	} else {
		GetRigidBodyServices().World()->BroadcastVessel (MSG_KILLNAVSENDER, ps->ids);
		if (ps->ids) delete ps->ids, ps->ids = 0;
	}
}

NAVHANDLE VESSEL::GetTransponder () const
{
	return (NAVHANDLE)vessel->xpdr;
}

NAVHANDLE VESSEL::GetIDS (DOCKHANDLE hDock) const
{
	PortSpec *dock = (PortSpec*)hDock;
	return (NAVHANDLE)dock->ids;
}

NAVHANDLE VESSEL::GetNavSource (oapi::UInt32 n) const
{
	return (n < vessel->nnav ? (NAVHANDLE)vessel->nav[n].sender : NULL);
}

bool VESSEL::GroundContact () const
{
	return vessel->bSurfaceContact;
}

bool VESSEL::OrbitStabilised () const
{
	return vessel->isOrbitStabilised();
}

bool VESSEL::NonsphericalGravityEnabled () const
{
	return vessel->bGPerturb;
}

int VESSEL::SendBufferedKey (oapi::UInt32 key, bool down, char *kstate)
{
	static char def_kstate[256] = {0};
	if (!kstate) kstate = def_kstate;
	return vessel->ConsumeBufferedKey (key, down, kstate);
}

bool VESSEL::GetEditorModule (char *fname) const
{
	return vessel->EditorModule (fname);
}

bool VESSEL::MeshgroupTransform (VISHANDLE vis, const MESHGROUP_TRANSFORM &mt) const
{
	return false; // not supported yet
}

// ==============================================================
// Obsolete VESSEL methods

bool VESSEL::SetNavRecv (oapi::UInt32 n, oapi::UInt32 step) const
{
	LOGOUT_OBSOLETE;
	return vessel->SetNavChannel (n, step);
}

oapi::UInt32 VESSEL::GetNavRecv (oapi::UInt32 n) const
{
	LOGOUT_OBSOLETE;
	return vessel->GetNavChannel (n);
}

// =======================================================================
// =======================================================================
// class VESSEL2: module interface to vessel class (extended)

VESSEL2::VESSEL2 (OBJHANDLE hVessel, int fmodel): VESSEL (hVessel, fmodel)
{
	version = 1;
}

void VESSEL2::clbkSetClassCaps (FILEHANDLE cfg)
{
}

void VESSEL2::clbkSaveState (FILEHANDLE scn)
{
	vessel->WriteDefault (*(ostream*)scn);
}

void VESSEL2::clbkLoadStateEx (FILEHANDLE scn, void *status)
{
	vessel->ParseScenarioEx (*(ifstream*)scn, status);
}

void VESSEL2::clbkSetStateEx (const void *status)
{
	vessel->SetStateEx (status);
}

void VESSEL2::clbkPostCreation ()
{
}

void VESSEL2::clbkFocusChanged (bool getfocus, OBJHANDLE hNewVessel, OBJHANDLE hOldVessel)
{
}

void VESSEL2::clbkPreStep (double simt, double simdt, double mjd)
{
}

void VESSEL2::clbkPostStep (double simt, double simdt, double mjd)
{
}

bool VESSEL2::clbkPlaybackEvent (double simt, double event_t, const char *event_type, const char *event)
{
	return false;
}

void VESSEL2::clbkVisualCreated (VISHANDLE vis, int refcount)
{
}

void VESSEL2::clbkVisualDestroyed (VISHANDLE vis, int refcount)
{
}



void VESSEL2::clbkRCSMode (int mode)
{
}

void VESSEL2::clbkADCtrlMode (oapi::UInt32 mode)
{
}

void VESSEL2::clbkHUDMode (int mode)
{
}

void VESSEL2::clbkMFDMode (int mfd, int mode)
{
}

void VESSEL2::clbkNavMode (int mode, bool active)
{
}

void VESSEL2::clbkDockEvent (int dock, OBJHANDLE mate)
{
}

void VESSEL2::clbkAnimate (double simt)
{
}

int VESSEL2::clbkConsumeDirectKey (char *keystate)
{
	return 0;
}

int VESSEL2::clbkConsumeBufferedKey (oapi::UInt32 key, bool down, char *keystate)
{
	return 0;
}

bool VESSEL2::clbkLoadGenericCockpit ()
{
	SetCameraDefaultDirection (_V(0,0,1));
	return true;
}

bool VESSEL2::clbkLoadPanel (int id)
{
	return false;
}

bool VESSEL2::clbkPanelMouseEvent (int id, int event, int mx, int my)
{
	return false;
}

bool VESSEL2::clbkPanelRedrawEvent (int id, int event, SURFHANDLE surf)
{
	return false;
}

bool VESSEL2::clbkLoadVC (int id)
{
	return false;
}

bool VESSEL2::clbkVCMouseEvent (int id, int event, VECTOR3 &p)
{
	return false;
}

bool VESSEL2::clbkVCRedrawEvent (int id, int event, SURFHANDLE surf)
{
	return false;
}


// =======================================================================
// =======================================================================
// class VESSEL3: module interface to vessel class (extended)

VESSEL3::VESSEL3 (OBJHANDLE hVessel, int fmodel): VESSEL2 (hVessel, fmodel)
{
	version = 2;
}











bool VESSEL3::clbkPanelMouseEvent (int id, int event, int mx, int my, void *context)
{
	return false;
}

bool VESSEL3::clbkPanelRedrawEvent (int id, int event, SURFHANDLE surf, void *context)
{
	return false;
}

int VESSEL3::clbkGeneric (int msgid, int prm, void *context)
{
	return 0;
}

bool VESSEL3::clbkLoadPanel2D (int id, PANELHANDLE hPanel, oapi::UInt32 viewW, oapi::UInt32 viewH)
{
	return false;
}





void VESSEL3::clbkGetRadiationForce (const VECTOR3 &mflux, VECTOR3 &F, VECTOR3 &pos)
{
	double size = vessel->size;
	double cs = size*size;  // simplified cross section
	double albedo = 1.5;    // simplistic albedo (mixture of absorption, reflection)

	F = mflux * (cs*albedo);
	pos = _V(0,0,0);        // don't induce torque
}



// =======================================================================
// =======================================================================
// class VESSEL4: module interface to vessel class (extended)

VESSEL4::VESSEL4 (OBJHANDLE hVessel, int fmodel) : VESSEL3 (hVessel, fmodel)
{
	version = 3;
}



int VESSEL4::RegisterMFDMode(const MFDMODESPECEX &spec)
{
	return vessel->RegisterMFDMode (&spec);
}

bool VESSEL4::UnregisterMFDMode (int mode)
{
	return vessel->UnregisterMFDMode (mode);
}

int VESSEL4::clbkNavProcess (int mode)
{
	return mode;
}
