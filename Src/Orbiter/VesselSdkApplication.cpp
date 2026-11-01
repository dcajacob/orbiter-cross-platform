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

void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd) const
{
	vessel->camdir0.Set (cd.x, cd.y, cd.z);
	vessel->camtilt0 = 0;
	if (vessel == g_focusobj) g_camera->SetDefaultCockpitDir (vessel->camdir0);
}

void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd, double tilt) const
{
	vessel->camdir0.Set (cd.x, cd.y, cd.z);
	vessel->camtilt0 = tilt;
	if (vessel == g_focusobj) g_camera->SetDefaultCockpitDir (vessel->camdir0, tilt);
}

void VESSEL::SetCameraCatchAngle (double cangle) const
{
	vessel->camcatchangle = cangle;
	if (vessel == g_focusobj) g_camera->SetCatchAngle (cangle);
}

void VESSEL::TriggerPanelRedrawArea (int panel_id, int area_id)
{
	if (g_pane && vessel == g_focusobj)
		g_pane->TriggerPanelRedrawArea (panel_id, area_id);
}

void VESSEL::TriggerRedrawArea (int panel_id, int vc_id, int area_id)
{
	if (g_pane && vessel == g_focusobj)
		g_pane->TriggerRedrawArea (panel_id, vc_id, area_id);
}

DEVMESHHANDLE VESSEL::GetDevMesh (VISHANDLE vis, UINT idx) const
{
	oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient();
	return (gc ? (DEVMESHHANDLE)gc->clbkGetMesh (vis, idx) : NULL);
}

void VESSEL2::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, HDC hDC)
{
	if (vessel->hudskp && vessel->hudskp->GetDC() == hDC)
		g_pane->DrawDefaultHUD (vessel->hudskp);
}

int VESSEL3::SetPanelBackground (PANELHANDLE hPanel, SURFHANDLE *hSurf, DWORD nsurf, MESHHANDLE hMesh, DWORD width, DWORD height, DWORD baseline, DWORD scrollflag)
{
	return ((Panel2D*)hPanel)->SetBackground (hSurf, nsurf, hMesh, width, height, baseline, scrollflag);
}

int VESSEL3::SetPanelScaling (PANELHANDLE hPanel, double defscale, double extscale)
{
	return ((Panel2D*)hPanel)->SetScaling (defscale, extscale);
}

int VESSEL3::RegisterPanelMFDGeometry (PANELHANDLE hPanel, int MFD_id, int nmesh, int ngroup)
{
	return ((Panel2D*)hPanel)->RegisterMFDGeometry (MFD_id, nmesh, ngroup);
}

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const RECT &pos, const RECT &texpos, int draw_event, int mouse_event, int bkmode)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, 0, texpos, draw_event | PANEL_REDRAW_GDI | PANEL_REDRAW_SKETCHPAD, mouse_event, bkmode);
}

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const RECT &pos, int draw_event, int mouse_event, SURFHANDLE surf, void *context)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, draw_event, mouse_event, surf, context);
}

bool VESSEL3::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, oapi::Sketchpad *skp)
{
	g_pane->DrawDefaultHUD (skp);
	return true;
}

void VESSEL3::clbkRenderHUD (int mode, const HUDPAINTSPEC *hps, SURFHANDLE hDefaultTex)
{
	g_pane->RenderDefaultHUD ();
}

int VESSEL4::RegisterPanelArea (PANELHANDLE hPanel, int id, const RECT &pos, int texidx, const RECT &texpos, int draw_event, int mouse_event, int bkmode)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, texidx, texpos, draw_event, mouse_event, bkmode);
}
