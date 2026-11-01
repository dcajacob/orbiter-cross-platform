// Licensed under the MIT License
// Explicit pre-cockpit capability boundary; the external-view host exposes none
// of these operations. Windows keeps the original implementations.
#include "NativeVesselAPI.h"
#include <stdexcept>

void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd) const
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::SetCameraDefaultDirection");}

void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd, double tilt) const
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::SetCameraDefaultDirection");}

void VESSEL::SetCameraCatchAngle (double cangle) const
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::SetCameraCatchAngle");}

void VESSEL::TriggerPanelRedrawArea (int panel_id, int area_id)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::TriggerPanelRedrawArea");}

void VESSEL::TriggerRedrawArea (int panel_id, int vc_id, int area_id)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::TriggerRedrawArea");}

DEVMESHHANDLE VESSEL::GetDevMesh (VISHANDLE vis, oapi::UInt idx) const
{throw std::runtime_error("Native cockpit service unavailable: VESSEL::GetDevMesh");}

void VESSEL2::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, oapi::SdkDrawContext hDC)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL2::clbkDrawHUD");}

int VESSEL3::SetPanelBackground (PANELHANDLE hPanel, SURFHANDLE *hSurf, oapi::UInt32 nsurf, MESHHANDLE hMesh, oapi::UInt32 width, oapi::UInt32 height, oapi::UInt32 baseline, oapi::UInt32 scrollflag)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::SetPanelBackground");}

int VESSEL3::SetPanelScaling (PANELHANDLE hPanel, double defscale, double extscale)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::SetPanelScaling");}

int VESSEL3::RegisterPanelMFDGeometry (PANELHANDLE hPanel, int MFD_id, int nmesh, int ngroup)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::RegisterPanelMFDGeometry");}

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, const oapi::SdkRectangle &texpos, int draw_event, int mouse_event, int bkmode)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::RegisterPanelArea");}

int VESSEL3::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, int draw_event, int mouse_event, SURFHANDLE surf, void *context)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::RegisterPanelArea");}

bool VESSEL3::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, oapi::Sketchpad *skp)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::clbkDrawHUD");}

void VESSEL3::clbkRenderHUD (int mode, const HUDPAINTSPEC *hps, SURFHANDLE hDefaultTex)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL3::clbkRenderHUD");}

int VESSEL4::RegisterPanelArea (PANELHANDLE hPanel, int id, const oapi::SdkRectangle &pos, int texidx, const oapi::SdkRectangle &texpos, int draw_event, int mouse_event, int bkmode)
{throw std::runtime_error("Native cockpit service unavailable: VESSEL4::RegisterPanelArea");}
