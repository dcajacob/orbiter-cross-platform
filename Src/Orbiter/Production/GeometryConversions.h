// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_GEOMETRY_CONVERSIONS_H
#define ORBITER_PRODUCTION_GEOMETRY_CONVERSIONS_H
#include "Vecmat.h"
#include "OrbiterVectorMath.h"

// conversion between Vector and VECTOR3 structures

inline Vector MakeVector (const VECTOR3 &v)
{ return Vector(v.x, v.y, v.z); }

inline VECTOR3 MakeVECTOR3 (const Vector &v)
{ return _V(v.x, v.y, v.z); }

inline VECTOR4 MakeVECTOR4 (const Vector &v)
{ return _V(v.x, v.y, v.z, 1.0); }

inline void CopyVector (const VECTOR3 &v3, Vector &v)
{ v.x = v3.x, v.y = v3.y, v.z = v3.z; }

inline void CopyVector (const Vector &v, VECTOR3 &v3)
{ v3.x = v.x, v3.y = v.y, v3.z = v.z; }

inline void EulerAngles (const Matrix &R, Vector &e)
{
	e.x = atan2 (R.m23, R.m33);
	e.y = -asin (R.m13);
	e.z = atan2 (R.m12, R.m11);
}

inline void EulerAngles (const Matrix &R, VECTOR3 &e)
{
	e.x = atan2 (R.m23, R.m33);
	e.y = -asin (R.m13);
	e.z = atan2 (R.m12, R.m11);
}

#endif
