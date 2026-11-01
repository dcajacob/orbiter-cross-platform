// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#define OAPI_IMPLEMENTATION

#include "Astro.h"
#include "Orbiter.h"
#include "Vessel.h"
#include "SuperVessel.h"
#include "Config.h"
#include "Camera.h"
#include "Pane.h"
#include "Panel2D.h"
#include "Element.h"
#include "Psys.h"
#include "Base.h"
#include "Mfd.h"
#include "Keymap.h"
#include "Log.h"
#include "Dialogs.h"
#include "State.h"
#include "Util.h"
#include "Planet.h"
#include "Mesh.h"
#include "CollisionCore.h"
#include "elevmgr.h"
#include <fstream>
#include <iomanip>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <functional>
#include <stdio.h>
#include <stdlib.h>
#include <string>

using namespace std;

extern Orbiter *g_pOrbiter;
extern Vessel *g_focusobj;
extern Camera *g_camera;
extern Pane *g_pane;
extern Select *g_select;
extern InputBox *g_input;
extern TimeData td;
extern PlanetarySystem *g_psys;
extern bool g_bStateUpdate;

extern char DBG_MSG[256];


int Vessel::ConsumeBufferedKey (DWORD key, bool down, char *kstate)
{
	int res;
	const Keymap &keymap = g_pOrbiter->keymap;

	// first offer the key to the module
	if (modIntf.v->Version() >= 1)
		if (res = ((VESSEL2*)modIntf.v)->clbkConsumeBufferedKey (key, down, kstate)) return res;
	// If module processes the key, we skip default handler

	if (!down) return 0; // at the moment, only process keydown events

	// Navigation computer modes
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMHoldAltitude)) TglNavMode (NAVMODE_HOLDALT);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMHLevel))       TglNavMode (NAVMODE_HLEVEL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMPrograde))     TglNavMode (NAVMODE_PROGRADE);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMRetrograde))   TglNavMode (NAVMODE_RETROGRADE);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMNormal))       TglNavMode (NAVMODE_NORMAL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMAntinormal))   TglNavMode (NAVMODE_ANTINORMAL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMKillrot))      TglNavMode (NAVMODE_KILLROT);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_RCSEnable))      SetAttMode (attmode >= 1 ? 0 : 1);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_RCSMode))        ToggleAttMode ();
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_Undock))         UndockInteractive ();

	// HUD control (internal view only)
	if (g_camera->IsInternal()) {
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUD))          g_pane->ToggleHUD();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDMode))      g_pane->SwitchHUDMode();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDReference))
			if (g_pane->GetHUD())                                      g_pane->GetHUD()->SelectReference();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDTarget))
			if (g_pane->GetHUD() && g_pane->GetHUD()->Mode() == HUD_DOCKING)    ((HUD_Docking*)g_pane->GetHUD())->SelectReferenceOld();
	}

	if (KEYMOD_CONTROL (kstate)) {  // CTRL-Key combinations

		switch (key) {
		case OAPI_KEY_C:        // landing/takeoff clearance request
			IssueClearanceRequest ();
			return 1;
		}

	} else if (KEYMOD_SHIFT (kstate)) { // virtual instrument
	} else if (KEYMOD_ALT (kstate)) {   // ALT-Key combinations

		switch (key) {
		case OAPI_KEY_DIVIDE:   // connect/disconnect user input to aerodynamic control surfaces
			ToggleADCtrlMode ();
			return 1;
		}

	}
	return 0;
}

void Vessel::DrawHUD (HUD *hud, oapi::Sketchpad *skp)
{
	if (modIntf.v->Version() >= 1) {
		bool drawn = false;
		if (modIntf.v->Version() >= 2) {
			drawn = ((VESSEL3*)modIntf.v)->clbkDrawHUD (hud->Mode(), hud->PaintSpec(), skp);
		}
	} else
		hud->DrawDefault (skp);
}

