// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_MESH_NORMALS_H
#define ORBITER_PRODUCTION_MESH_NORMALS_H
#include <cmath>
#include <cstdint>
namespace orbiter::production {
struct NormalVector { float x, y, z; };
inline NormalVector NormalCrossProduct(const NormalVector& v1, const NormalVector& v2)
{
    NormalVector result;
    result.x = v1.y * v2.z - v1.z * v2.y;
    result.y = v1.z * v2.x - v1.x * v2.z;
    result.z = v1.x * v2.y - v1.y * v2.x;
    return result;
}
inline float NormalLength(const NormalVector& v)
{
    return (float)sqrt(v.x*v.x + v.y*v.y + v.z*v.z);
}
template<class Vertex>
void CalculateMeshNormals(Vertex* vtx, const std::uint16_t* idx,
    int nv, int nt, bool missingonly)
{
	const float eps = 1e-8f;
	int i;
	bool *calcNml = new bool[nv];
	if (missingonly) {
		for (i = 0; i < nv; i++) {
			if (vtx[i].nx*vtx[i].nx + vtx[i].ny*vtx[i].ny + vtx[i].nz*vtx[i].nz > 0.1f) {
				calcNml[i] = false; // flag for "leave normal alone"
			} else {
				calcNml[i] = true;
				vtx[i].nx = vtx[i].ny = vtx[i].nz = 0.0f;
			}
		}
	} else {
		for (i = 0; i < nv; i++) {
			calcNml[i] = true;
			vtx[i].nx = vtx[i].ny = vtx[i].nz = 0.0f;
		}
	}
	for (i = 0; i < nt; i++) {
		std::uint32_t i0 = idx[i*3], i1 = idx[i*3+1], i2 = idx[i*3+2];
		if (!calcNml[i0] && !calcNml[i1] && !calcNml[i2])
			continue; // nothing to do for this triangle
		NormalVector V01 = { vtx[i1].x - vtx[i0].x, vtx[i1].y - vtx[i0].y, vtx[i1].z - vtx[i0].z };
		NormalVector V02 = { vtx[i2].x - vtx[i0].x, vtx[i2].y - vtx[i0].y, vtx[i2].z - vtx[i0].z };
		NormalVector V12 = { vtx[i2].x - vtx[i1].x, vtx[i2].y - vtx[i1].y, vtx[i2].z - vtx[i1].z };
		NormalVector nm = NormalCrossProduct (V01, V02);
		float len = NormalLength (nm);

		if (len >= eps) {
			nm.x /= len, nm.y /= len, nm.z /= len;
			float d01 = NormalLength(V01);
			float d02 = NormalLength(V02);
			float d12 = NormalLength(V12);
			if (calcNml[i0]) {
				float a0 = acos((d01 * d01 + d02 * d02 - d12 * d12) / (2.0f * d01 * d02));
				vtx[i0].nx += nm.x * a0, vtx[i0].ny += nm.y * a0, vtx[i0].nz += nm.z * a0;
			}
			if (calcNml[i1]) {
				float a1 = acos((d01 * d01 + d12 * d12 - d02 * d02) / (2.0f * d01 * d12));
				vtx[i1].nx += nm.x * a1, vtx[i1].ny += nm.y * a1, vtx[i1].nz += nm.z * a1;
			}
			if (calcNml[i2]) {
				float a2 = acos((d02 * d02 + d12 * d12 - d01 * d01) / (2.0f * d02 * d12));
				vtx[i2].nx += nm.x * a2, vtx[i2].ny += nm.y * a2, vtx[i2].nz += nm.z * a2;
			}
		}
	}
	for (i = 0; i < nv; i++)
		if (calcNml[i]) {
			NormalVector nm = { vtx[i].nx, vtx[i].ny, vtx[i].nz };
			float len = NormalLength(nm);
			vtx[i].nx /= len, vtx[i].ny /= len, vtx[i].nz /= len;
		}
	delete []calcNml;
	calcNml = NULL;
}

}
#endif
