// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original CameraApplication mouse algorithms with native window services.
#include "Camera.h"
#include "Keymap.h"
#include "TimeData.h"
#include "CockpitServices.h"
#include "NativeCockpitUi.h"
#include <cmath>
using namespace orbiter::production;
using std::ceil;
using std::floor;

bool Camera::ProcessMouse (oapi::UInt event, oapi::UInt32 state, oapi::UInt32 x, oapi::UInt32 y, const char *kstate)
{
	if (event != CockpitMouse::Wheel)
		mx = (int)x, my = (int)y;

	switch (event) {
	case CockpitMouse::LeftDown:
		mbdown[0] = true;
		return true;
	case CockpitMouse::RightDown:
		mbdown[1] = true;
		GetNativeRenderContext().graphics->SetCameraRotation(true);
		return true;
	case CockpitMouse::LeftUp:
		if (mbdown[0]) {
			mbdown[0] = false;
			return true;
		}
		break;
	case CockpitMouse::RightUp:
		if (mbdown[1]) {
			mbdown[1] = false;
			GetNativeRenderContext().graphics->SetCameraRotation(false);
			return true;
		}
		break;
	case CockpitMouse::Wheel:
		if (KEYMOD_CONTROL(kstate)) {
		}
		else {
			short zDelta = (short)CockpitHighWord(state);
			if (external_view)
				ShiftDist(-zDelta*0.001);
			else
				GetCameraServices().IncFOV(zDelta*(-2.0 / 120.0*RAD));
		} return true;
		break;
	}
	return false;
}

void Camera::UpdateMouse ()
{
	const auto cursor = GetNativeRenderContext().graphics->CursorPosition();
	oapi::SdkPoint pt = cursor;
	if (pt.x != pm.x || pt.y != pm.y) {
		pm.x = pt.x, pm.y = pt.y;
		mmoveT = GetRigidBodyServices().Time().SysT0;
	}

	if (mbdown[1]) {
		int dx, dy, x0, y0;
		x0 = pt.x, y0 = pt.y;
		// GLFW supplies framebuffer client coordinates; no desktop conversion is needed.
		dx = pt.x - mx;
		dy = pt.y - my;
		GetNativeRenderContext().graphics->SetCursorPosition ({x0-dx, y0-dy});
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

namespace orbiter::production {
bool HandleCockpitStepFov(const Keymap& keymap,UInt32& key,char* kstate) {
    auto* g_camera=GetNativeRenderContext().camera;
    auto SetFOV=[](double value){GetCameraServices().SetFOV(value);};
    if (keymap.IsLogicalKey(key, kstate, OAPI_LKEY_StepIncFOV)) {
        SetFOV(ceil((g_camera->Aperture() * DEG + 1e-6) / 5.0) * 5.0 * RAD);
        return true;
    }
    if (keymap.IsLogicalKey(key, kstate, OAPI_LKEY_StepDecFOV)) {
        SetFOV(floor((g_camera->Aperture() * DEG - 1e-6) / 5.0) * 5.0 * RAD);
        return true;
    }
    return false;
}
}
