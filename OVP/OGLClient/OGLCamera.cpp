// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//   ORBITER VISUALISATION PROJECT (OVP)
//   D3D7 Client module
// ==============================================================

// ==============================================================
// Camera.cpp
// Class Camera (implementation)
//
// The camera defines the observer position in the 3D world.
// Each scene consists of a camera and a collection of vObjects
// within visual range around it.
// The "render space" (i.e. the coordinate system in which the
// camera and visual objects live) is translated against the
// "global frame" in which orbiter's logical objects live, such
// that the camera is always at the origin. Global and render
// space have however the same orientation.
// ==============================================================

#include "OGLCamera.h"
#include "OrbiterAPI.h"
#include <glm/gtc/type_ptr.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include "OGLClient.h"

OGLCamera::OGLCamera (uint32_t w, uint32_t h)
{
	width = w, height = h;
	aspect = (double)w/(double)h;

	nearplane = 0.1f;
	farplane = 1e11f;

	mView = glm::fmat4(1.0f);
	SetAperture (RAD*50.0);
	UpdateProjectionMatrix();
}

void OGLCamera::SetSize(uint32_t w, uint32_t h)
{
	width = w, height = h;
	aspect = (double)w/(double)h;
	UpdateProjectionMatrix();
}

void OGLCamera::UpdateProjectionMatrix()
{
	mProj = glm::perspective (2*fov, aspect, nearplane, farplane);
	mViewProj = mProj * mView;
}

void OGLCamera::SetAperture (double _ap)
{
	fov = _ap; // Orbiter aperture is half the vertical field of view.
	tanap = tan(_ap);
	UpdateProjectionMatrix ();
}

void OGLCamera::Update ()
{
	if (fov != oapiCameraAperture())
		SetAperture (oapiCameraAperture());

	VECTOR3 vec;
	oapiCameraGlobalPos (&vec);
	gpos.x = vec.x;
	gpos.y = vec.y;
	gpos.z = vec.z;

	oapiCameraGlobalDir (&vec);
	gdir.x = vec.x;
	gdir.y = vec.y;
	gdir.z = vec.z;
	MATRIX3 mat;
	oapiCameraRotationMatrix (&mat);
	// Explicit row/column conversion; preserve public MATRIX3 storage.
    grot = glm::dmat3(mat.m11,mat.m21,mat.m31,mat.m12,mat.m22,mat.m32,mat.m13,mat.m23,mat.m33);
    mView = glm::scale(glm::mat4(1),glm::vec3(1,1,-1))*glm::mat4(glm::transpose(grot));
	mViewProj = mProj * mView;

	// note: in render space, the camera is always placed at the origin,
	// so that render coordinates are precise in the vicinity of the
	// observer (before they are translated into D3D single-precision
	// format). However, the orientation of the render space is the same
	// as orbiter's global coordinate system. Therefore there is a
	// translational transformation between orbiter global coordinates
	// and render coordinates.

	// find the planet closest to the current camera position
	double d, r, alt, ralt, ralt_proxy = 1e100;
	int i, n = oapiGetGbodyCount();
	VECTOR3 ppos;
	for (i = 0; i < n; i++) {
		OBJHANDLE hObj = oapiGetGbodyByIndex (i);
		oapiGetGlobalPos (hObj, &ppos);
		r = oapiGetSize(hObj);
		d = dist(gpos, ppos);
		alt = d - r;
		ralt = alt/r;
		if (ralt < ralt_proxy) {
			ralt_proxy = ralt;
			alt_proxy = alt;
			hObj_proxy = hObj;
		}
	}
}

static bool Vector3Matrix4Multiply (glm::fvec3 *res, const glm::fvec3 *v, const glm::fmat4 &mat)
{
    float x = v->x* mat[0][0] + v->y*mat[1][0] + v->z* mat[2][0] + mat[3][0];
    float y = v->x* mat[0][1] + v->y*mat[1][1] + v->z* mat[2][1] + mat[3][1];
    float z = v->x* mat[0][2] + v->y*mat[1][2] + v->z* mat[2][2] + mat[3][2];
    float w = v->x* mat[0][3] + v->y*mat[1][3] + v->z* mat[2][3] + mat[3][3];

    if (fabs (w) < 1e-5f) return false;

    res->x = x/w;
    res->y = y/w;
    res->z = z/w;
    return true;
}

bool OGLCamera::Direction2Viewport(const VECTOR3 &dir, int &x, int &y)
{
	glm::vec3 homog;
	glm::vec3 idir = {-dir.x, -dir.y, -dir.z};
	if(!Vector3Matrix4Multiply (&homog, &idir, mViewProj))
		return false;

	if (homog.x >= -1.0f && homog.y <= 1.0f && homog.z >= 0.0) {
		if (std::hypot(homog.x, homog.y) < 1e-6) {
			x = width/2, y = height/2;
		} else {
			x = (int)(width*0.5f*(1.0f+homog.x));
			y = (int)(height*0.5f*(1.0f-homog.y));
		}
		return true;
	} else
		return false;
}
