// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#define STRICT 1
#define OAPI_IMPLEMENTATION
#include "CamAPI.h"
#include "Camera.h"

extern Camera *g_camera;

// ======================================================================
// class ExternalCameraControl

// ======================================================================
// External control registration

DLLEXPORT bool oapiRegisterExternalCameraControl (ExternalCameraControl *ecc)
{
	return (g_camera ? g_camera->RegisterExternalControl (ecc) : false);
}

DLLEXPORT bool oapiUnregisterExternalCameraControl ()
{
	return (g_camera ? g_camera->UnregisterExternalControl () : false);
}