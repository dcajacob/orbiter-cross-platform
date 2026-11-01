// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// Implementation of class StarSpec

#include <fstream>
#include "Star.h"
using namespace std;
using namespace orbiter::production;

Star::Star (double _mass, double _mean_radius)
: CelestialBody (_mass, _mean_radius)
{
	Setup ();
}

Star::Star (char *fname)
: CelestialBody (fname)
{
	ifstream ifs (GetBodyServices().ConfigPath(fname));
	if (!ifs) return;
	bDynamicPosVel = false;
	// read star-specific parameters here
	InitDeviceObjects ();
	Setup ();
}

Star::~Star ()
{
	DestroyDeviceObjects ();
}

void Star::Setup ()
{
	CelestialBody::Setup ();
	ExternPosition(); // try to init from module
}

void Star::Update (bool force)
{
	if (bDynamicPosVel || GetCelestialServices().HasModule(*this) && GetCelestialServices().HasEphemeris(*this))
		CelestialBody::Update (force);
	// otherwise don't update: keep star in the origin
	// of the global coordinate system
}

Vector Star::Pos2Barycentre (Vector &pos)
{
	// by definition, the barycentre of stars (root objects) is the origin
	return Vector();
}

Vector4 Star::GetLightColor ()
{
	return {1,1,1,1};
}
