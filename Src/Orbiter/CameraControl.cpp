// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#define OAPI_IMPLEMENTATION
#include "CamAPI.h"

ExternalCameraControl::ExternalCameraControl (oapi::UInt32 dmode, oapi::UInt32 cmode)
{
	SetDataMode (dmode);
	SetCameraMode (cmode);
	// set default VC parameters
	vcmode.trackrotation = true;
	vcmode.trackposition = true;
	vcmode.freezeonmouse = false;
	vcmode.rotationrange = PI;
	vcmode.positionrange = 0.5;
	vcmode.freeze_t = 1.0;
	// set default track parameters
	trkmode.trackrotation = true;
	trkmode.trackzoom = true;
	trkmode.rotationdata = TrackMode::BYROTATION;
	trkmode.deadzone = 0.2;
	trkmode.speed = 2.0;
}

void ExternalCameraControl::SetDataMode (oapi::UInt32 mode)
{
	datamode = mode & 0x2F;
}

oapi::UInt32 ExternalCameraControl::GetDataMode () const
{
	return datamode;
}

void ExternalCameraControl::SetCameraMode (oapi::UInt32 mode)
{
	cameramode = mode & 0x1F;
}

oapi::UInt32 ExternalCameraControl::GetCameraMode () const
{
	return cameramode;
}
