// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifdef _WIN32
#define OAPI_IMPLEMENTATION
#include "Orbiter.h"
#else
#include "NativeVesselAPI.h"
#endif
#include "Production/CockpitServices.h"
#include "Astro.h"
#include "Pane.h"
#include "Defpanel.h"

bool oapiSetHUDMode (int mode)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	return (pane ? pane->SetHUDMode (mode) : false);
}

bool oapiSetHUDMode (int mode, const HUDPARAM *prm)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	return (pane ? pane->SetHUDMode (mode, prm) : false);
}

int oapiGetHUDMode ()
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	return (pane ? pane->GetHUDMode () : 0);
}

int oapiGetHUDMode (HUDPARAM *prm)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	return (pane ? pane->GetHUDMode (prm) : 0);
}

void oapiToggleHUDColour ()
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane) pane->ToggleHUDColour ();
}

double oapiGetHUDIntensity ()
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	return (pane ? pane->HudIntens() : 0.0);
}

void oapiSetHUDIntensity (double val)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane) pane->SetHUDIntens (val);
}

void oapiIncHUDIntensity ()
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane) pane->IncHUDIntens ();
}

void oapiDecHUDIntensity ()
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane) pane->DecHUDIntens ();
}

void oapiRenderHUD (MESHHANDLE hMesh, SURFHANDLE *hTex)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane) pane->RenderCustomHUD (hMesh, hTex);
}

void oapiRegisterMFD (int mfd, const EXTMFDSPEC *spec)
{
	orbiter::production::CockpitPane()->RegisterMFD (mfd, spec);
}

void oapiSetPanelNeighbours (int left, int right, int top, int bottom)
{
	orbiter::production::CockpitPane()->SetPanelNeighbours (left, right, top, bottom);
}

void oapiVCSetNeighbours (int left, int right, int top, int bottom)
{
	orbiter::production::CockpitPane()->SetVCNeighbours (left, right, top, bottom);
}

bool oapiBltPanelAreaBackground (int area_id, SURFHANDLE surf)
{
	Pane *pane = orbiter::production::ActiveCockpitPane();
	if (pane)
		return pane->BltPanelAreaBackground (area_id, surf);
	else
		return false;
}

void oapiSetDefNavDisplay (int mode)
{
	DefaultPanel *defpanel = orbiter::production::CockpitPane()->GetDefaultPanel();
	if (defpanel) defpanel->SetNavDisplayMode (mode);
}

void oapiSetDefRCSDisplay (int mode)
{
	DefaultPanel *defpanel = orbiter::production::CockpitPane()->GetDefaultPanel();
	if (defpanel) defpanel->SetRCSDisplayMode (mode);
}

int oapiSwitchPanel (int direction)
{
	return orbiter::production::CockpitPane()->SwitchPanel (direction);
}

int oapiSetPanel (int panel_id)
{
	return orbiter::production::CockpitPane()->SelectPanel (panel_id);
}

void oapiSetPanelBlink (VECTOR3 v[4])
{
	orbiter::production::CockpitPane()->SetPanel2DBlink (v);
}

void oapiVCTriggerRedrawArea (int vc_id, int area_id)
{
	orbiter::production::CockpitPane()->TriggerVCRedrawArea (vc_id, area_id);
}

void oapiVCRegisterArea (int id, const oapi::SdkRectangle &tgtrect, int draw_event, int mouse_event, int bkmode, SURFHANDLE tgt)
{
	orbiter::production::CockpitPane()->RegisterVCArea (id, tgtrect, draw_event, mouse_event, bkmode, tgt);
}

void oapiVCRegisterArea (int id, int draw_event, int mouse_event)
{
	orbiter::production::CockpitPane()->RegisterVCArea (id, _R(0,0,0,0), draw_event, mouse_event, PANEL_MAP_NONE, NULL);
}

void oapiVCSetAreaClickmode_Spherical (int id, const VECTOR3 &cnt, double rad)
{
	orbiter::production::CockpitPane()->SetVCAreaClickmode_Spherical (id, Vector(cnt.x, cnt.y, cnt.z), rad);
}

void oapiVCSetAreaClickmode_Quadrilateral (int id, const VECTOR3 &p1, const VECTOR3 &p2, const VECTOR3 &p3, const VECTOR3 &p4)
{
	orbiter::production::CockpitPane()->SetVCAreaClickmode_Quadrilateral (id, Vector(p1.x, p1.y, p1.z), Vector(p2.x,p2.y,p2.z), Vector(p3.x,p3.y,p3.z), Vector(p4.x,p4.y,p4.z));
}

void FormatValue (char *cbuf, int n, double f, int precision)
{
	char *s = FloatStr (f, precision);
	strncpy (cbuf, s, n);
}
