// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original production callbacks shared by the Windows and native adapters.
void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd) const
{
	vessel->camdir0.Set (cd.x, cd.y, cd.z);
	vessel->camtilt0 = 0;
	if (vessel == orbiter::production::CockpitFocus()) orbiter::production::CockpitCamera()->SetDefaultCockpitDir (vessel->camdir0);
}

void VESSEL::SetCameraDefaultDirection (const VECTOR3 &cd, double tilt) const
{
	vessel->camdir0.Set (cd.x, cd.y, cd.z);
	vessel->camtilt0 = tilt;
	if (vessel == orbiter::production::CockpitFocus()) orbiter::production::CockpitCamera()->SetDefaultCockpitDir (vessel->camdir0, tilt);
}

void VESSEL::SetCameraCatchAngle (double cangle) const
{
	vessel->camcatchangle = cangle;
	if (vessel == orbiter::production::CockpitFocus()) orbiter::production::CockpitCamera()->SetCatchAngle (cangle);
}

void VESSEL::TriggerPanelRedrawArea (int panel_id, int area_id)
{
	if (orbiter::production::ActiveCockpitPane() && vessel == orbiter::production::CockpitFocus())
		orbiter::production::CockpitPane()->TriggerPanelRedrawArea (panel_id, area_id);
}

void VESSEL::TriggerRedrawArea (int panel_id, int vc_id, int area_id)
{
	if (orbiter::production::ActiveCockpitPane() && vessel == orbiter::production::CockpitFocus())
		orbiter::production::CockpitPane()->TriggerRedrawArea (panel_id, vc_id, area_id);
}

DEVMESHHANDLE VESSEL::GetDevMesh (VISHANDLE vis, oapi::UInt idx) const
{
	oapi::CockpitClient *gc = orbiter::production::CockpitGraphicsClient();
	return (gc ? (DEVMESHHANDLE)gc->clbkGetMesh (vis, idx) : NULL);
}
