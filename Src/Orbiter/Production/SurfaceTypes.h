// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SURFACE_TYPES_H
#define ORBITER_PRODUCTION_SURFACE_TYPES_H
#include "CoreTypes.h"
#include "Export.h"
#include "OrbiterMeshData.h"
#ifdef _WIN32
#include "D3dmath.h"
#include "D3d7util.h"
#endif
namespace orbiter::production {
using SurfaceScalar=float;
using SurfaceName=std::int64_t;
#ifdef _WIN32
using SurfaceVector=D3DVECTOR;
using SurfacePoint=VERTEX_XYZ;
using SurfacePoint2=VECTOR2D;
using SurfaceTextureVertex=POSTEXVERTEX;
using SurfaceMaterial=D3DMATERIAL7;
#else
struct SurfaceVector {float x,y,z;};
struct SurfacePoint {float x,y,z;};
struct SurfacePoint2 {float x,y;};
struct SurfaceTextureVertex {float x,y,z,tu,tv;};
using SurfaceMaterial=MATERIAL;
#endif
static_assert(sizeof(SurfaceName)==8 && sizeof(SurfaceVector)==12 && sizeof(SurfaceTextureVertex)==20);
}
ORBITER_PRODUCTION_API orbiter::production::SurfaceName NameToId(const char* name);
#endif
