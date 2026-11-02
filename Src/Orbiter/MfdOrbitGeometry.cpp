// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "MfdOrbitGeometry.h"

using namespace std;

// =======================================================================
// local utility functions

Matrix RotMatrix (double coso, double sino, double cosp, double sinp, double cosi, double sini)
{
	return Matrix (
		cosp*coso-sinp*cosi*sino, sinp*sini,-cosp*sino-sinp*cosi*coso,
		sini*sino,                cosi,      sini*coso,
		sinp*coso+cosp*cosi*sino,-cosp*sini,-sinp*sino+cosp*cosi*coso);
}

// =======================================================================

Matrix IRotMatrix (double cosp, double sinp, double cosi, double sini)
{
	return Matrix (
		cosp*cosp+sinp*sinp*cosi, -sinp*sini, cosp*sinp-sinp*cosp*cosi,
		sinp*sini,                 cosi,     -cosp*sini,
		sinp*cosp-cosp*sinp*cosi,  cosp*sini, sinp*sinp+cosp*cosp*cosi);
}

// =======================================================================

void UpdateEllipse (int cntx, int cnty, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *p)
{
	int i;
	int idx1 = ELN-1, idx2 = 2*ELNQ, idx3 = idx2-1;
	Vector tmp, v[ELN];
	double phi, sphi, cphi, r, x, y;
	double fac = Pi05/(double)ELNQ;
	double e2 = el->e * el->e;

	for (i = 0; i < ELNQ; i++) {
		phi = (i+0.5)*fac; sphi = sin(phi), cphi = cos(phi);
		r = el->SMi() / sqrt (1.0 - e2*cphi*cphi);
		x = r*cphi, y = r*sphi;
		v[i].x      = v[idx1-i].x =  x - el->LinEcc();
		v[i].z      = v[idx3-i].z =  y;
		v[idx3-i].x = v[idx2+i].x = -x - el->LinEcc();
		v[idx2+i].z = v[idx1-i].z = -y;
	}
	for (i = 0; i < ELN; i++)
		MapScreen (cntx, cnty, scale, mul (rot, v[i]), p+i);
	MapScreen (cntx, cnty, scale, mul (irot, el->RVec()), p+ELN);  // radius vector
	p[ELN+1].x = (p[0].x + p[ELN-1].x)/2;       // periapsis
	p[ELN+1].y = (p[0].y + p[ELN-1].y)/2;
	p[ELN+2].x = (p[ELNH-1].x + p[ELNH].x)/2;   // apoapsis
	p[ELN+2].y = (p[ELNH-1].y + p[ELNH].y)/2;
	el->AscendingNode (tmp);                    // ascending node
	MapScreen (cntx, cnty, scale, mul (irot, tmp), p+(ELN+3));
	el->DescendingNode (tmp);                   // descending node
	MapScreen (cntx, cnty, scale, mul (irot, tmp), p+(ELN+4));
}

// =======================================================================

void UpdateHyperbola (int cntx, int cnty, int IW, int IH, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *pt)
{
	if (isnan(scale) || scale == 0) return;

	int i;
	int idx = ELNH-1;
	Vector asc, desc, v[ELN-1];
	double phi, cphi, sphi, r, x, y, len = 1;
	double p = el->PeDist()*(1.0+el->e); // parameter of polar equation
	double radmax = 1.5*cntx/scale;
	double phimax = acos ((p/radmax - 1.0)/el->e);
	double fac = phimax/(double)(ELNH-1);
	bool ascok, descok;

	// periapsis
	v[idx].x = el->PeDist(); v[idx].y = 0.0;

	for (i = 1; i < ELNH; i++) {
		phi = i*fac; sphi = sin(phi), cphi = cos(phi);
		r = p / (1.0 + el->e * cphi);
		x = r*cphi, y = r*sphi;
		v[idx-i].x =   v[idx+i].x = x;
		v[idx-i].z = -(v[idx+i].z = y);
	}
	for (i = 0; i < ELN-1; i++)
		MapScreen (cntx, cnty, scale, mul (rot, v[i]), pt+i);

	for (i = 1; i < ELNH; i++) {
		// do some clipping. Leaving this to the renderer can cause problems in extreme cases
		if (pt[idx+i].x < -10*IW || pt[idx+i].x >= 11*IW || pt[idx+i].y < -10*IH || pt[idx+i].y >= 11*IH)
			pt[idx+i].x = pt[idx+i-1].x,  pt[idx+i].y = pt[idx+i-1].y;
		if (pt[idx-i].x < -10*IW || pt[idx-i].x >= 11*IW || pt[idx-i].y < -10*IH || pt[idx-i].y >= 11*IH)
			pt[idx-i].x = pt[idx-i+1].x,  pt[idx-i].y = pt[idx-i+1].y;
	}

	MapScreen (cntx, cnty, scale, mul (irot, el->RVec()), pt+ELN);  // radius vector
	pt[ELN+1].x = pt[idx].x;               // periapsis
	pt[ELN+1].y = pt[idx].y;
	pt[ELN+2].x = -1;                      // apoapsis - mark invalid
	if (ascok = el->AscendingNode (asc)) {               // ascending node
		if ((len = asc.length()) > radmax) asc *= (radmax/len);
		MapScreen (cntx, cnty, scale, mul (irot, asc), pt+(ELN+3));
	}
	if (descok = el->DescendingNode (desc)) {              // descending node
		if ((len = desc.length()) > radmax) desc *= (radmax/len);
		MapScreen (cntx, cnty, scale, mul (irot, desc), pt+(ELN+4));
	}
	if (!ascok) {
		asc = desc * -(radmax/len);
		MapScreen (cntx, cnty, scale, mul (irot, asc), pt+(ELN+3));
	} else if (!descok) {
		desc = asc * -(radmax/len);
		MapScreen (cntx, cnty, scale, mul (irot, desc), pt+(ELN+4));
	}
}

// =======================================================================

void UpdateOrbitGraph (int cntx, int cnty, int IW, int IH, double scale,
	const Elements *el, const Matrix &rot, const Matrix &irot, oapi::IVECTOR2 *p)
{
	if (el->e < 1.0) UpdateEllipse (cntx, cnty, scale, el, rot, irot, p);
	else             UpdateHyperbola (cntx, cnty, IW, IH, scale, el, rot, irot, p);
}