void Vessel::RenderHUD (HUD *hud, int mode, HUDPAINTSPEC *spec, SURFHANDLE hTex)
{
	if (modIntf.v->Version() >= 2)
		((VESSEL3*)modIntf.v)->clbkRenderHUD (mode, spec, hTex);
	else
		hud->RenderDefault ();
}

int Vessel::RegisterMFDMode (const MFDMODESPECEX *spec)
{
	// note: should check for mode already present
	MFDMODE *tmp = new MFDMODE[nmfdmode+1];
	if (nmfdmode) {
		memcpy (tmp, mfdmode, nmfdmode*sizeof(MFDMODE));
		delete []mfdmode;
	}
	mfdmode = tmp;
	mfdmode[nmfdmode].spec = new MFDMODESPECEX;
	mfdmode[nmfdmode].oldspec = new MFDMODESPEC;
	memcpy (mfdmode[nmfdmode].spec, spec, sizeof(MFDMODESPECEX));
	mfdmode[nmfdmode].spec->name = new char[strlen(spec->name)+1];
	strcpy (mfdmode[nmfdmode].spec->name, spec->name);
	mfdmode[nmfdmode].id = nmfdmode+1000;

	// check for duplicate key codes and disable if required
	if (spec->key) {
		DWORD i, k;
		for (i = 0; i < nmfdmode; i++)
			if (mfdmode[i].spec->key == spec->key) break;
		if (i < nmfdmode) { // key already assigned
			mfdmode[nmfdmode].spec->key = 0;
			for (k = OAPI_KEY_1; k <= OAPI_KEY_0; k++) {
				for (i = 0; i < nmfdmode; i++)
					if (mfdmode[i].spec->key == k) break;
				if (i == nmfdmode) { // found un-assigned key
					mfdmode[nmfdmode].spec->key = k;
					break;
				}
			}
		}
	}

	mfdmode[nmfdmode].oldspec->key = mfdmode[nmfdmode].spec->key;
	mfdmode[nmfdmode].oldspec->name = mfdmode[nmfdmode].spec->name;
	mfdmode[nmfdmode].oldspec->msgproc = mfdmode[nmfdmode].spec->msgproc;

	return mfdmode[nmfdmode++].id;
}

bool Vessel::UnregisterMFDMode (int id)
{
	DWORD i, j, k;
	for (i = 0; i < nmfdmode; i++)
		if (mfdmode[i].id == id) break;
	if (i == nmfdmode) return false;

	delete []mfdmode[i].spec->name;
	mfdmode[i].spec->name = NULL;
	delete mfdmode[i].spec;
	delete mfdmode[i].oldspec;
	MFDMODE *tmp = NULL;
	if (nmfdmode > 1) {
		tmp = new MFDMODE[nmfdmode-1];
		for (j = k = 0; j < nmfdmode; j++)
			if (j != i) {
				tmp[k].spec = mfdmode[j].spec;
				tmp[k].oldspec = mfdmode[j].oldspec;
				tmp[k].id = mfdmode[j].id;
				k++;
			}
	}
	delete []mfdmode;
	mfdmode = tmp;
	nmfdmode--;
	return true;
}

void Vessel::UnregisterMFDModes ()
{
	while (nmfdmode)
		UnregisterMFDMode (mfdmode[0].id);
}

bool Vessel::LoadPanel2D (int which, Panel2D *panel) const
{
	if (modIntf.v && modIntf.v->Version() >= 2) {
		oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient();
		if (gc) {
			DWORD viewW, viewH;
			gc->clbkGetViewportSize (&viewW, &viewH);
			return ((VESSEL3*)modIntf.v)->clbkLoadPanel2D (which, (PANELHANDLE)panel, viewW, viewH);
		}
	}
	return false;
}

