// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "SurfaceNavigation.h"
#include "Vecmat.h"
#include "OrbiterCelestialData.h"

void Orthodome (double lng1, double lat1, double lng2, double lat2,
				double &dist, double &dir)
{
	double A = lng2-lng1;
	double dlng = fabs(A);
	double dlat = fabs(lat2-lat1);
	if (dlat < 1e-14) {
		dist = dlng;
		dir = (lng2 > lng1 ? PI05 : 3*PI05);
		return;
	} else if (dlng < 1e-14) {
		dist = dlat;
		dir = (lat2 > lat1 ? 0.0 : PI);
	} else {
		double sinA  = sin(A),    cosA  = cos(A);
		double slat1 = sin(lat1), clat1 = cos(lat1);
		double slat2 = sin(lat2), clat2 = cos(lat2);
		double cosa  = slat2*slat1 + clat2*clat1*cosA;
		dist = acos (cosa);
		dir = atan2 (sinA*clat2, clat1*slat2 - slat1*clat2*cosA);
		if (dir < 0.0) dir += Pi2;     // 0 <= dir < 2pi
	}
}

double Orthodome (double lng1, double lat1, double lng2, double lat2)
{
	double cosA  = cos(lng2-lng1);
	double slat1 = sin(lat1), clat1 = cos(lat1);
	double slat2 = sin(lat2), clat2 = cos(lat2);
	double cosa  = slat2*slat1 + clat2*clat1*cosA;
	return acos (cosa);
}
