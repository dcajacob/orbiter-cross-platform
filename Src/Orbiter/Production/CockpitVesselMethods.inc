// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original production callbacks shared by the Windows and native adapters.
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
		oapi::UInt32 i, k;
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
	oapi::UInt32 i, j, k;
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
		oapi::CockpitClient *gc = orbiter::production::CockpitGraphicsClient();
		if (gc) {
			oapi::UInt32 viewW, viewH;
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
		if (smooth) orbiter::production::CockpitCamera()->MoveTo (Vector(0,0,0));
		else        orbiter::production::CockpitCamera()->MoveToDirect (Vector(0,0,0));
		orbiter::production::CockpitCamera()->ResetCockpitDir (smooth);
		break;
	case 1: // forward
		if (smooth) orbiter::production::CockpitCamera()->MoveTo (camfwd.pos);
		else        orbiter::production::CockpitCamera()->MoveToDirect (camfwd.pos);
		orbiter::production::CockpitCamera()->ResetCockpitDir(camfwd.phi, camfwd.tht, smooth);
		break;
	case 2: // left
		if (smooth) orbiter::production::CockpitCamera()->MoveTo (camleft.pos);
		else        orbiter::production::CockpitCamera()->MoveToDirect (camleft.pos);
		orbiter::production::CockpitCamera()->ResetCockpitDir(camleft.phi, camleft.tht, smooth);
		//orbiter::production::CockpitCamera()->ResetCockpitDir(60*RAD, 0/*orbiter::production::CockpitCamera()->ctheta0*/);
		break;
	case 3: // right
		if (smooth) orbiter::production::CockpitCamera()->MoveTo (camright.pos);
		else        orbiter::production::CockpitCamera()->MoveToDirect (camright.pos);
		orbiter::production::CockpitCamera()->ResetCockpitDir(camright.phi, camright.tht, smooth);
		//orbiter::production::CockpitCamera()->ResetCockpitDir(-60*RAD, 0/*orbiter::production::CockpitCamera()->ctheta0*/);
		break;
	}
}
