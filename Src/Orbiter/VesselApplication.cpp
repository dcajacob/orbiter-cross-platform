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
#include "Production/CockpitServices.h"
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

#include "Production/CockpitVesselMethods.inc"

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
