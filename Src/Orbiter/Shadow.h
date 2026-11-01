// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __SHADOW_H
#define __SHADOW_H

#include "Production/SurfaceTypes.h"
using orbiter::production::UInt32;
using orbiter::production::UInt16;
using orbiter::production::SurfacePoint2;

ORBITER_PRODUCTION_API void Find2DConvexHull( UInt32 dwNumInVertices, SurfacePoint2* pInVertices,
					   UInt32* pdwNumOutIndices, UInt16** ppOutIndices );

#endif // !__SHADOW_H