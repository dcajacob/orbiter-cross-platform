// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// Implementation of class Body

#include "Body.h"
#include "ConfigFile.h"
#ifdef ORBITER_REFERENCE_MATH
#include "Production/Math/Runtime.h"
#endif
#include <fstream>
#include <string.h>

using namespace std;
using orbiter::production::GetBodyServices;

// =======================================================================
// class Body

Body::Body ()
{
	s0 = sv;
	s1 = (GetBodyServices().IsUpdating() ? sv + 1 : sv);
	updcount = irand(100); // spread update times
	s0->R = IMatrix();       // align body with its parent's orientation
}

Body::Body (double _mass, double _size)
	: Body()
{
	mass = _mass;
	size = _size;
}

Body::Body(char* fname)
	: Body()
{
	const auto path = GetBodyServices().ConfigPath(fname);
	const auto pathString = path.string();
	const char *cpath = pathString.c_str();

	GetBodyServices().LoadStatus(cpath, 1);

	ifstream ifs (path);
	if (!ifs) return;
	
	filename = cpath;

	char cbuf[256], *_name = 0;
	if (GetItemString (ifs, "Name", cbuf)) _name = cbuf;
	SetName (_name);

	if (!GetItemReal (ifs, "Mass", mass)) mass = 1.0; // desperate default
	if (!GetItemReal (ifs, "Size", size)) size = 1.0; // desperate default

	if (!GetItemVector (ifs, "AlbedoRGB", albedo)) albedo.Set (1,1,1);

	GetItemVector (ifs, "InitPos", s0->pos);
	GetItemVector (ifs, "InitVel", s0->vel);

	rpos_base.Set (s0->pos); rpos_add.Set (0,0,0);
	rvel_base.Set (s0->vel); rvel_add.Set (0,0,0);
}

void Body::SetName (char *_name)
{
	static int noname = 0;
	if (!_name) name = "obj" + std::to_string(++noname);
	else name = _name;
}

void Body::SetSize (double newsize)
{
	size = newsize;
	GetBodyServices().SizeChanged(this);
}

void Body::RPlace (const Vector &rpos, const Vector &rvel)
{
	// should RPlace be allowed outside update phase?
	s1->pos = rpos_base = rpos;
	rpos_add.Set (0,0,0);
	s1->vel = rvel_base = rvel;
	rvel_add.Set (0,0,0);
}

void Body::SetRPos (const Vector &p)
{
#if defined(_DEBUG) || !defined(NDEBUG)
	GetBodyServices().CheckUpdateState(s1 != s0);
#endif
	rpos_base = s1->pos = p;
	rpos_add.Set (0,0,0);
}

void Body::AddRPos (const Vector &dp) {
	rpos_base += dp;
	s1->pos = rpos_base + rpos_add;
}

void Body::FlushRPos ()
{
	rpos_base = s1->pos;
	rpos_add.Set(0,0,0);
}

void Body::SetRVel (const Vector &v)
{
#if defined(_DEBUG) || !defined(NDEBUG)
	GetBodyServices().CheckUpdateState(s1 != s0);
#endif
	rvel_base = s1->vel = v;
	rvel_add.Set (0,0,0);
}

void Body::AddRVel (const Vector &dv)
{
#if defined(_DEBUG) || !defined(NDEBUG)
	GetBodyServices().CheckUpdateState(s1 != s0);
#endif
	rvel_base += dv;
	s1->vel = rvel_base + rvel_add;
}

void Body::FlushRVel ()
{
	rvel_base = s1->vel;
	rvel_add.Set(0,0,0);
}

void Body::LocalToEquatorial (const Vector &loc, double &lng, double &lat, double &rad) const
{
	rad = loc.length();
	//loc *= 1.0/rad;
	lng = atan2 (loc.z, loc.x);
#ifdef ORBITER_REFERENCE_MATH
	lat = orbiter::production::ReferenceLatitudeAsin(loc.y / rad);
#else
	lat = asin  (loc.y / rad);
#endif
	//lat = atan  (loc.y / hypot (loc.x, loc.z));
}

bool Body::SurfpointVisible (double lng, double lat, const Vector &gcam) const
{
	Vector sp;
	EquatorialToGlobal (lng, lat, size, sp);
	return (dotp (sp-GPos(), gcam-sp) >= 0.0);
}

void Body::BroadcastVisMsg (orbiter::production::BodyParameter msg, orbiter::production::BodyContent content)
{
	if (hVis) GetBodyServices().VisualEvent(this, hVis, msg, content);
}

void Body::BeginStateUpdate ()
{
	// enable the update state
	s1 = (s0 == sv ? sv + 1 : sv);
}

void Body::EndStateUpdate ()
{
	// disable the update state, to avoid it being addressed outside the update phase
	s1 = s0 = (s0 == sv ? sv + 1 : sv);
}