void Vessel::LeanCamera (int dir, bool smooth)
{
	switch (dir) {
	case 0: // default position
		if (smooth) g_camera->MoveTo (Vector(0,0,0));
		else        g_camera->MoveToDirect (Vector(0,0,0));
		g_camera->ResetCockpitDir (smooth);
		break;
	case 1: // forward
		if (smooth) g_camera->MoveTo (camfwd.pos);
		else        g_camera->MoveToDirect (camfwd.pos);
		g_camera->ResetCockpitDir(camfwd.phi, camfwd.tht, smooth);
		break;
	case 2: // left
		if (smooth) g_camera->MoveTo (camleft.pos);
		else        g_camera->MoveToDirect (camleft.pos);
		g_camera->ResetCockpitDir(camleft.phi, camleft.tht, smooth);
		//g_camera->ResetCockpitDir(60*RAD, 0/*g_camera->ctheta0*/);
		break;
	case 3: // right
		if (smooth) g_camera->MoveTo (camright.pos);
		else        g_camera->MoveToDirect (camright.pos);
		g_camera->ResetCockpitDir(camright.phi, camright.tht, smooth);
		//g_camera->ResetCockpitDir(-60*RAD, 0/*g_camera->ctheta0*/);
		break;
	}
}

bool Vessel::LoadModule (ifstream &classf)
{
	char cbuf[256];
	bool found;
	hMod = 0;
	ClearModule();
	modIntf.v = 0;
	modIntf.coreCreated = false;
	flightmodel = g_pOrbiter->Cfg()->CfgLogicPrm.FlightModelLevel;
	if (found = GetItemString (classf, "Module", cbuf)) {
		found = RegisterModule (cbuf);
		if (!found) {
			DWORD code = GetLastError();
			char errbuf[256];
			sprintf(errbuf, "Could not load vessel module: %s (code %d)", cbuf, code);
			LOGOUT_ERR (errbuf);
		}
		if (modIntf.ovcInit)
			modIntf.v = modIntf.ovcInit ((OBJHANDLE)this, flightmodel);
	}
	if (!modIntf.v) { // Problem: module didn't create a VESSEL instance!
		modIntf.v = new VESSEL ((OBJHANDLE)this, flightmodel); TRACENEW
		modIntf.coreCreated = true;
	}
	return found;
}

bool Vessel::RegisterModule (const char *dllname)
{
	char cbuf[256];
	sprintf (cbuf, "Modules\\%s.dll", dllname);
	hMod = LoadLibrary (cbuf);
	if (!hMod)
		return false;

	// retrieve module version
	int (*fversion)() = (int(*)())GetProcAddress (hMod, "GetModuleVersion");
	modIntf.version = (fversion ? fversion() : 0);

	modIntf.ovcInit = (VESSEL_Init)GetProcAddress (hMod, "ovcInit");
	modIntf.ovcExit = (VESSEL_Exit)GetProcAddress (hMod, "ovcExit");
	return true;
}

void Vessel::ClearModule ()
{
	if (hMod) {
		FreeLibrary (hMod);
		hMod = 0;
	}
	memset (&modIntf, 0, sizeof (modIntf));
}

oapi::ParticleStream *Vessel::AddParticleStream (PARTICLESTREAMSPEC *pss, const Vector &pos, const Vector &dir, double *lvl)
{
	if (!g_pOrbiter->Cfg()->CfgVisualPrm.bParticleStreams) return 0;
	oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient ();
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[ncontrail+1]; TRACENEW
	if (ncontrail) {
		memcpy (tmp, contrail, ncontrail*sizeof(oapi::ParticleStream*));
		delete []contrail;
	}
	contrail = tmp;
	contrail[ncontrail] = gc->clbkCreateExhaustStream (pss, (OBJHANDLE)this, lvl, MakeVECTOR3(pos), MakeVECTOR3(-dir));
	return contrail[ncontrail++];
}

oapi::ParticleStream *Vessel::AddExhaustStream (ThrustSpec *ts, PARTICLESTREAMSPEC *pss, const Vector *pos, const Vector *dir)
{
	if (!g_pOrbiter->Cfg()->CfgVisualPrm.bParticleStreams) return 0;
	oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient ();
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[ncontrail+1]; TRACENEW
	if (ncontrail) {
		memcpy (tmp, contrail, ncontrail*sizeof(oapi::ParticleStream*));
		delete []contrail;
	}
	contrail = tmp;
	contrail[ncontrail] = gc->clbkCreateExhaustStream (pss, (OBJHANDLE)this, &ts->level, &ts->ref, &ts->dir);
	if (pos) // local position reference
		contrail[ncontrail]->SetFixedPos (MakeVECTOR3(*pos));
	if (dir) // local direction reference
		contrail[ncontrail]->SetFixedDir (MakeVECTOR3(*dir));
	return contrail[ncontrail++];
}

