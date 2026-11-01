// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_MESH_TYPES_H
#define ORBITER_PRODUCTION_MESH_TYPES_H
#include "CoreTypes.h"
#include "OrbiterMeshData.h"
#include <cmath>
namespace orbiter::production {
struct MeshVector3 { float x,y,z; };
struct MeshTransform4 {
    float _11,_12,_13,_14,_21,_22,_23,_24,_31,_32,_33,_34,_41,_42,_43,_44;
};
inline void NormalizeMeshVector(MeshVector3& v)
{
    const float length=(float)sqrt(v.x*v.x + v.y*v.y + v.z*v.z);
    const float inverse=1.0f/length;
    v.x*=inverse; v.y*=inverse; v.z*=inverse;
}
struct MeshGroupRequest {
    NTVERTEX* Vtx; UInt32 nVtx; UInt16* VtxPerm; UInt16* Idx;
    UInt32 nIdx; UInt16* IdxPerm; UInt32 MtrlIdx,TexIdx;
};
struct MeshGroupEdit {
    UInt32 flags,UsrFlag; NTVERTEX* Vtx; UInt32 nVtx; UInt16* vIdx;
};
constexpr UInt32 MeshExtraTextures=1;
}
#endif
