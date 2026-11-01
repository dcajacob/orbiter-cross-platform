// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#define STRICT 1
#define OAPI_IMPLEMENTATION

#include <stdio.h>
#include <iomanip>

#include "resource.h"
#include "D3dmath.h"
#include "Camera.h"
#include "Config.h"
#include "Body.h"
#include "Planet.h"
#include "Vessel.h"
#include "Psys.h"
#include "Pane.h"
#include "Dialogs.h"
#include "DlgMgr.h"
#include "Orbiter.h"
#include "Orbitersdk.h"
#include "Util.h"
#include "Log.h"
#include "OrbiterAPI.h"
#include "Vobject.h"
#include <zmouse.h>

using namespace std;

extern Orbiter *g_pOrbiter;
extern TimeData td;
extern PlanetarySystem *g_psys;
extern Pane *g_pane;
extern Vessel *g_focusobj;
extern char DBG_MSG[256];

bool Camera::ProcessMouse (UINT event, DWORD state, DWORD x, DWORD y, const char *kstate)
{
	if (event != WM_MOUSEWHEEL)
		mx = (int)x, my = (int)y;

	switch (event) {
	case WM_LBUTTONDOWN:
		mbdown[0] = true;
		return true;
	case WM_RBUTTONDOWN:
		mbdown[1] = true;
		g_pOrbiter->InitRotationMode();
		return true;
	case WM_LBUTTONUP:
		if (mbdown[0]) {
			mbdown[0] = false;
			return true;
		}
		break;
	case WM_RBUTTONUP:
		if (mbdown[1]) {
			mbdown[1] = false;
			g_pOrbiter->ExitRotationMode();
			return true;
		}
		break;
	case WM_MOUSEWHEEL:
		if (KEYMOD_CONTROL(kstate)) {
		}
		else {
			short zDelta = (short)HIWORD(state);
			if (external_view)
				ShiftDist(-zDelta*0.001);
			else
				g_pOrbiter->IncFOV(zDelta*(-2.0 / 120.0*RAD));
		} return true;
		break;
	}
	return false;
}

void Camera::UpdateMouse ()
{
	POINT pt;
	GetCursorPos (&pt);
	if (pt.x != pm.x || pt.y != pm.y) {
		pm.x = pt.x, pm.y = pt.y;
		mmoveT = td.SysT0;
	}

	if (mbdown[1]) {
		int dx, dy, x0, y0;
		x0 = pt.x, y0 = pt.y;
		if (!g_pOrbiter->IsFullscreen())
			ScreenToClient (g_pOrbiter->GetRenderWnd(), &pt);
		dx = pt.x - mx;
		dy = pt.y - my;
		SetCursorPos (x0-dx, y0-dy);
		if (!(dx || dy)) return;

		if (external_view) {
			if (extmode == CAMERA_GROUNDOBSERVER) {
				if (go->LockedOnTarget()) {
					GroundObserverShift (dx*go->PanSpeed() * -0.005, dy*go->PanSpeed() * -0.005, 0.0);
				} else
					GroundObserverTilt (dx * -0.005, dy * -0.005);
			} else {
				if (dx) ShiftPhi (dx * -0.005);
				if (dy) ShiftTheta (dy * -0.005);
			}
		} else {
			Rotate (dx * -0.001, dy * -0.001);
		}
	}
}

bool Camera::Direction2Viewport(const Vector &dir, int &x, int &y)
{
	D3DVECTOR homog;
	D3DMath_VectorMatrixMultiply (homog, D3DMath_Vector(dir.x, dir.y, dir.z), *D3D_ProjViewMatrix());
	if (homog.x >= -1.0f && homog.y <= 1.0f && homog.z <= 1.0f) {
		if (std::hypot(homog.x, homog.y) < 1e-6) {
			x = (int)w05, y = (int)h05;
		} else {
			x = (int)(w05*(1.0f+homog.x));
			y = (int)(h05*(1.0f-homog.y));
		}
		return true;
	} else
		return false;
}

D3DMATRIX *Camera::D3D_ProjViewMatrix ()
{
	if (!pv_mat_valid) {
		D3DMath_MatrixMultiply (pv_mat, proj_mat, view_mat);
		pv_mat_valid = true;
	}
	return &pv_mat;
}

void Camera::UpdateProjectionMatrix ()
{
	ZeroMemory (&proj_mat, sizeof (D3DMATRIX));
	proj_mat._11 = (FLOAT)(aspect / tan_ap);
	proj_mat._22 = (FLOAT)(1.0    / tan_ap);
	if (farplane >= 1e20) {
		proj_mat._33 = 1.0f;
		proj_mat._43 = -nearplane;
	} else {
		proj_mat._43 = (proj_mat._33 = farplane / (farplane-nearplane)) * (-nearplane);
	}
	proj_mat._34 = 1.0f;

	// register new projection matrix with device
    //pDev->SetTransform (D3DTRANSFORMSTATE_PROJECTION, &proj_mat);
}