bool Vessel::DelExhaustStream (oapi::ParticleStream *ep)
{
	if (!ncontrail) return false;

	DWORD i, j, k;
	for (i = 0; i < ncontrail; i++)
		if (contrail[i] == ep) break;
	if (i == ncontrail) return false;

	ep->Detach();
	// we detach the contrail from its source, but leave it
	// to the scene to delete it once all particles have expired

	oapi::ParticleStream **tmp;
	if (ncontrail > 1) {
		tmp = new oapi::ParticleStream*[ncontrail-1]; TRACENEW
		for (j = k = 0; j < ncontrail; j++)
			if (j != i) tmp[k++] = contrail[j];
	} else tmp = 0;
	delete []contrail;
	contrail = tmp;
	ncontrail--;
	return true;
}

oapi::ParticleStream *Vessel::AddReentryStream (PARTICLESTREAMSPEC *pss)
{
	if (!g_pOrbiter->Cfg()->CfgVisualPrm.bParticleStreams) return 0;
	oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient ();
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[nreentrystream+1]; TRACENEW
	if (nreentrystream) {
		memcpy (tmp, reentrystream, nreentrystream*sizeof(oapi::ParticleStream*));
		delete []reentrystream;
	}
	reentrystream = tmp;
	reentrystream[nreentrystream] = gc->clbkCreateReentryStream (pss, (OBJHANDLE)this);
	return reentrystream[nreentrystream++];
}

bool Vessel::DelReentryStream (oapi::ParticleStream *ep)
{
	if (!nreentrystream) return false;

	DWORD i, j, k;

	for (i = 0; i < nreentrystream; i++)
		if (reentrystream[i] == ep) break;
	if (i == nreentrystream) return false;

	ep->Detach();
	// we detach the contrail from its source, but leave it
	// to the scene to delete it once all particles have expired

	oapi::ParticleStream **tmp;
	if (nreentrystream > 1) {
		tmp = new oapi::ParticleStream*[nreentrystream-1]; TRACENEW
		for (j = k = 0; j < nreentrystream; j++)
			if (j != i) tmp[k++] = reentrystream[j];
	} else tmp = 0;
	delete []reentrystream;
	reentrystream = tmp;
	nreentrystream--;
	return true;
}

void Vessel::ClearReentryStreams ()
{
	if (nreentrystream) {
		for (DWORD i = 0; i < nreentrystream; i++)
			reentrystream[i]->Detach();
		delete []reentrystream;
		reentrystream = NULL;
		nreentrystream = 0;
	}
}

void Vessel::ClearExhaustStreamDefinitions ()
{
	if (ncontrail) {
		for (DWORD i = 0; i < ncontrail; i++) contrail[i]->Detach();
		delete []contrail;
		contrail = NULL;
		ncontrail = 0;
	}
}

LightEmitter *Vessel::AddPointLight (const VECTOR3 &pos, double range, double att0, double att1, double att2, COLOUR4 col_diff, COLOUR4 col_spec, COLOUR4 col_ambi)
{
	LightEmitter **tmp = new LightEmitter*[nemitter+1];
	if (nemitter) {
		memcpy (tmp, emitter, nemitter*sizeof(LightEmitter*));
		delete []emitter;
	}
	emitter = tmp;
	LightEmitter *pl = new PointLight ((OBJHANDLE)this, pos, range, att0, att1, att2, col_diff, col_spec, col_ambi);
	emitter[nemitter++] = pl;
	return pl;
}

