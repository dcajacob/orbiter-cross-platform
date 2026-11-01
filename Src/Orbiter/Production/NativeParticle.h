// Licensed under the MIT License
#pragma once
#include "NativeGraphics.h"
namespace oapi {
// Original production particle attachment state; GPU simulation remains in the
// shared OpenGL Particle.cpp implementation.
class ORBITER_PRODUCTION_API ParticleStream {
public:
    ParticleStream(orbiter::production::NativeGraphics*,PARTICLESTREAMSPEC*);
    ~ParticleStream();
    void Attach(OBJHANDLE,const VECTOR3*,const VECTOR3*,const double*);
    void Attach(OBJHANDLE,const VECTOR3&,const VECTOR3&,const double*);
    void Detach();void SetFixedPos(const VECTOR3&);void SetFixedDir(const VECTOR3&);
    void SetVariablePos(const VECTOR3*);void SetVariableDir(const VECTOR3*);void SetLevelPtr(const double*);
    const double* Level() const {return level;}
protected:
    orbiter::production::NativeGraphics* gc;const double* level;OBJHANDLE hRef;
    const VECTOR3 *pos,*dir;VECTOR3 lpos,ldir;
};
}
