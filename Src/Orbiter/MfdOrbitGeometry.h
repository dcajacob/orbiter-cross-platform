// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef ORBITER_MFD_ORBIT_GEOMETRY_H
#define ORBITER_MFD_ORBIT_GEOMETRY_H
#include "Element.h"
#include "DrawAPI.h"

#define ELN 256           // polygon resolution for orbit trajectory
#define ELNH (ELN/2)
#define ELNQ (ELN/4)

// =======================================================================
// local prototypes

Matrix RotMatrix (double coso, double sino, double cosp, double sinp, double cosi, double sini);
Matrix IRotMatrix (double cosp, double sinp, double cosi, double sini);
// rotation and inverse rotation matrices for mapping an orbit
// into a plane

void UpdateEllipse (int cntx, int cnty, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *p);
// generate polygon for orbit ellipse display given orbital elements
// and projection matrices

void UpdateHyperbola (int cntx, int cnty, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *p);
// generate polygon for orbit hyperbola display given orbital elements
// and projection matrices

void UpdateOrbitGraph (int cntx, int cnty, int IW, int IH, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *p);
// generate polygon for general conical section (ellipse or hyperbola)
// given orbital elements and projection matrices

inline void MapScreen (int cntx, int cnty, double scale, const Vector &v, oapi::IVECTOR2 *p)
{
	// map logical point into instrument coords
	p->x = cntx + (int)(v.x*scale);
	p->y = cnty - (int)(v.z*scale);
}

inline bool PointInView (int IW, int IH, oapi::IVECTOR2 *p)
{
	return (p->x >= 0 && p->y >= 0 && p->x < IW && p->y < IH);
}

#endif
