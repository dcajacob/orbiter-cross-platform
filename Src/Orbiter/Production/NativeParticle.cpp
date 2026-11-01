// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original production particle attachment state; no numerical replacement.
#include "NativeParticle.h"
using namespace oapi;
ParticleStream::ParticleStream (orbiter::production::NativeGraphics *_gc, PARTICLESTREAMSPEC *pss)
{
	gc = _gc;
	level = NULL;
	hRef = NULL;
	lpos = _V(0,0,0);  pos = &lpos;
	ldir = _V(0,0,0);  dir = &ldir;
}

ParticleStream::~ParticleStream ()
{
	if (hRef) // stream is being deleted while still attached
		orbiter::production::RenderDetachParticle(hRef,this);
		// notify vessel
}

void ParticleStream::Attach (OBJHANDLE hObj, const VECTOR3 *ppos, const VECTOR3 *pdir, const double *srclvl)
{
	hRef = hObj;
	SetVariablePos (ppos);
	SetVariableDir (pdir);
	SetLevelPtr (srclvl);
}

void ParticleStream::Attach (OBJHANDLE hObj, const VECTOR3 &_pos, const VECTOR3 &_dir, const double *srclvl)
{
	hRef = hObj;
	SetFixedPos (_pos);
	SetFixedDir (_dir);
	SetLevelPtr (srclvl);
}

void ParticleStream::Detach ()
{
	level = NULL;
	hRef = NULL;
	pos = &lpos;
	dir = &ldir;
}

void ParticleStream::SetFixedPos (const VECTOR3 &_pos)
{
	lpos = _pos;  pos = &lpos;
}

void ParticleStream::SetFixedDir (const VECTOR3 &_dir)
{
	ldir = _dir;  dir = &ldir;
}

void ParticleStream::SetVariablePos (const VECTOR3 *ppos)
{
	pos = ppos;
}

void ParticleStream::SetVariableDir (const VECTOR3 *pdir)
{
	dir = pdir;
}

void ParticleStream::SetLevelPtr (const double *srclvl)
{
	level = srclvl;
}
