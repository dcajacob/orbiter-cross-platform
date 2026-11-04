// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "NativeVesselAPI.h"
#include "Pane.h"
#include "CockpitServices.h"

void oapiRegisterPanelBackground (SURFHANDLE hBmp, oapi::UInt32 flag, oapi::UInt32 ck)
{
	orbiter::production::CockpitPane()->RegisterPanelBackground (hBmp, flag, ck);
}

void oapiRegisterPanelArea (int id, const oapi::SdkRectangle &pos, int draw_event, int mouse_event, int bkmode)
{
	orbiter::production::CockpitPane()->RegisterPanelArea (id, pos, draw_event, mouse_event, bkmode);
}