LightEmitter *Vessel::AddSpotLight (const VECTOR3 &pos, const VECTOR3 &dir, double range, double att0, double att1, double att2, double umbra, double penumbra, COLOUR4 col_diff, COLOUR4 col_spec, COLOUR4 col_ambi)
{
	LightEmitter **tmp = new LightEmitter*[nemitter+1];
	if (nemitter) {
		memcpy (tmp, emitter, nemitter*sizeof(LightEmitter*));
		delete []emitter;
	}
	emitter = tmp;
	LightEmitter *pl = new SpotLight ((OBJHANDLE)this, pos, dir, range, att0, att1, att2, umbra, penumbra, col_diff, col_spec, col_ambi);
	emitter[nemitter++] = pl;
	return pl;
}

bool Vessel::DelLightEmitter (LightEmitter *le)
{
	DWORD i, j, k;
	for (i = 0; i < nemitter; i++) {
		if (emitter[i] == le) {
			LightEmitter **tmp;
			if (nemitter > 1) {
				tmp = new LightEmitter*[nemitter-1];
				for (j = k = 0; j < nemitter; j++)
					if (j != i) tmp[k++] = emitter[j];
			} else tmp = NULL;
			delete []emitter;
			emitter = tmp;
			delete le;
			nemitter--;
			return true;
		}
	}
	return false;
}

void Vessel::ClearLightEmitters ()
{
	if (!nemitter) return; // nothing to do
	for (DWORD i = 0; i < nemitter; i++) {
		if (emitter[i]) delete emitter[i];
	}
	delete []emitter;
	nemitter = 0;
}

void Vessel::LightEmitterState (LightEmitter *le, int param, void *value)
{
	DWORD idx;
	char cbuf[256];
	for (idx = 0; idx < nemitter; idx++)
		if (emitter[idx] == le) break;
	if (idx == nemitter) return;
	switch (param) {
	case 0: { // activation state
		bool active = *(bool*)value;
		sprintf (cbuf, "%d ACTIVATE %d", idx, active);
		FRecorder_SaveEvent ("LIGHTSOURCE", cbuf);
	} break;
	}
}

void Vessel::ShiftLightEmitters (const VECTOR3 &ofs)
{
	DWORD i;
	for (i = 0; i < nemitter; i++) {
		emitter[i]->ShiftExplicitPosition (ofs);
	}
}

struct UndockSpec {
	Vessel *vessel;
	const Vessel *exclude;
	double vsep;
} undockspec;

bool Vessel::ClbkSelect_Undock (Select *menu, int item, char *str, void *data)
{
	UndockSpec *us = (UndockSpec*)data;
	DWORD i;
	char cbuf[16] = "Dock ";
	for (i = 0; i < us->vessel->ndock; i++) {
		sprintf(cbuf + 5, "%d", i + 1);
		menu->Append (cbuf, us->vessel->dock[i]->mate ? 0 : ITEM_NOHILIGHT);
	}
	return true;
}

bool Vessel::ClbkEnter_Undock (Select *menu, int item, char *str, void *data)
{
	return ClbkName_Undock (0, str+5, data);
}

bool Vessel::ClbkName_Undock (InputBox*, char *str, void *data)
{
	UINT did;
	UndockSpec *us = (UndockSpec*)data;
	if (sscanf (str, "%d", &did) && did >= 1 && did <= us->vessel->ndock)
		return us->vessel->Undock (did-1, us->exclude, us->vsep);
	else
		return false;
}

void Vessel::UndockInteractive (const Vessel *exclude, double vsep)
{
	UINT did = 0;
	undockspec.vessel = this;
	undockspec.exclude = exclude;
	undockspec.vsep = vsep;
	if (ndock == 1) {
		Undock (0, exclude, vsep);
	} else if (ndock) {
		if (ndock <= 20) {
			g_select->Open ("Select dock to disengage", ClbkSelect_Undock, ClbkEnter_Undock, (void*)&undockspec);
		} else {
			char cbuf[128] = "Select dock to disengage ";
			sprintf (cbuf+25, "(1-%d)", ndock);
			g_input->Open (cbuf, 0, 20, ClbkName_Undock, (void*)&undockspec);
		}
	}
}

// ==============================================================
