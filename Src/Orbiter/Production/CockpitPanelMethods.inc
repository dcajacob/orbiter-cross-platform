// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original production callbacks shared by the Windows and native adapters.
int VESSEL3::SetPanelBackground (PANELHANDLE hPanel, SURFHANDLE *hSurf, oapi::UInt32 nsurf, MESHHANDLE hMesh, oapi::UInt32 width, oapi::UInt32 height, oapi::UInt32 baseline, oapi::UInt32 scrollflag)
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

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, const oapi::SdkRectangle &texpos, int draw_event, int mouse_event, int bkmode)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, 0, texpos, draw_event | PANEL_REDRAW_GDI | PANEL_REDRAW_SKETCHPAD, mouse_event, bkmode);
}

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, int draw_event, int mouse_event, SURFHANDLE surf, void *context)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, draw_event, mouse_event, surf, context);
}

bool VESSEL3::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, oapi::Sketchpad *skp)
{
	orbiter::production::CockpitPane()->DrawDefaultHUD (skp);
	return true;
}

void VESSEL3::clbkRenderHUD (int mode, const HUDPAINTSPEC *hps, SURFHANDLE hDefaultTex)
{
	orbiter::production::CockpitPane()->RenderDefaultHUD ();
}

int VESSEL4::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, int texidx, const oapi::SdkRectangle &texpos, int draw_event, int mouse_event, int bkmode)
{
	return ((Panel2D*)hPanel)->DefineArea (id, pos, texidx, texpos, draw_event, mouse_event, bkmode);
}
