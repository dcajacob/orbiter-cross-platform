// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "Mesh.h"
#include "Production/MeshReader.h"
#include "Production/MeshNormals.h"
#include <stdio.h>
#include "Vecmat.h"
#include <algorithm>
#include <cstring>
#include <fstream>
#include <cmath>
#include <memory>
using orbiter::production::GetMeshServices;
#define TRACENEW GetMeshServices().allocation(GetMeshServices().context, __FILE__, __LINE__);

using namespace std;

// =======================================================================
// Class Triangle

Triangle::Triangle ()
{
	hasNodes = false;
	hasNormals = false;
}

Triangle::Triangle (const Triangle &tri)
{
	if (hasNodes = tri.hasNodes)
		for (int i = 0; i < 3; i++) nd[i] = tri.nd[i];
	if (hasNormals = tri.hasNormals)
		for (int i = 0; i < 3; i++) nm[i] = tri.nm[i];
}

Triangle::Triangle (int n0, int n1, int n2)
{
	hasNodes = true;
	hasNormals = false;
	nd[0] = n0;
	nd[1] = n1;
	nd[2] = n2;
}

void Triangle::SetNodes (int n0, int n1, int n2)
{
	hasNodes = true;
	nd[0] = n0;
	nd[1] = n1;
	nd[2] = n2;
}

// =======================================================================
// Class Mesh

Mesh::Mesh ()
{
	name = NULL;
	nGrp = nMtrl = nTex = 0;
	GrpVis   = 0;
	GrpSetup = false;
	bModulateMatAlpha = false;
}

Mesh::Mesh (NTVERTEX *vtx, UInt32 nvtx, UInt16 *idx, UInt32 nidx, UInt32 matidx, UInt32 texidx)
{
	name = NULL;
	nGrp = nMtrl = nTex = 0;
	GrpVis   = 0;
	GrpSetup = false;
	AddGroup (vtx, nvtx, idx, nidx, matidx, texidx);
	bModulateMatAlpha = false;
	Setup();
}

Mesh::Mesh (const Mesh &mesh)
{
	name = NULL;
	nGrp = nMtrl = nTex = 0;
	GrpVis = 0;
	GrpSetup = false;
	Set (mesh);
}

void Mesh::Set (const Mesh &mesh)
{
	UInt32 i;

	Clear ();
	if (nGrp = mesh.nGrp) {
		Grp = new GroupSpec[nGrp]; TRACENEW
		memcpy (Grp, mesh.Grp, nGrp*sizeof(GroupSpec));
		for (i = 0; i < nGrp; i++) {
			Grp[i].Vtx = new NTVERTEX[Grp[i].nVtx]; TRACENEW
			memcpy (Grp[i].Vtx, mesh.Grp[i].Vtx, Grp[i].nVtx*sizeof(NTVERTEX));
			Grp[i].Idx = new UInt16[Grp[i].nIdx]; TRACENEW
			memcpy (Grp[i].Idx, mesh.Grp[i].Idx, Grp[i].nIdx*sizeof(UInt16));
		}
	}
	if (nMtrl = mesh.nMtrl) {
		Mtrl = new MATERIAL[nMtrl]; TRACENEW
		memcpy (Mtrl, mesh.Mtrl, nMtrl*sizeof(MATERIAL));
	}
	if (nTex = mesh.nTex) {
		Tex = new MeshSurface[nTex]; TRACENEW
		memcpy (Tex, mesh.Tex, nTex*sizeof(MeshSurface));
		textureSources = mesh.textureSources;
	}
	if (GrpSetup = mesh.GrpSetup) {
		GrpCnt = new MeshVector3[nGrp]; TRACENEW
		memcpy (GrpCnt, mesh.GrpCnt, nGrp*sizeof(MeshVector3));
		GrpRad = new float[nGrp]; TRACENEW
		memcpy (GrpRad, mesh.GrpRad, nGrp*sizeof(float));
		GrpVis = new UInt32[nGrp]; TRACENEW
		memcpy (GrpVis, mesh.GrpVis, nGrp*sizeof(UInt32));
	} else {
		GrpVis = 0;
	}
	SetName(mesh.GetName());
	bModulateMatAlpha = mesh.bModulateMatAlpha;
}

Mesh::~Mesh ()
{
	Clear ();
}

void Mesh::Setup ()
{
	UInt32 g;
	if (GrpVis) { // allocated already
		delete []GrpCnt;
		GrpCnt = NULL;
		delete []GrpRad;
		GrpRad = NULL;
		delete []GrpVis;
		GrpVis = 0;
	}
	GrpCnt  = new MeshVector3[nGrp]; TRACENEW
	GrpRad  = new float[nGrp]; TRACENEW
	GrpVis  = new UInt32[nGrp]; TRACENEW
	GrpSetup = true;
	for (g = 0; g < nGrp; g++) {
		SetupGroup (g);
		// check validity of material/texture indices
		if (Grp[g].MtrlIdx != SPEC_INHERIT && Grp[g].MtrlIdx >= nMtrl) Grp[g].MtrlIdx = SPEC_DEFAULT;
		if (Grp[g].TexIdx != SPEC_INHERIT && Grp[g].TexIdx >= nTex) Grp[g].TexIdx = SPEC_DEFAULT;
	}
}

void Mesh::SetupGroup (UInt32 grp)
{
	UInt32 i;
	float x, y, z, dx, dy, dz, d2, d2max;
	float invtx = (float)(1.0/Grp[grp].nVtx);
	x = y = z = 0.0f;
	for (i = 0; i < Grp[grp].nVtx; i++) {
		x += Grp[grp].Vtx[i].x;
		y += Grp[grp].Vtx[i].y;
		z += Grp[grp].Vtx[i].z;
	}
	GrpCnt[grp].x = (x *= invtx);
	GrpCnt[grp].y = (y *= invtx);
	GrpCnt[grp].z = (z *= invtx);
	d2max = 0.0f;
	for (i = 0; i < Grp[grp].nVtx; i++) {
		dx = x - Grp[grp].Vtx[i].x;
		dy = y - Grp[grp].Vtx[i].y;
		dz = z - Grp[grp].Vtx[i].z;
		d2 = dx*dx + dy*dy + dz*dz;
		if (d2 > d2max) d2max = d2;
	}
	GrpRad[grp] = (float)sqrt (d2max);
}

int Mesh::AddGroup (NTVERTEX *vtx, UInt32 nvtx, UInt16 *idx, UInt32 nidx,
	UInt32 mtrl_idx, UInt32 tex_idx, UInt16 zbias, UInt32 flag, bool deepcopy)
{
	UInt32 n;
	GroupSpec *g, *tmp_Grp = new GroupSpec[nGrp+1]; TRACENEW
	MeshVector3 *tmp_Cnt = new MeshVector3[nGrp+1]; TRACENEW
	float *tmp_Rad = new float[nGrp+1]; TRACENEW
	UInt32 *tmp_Vis = new UInt32[nGrp+1]; TRACENEW
	if (nGrp) {
		memcpy (tmp_Grp, Grp, nGrp*sizeof(GroupSpec));
		memcpy (tmp_Cnt, GrpCnt, nGrp*sizeof(MeshVector3));
		memcpy (tmp_Rad, GrpRad, nGrp*sizeof(float));
		memcpy (tmp_Vis, GrpVis, nGrp*sizeof(UInt32));
		delete []Grp;
		Grp = NULL;
		delete []GrpCnt;
		GrpCnt = NULL;
		delete []GrpRad;
		GrpRad = NULL;
		delete []GrpVis;
		GrpVis = 0;
	}
	Grp = tmp_Grp;
	GrpCnt = tmp_Cnt;
	GrpRad = tmp_Rad;
	GrpVis = tmp_Vis;
	g = Grp+nGrp;
	if (deepcopy) {
		g->Vtx = new NTVERTEX[nvtx]; 
		if (vtx) memcpy (g->Vtx, vtx, nvtx*sizeof(NTVERTEX));
		else     memset (g->Vtx, 0, nvtx*sizeof(NTVERTEX));
		g->Idx = new UInt16[nidx];
		if (idx) memcpy (g->Idx, idx, nidx*sizeof(UInt16));
		else     memset (g->Idx, 0, nidx*sizeof(UInt16));
	} else {
		g->Vtx = vtx;
		g->Idx = idx;
	}
	g->nVtx = nvtx;
	g->nIdx = nidx;
	g->MtrlIdx = mtrl_idx;
	g->TexIdx = tex_idx;
	for (n = 0; n < MeshExtraTextures; n++) {
		g->TexIdxEx[n] = SPEC_DEFAULT;
		g->TexMixEx[n] = 0.0f;
	}
	g->zBias = zbias;
	g->Flags = 0;
	g->UsrFlag = flag;
	if (GrpSetup) {
		SetupGroup (nGrp);
		if (g->MtrlIdx != SPEC_INHERIT && g->MtrlIdx >= nMtrl)
			g->MtrlIdx = SPEC_DEFAULT;
		if (g->TexIdx != SPEC_INHERIT && g->TexIdx >= nTex)
			g->TexIdx = SPEC_DEFAULT;
	}
	return nGrp++;
}

bool Mesh::AddGroupBlock (UInt32 grp, const NTVERTEX *vtx, UInt32 nvtx, const UInt16 *idx, UInt32 nidx)
{
	if (grp >= nGrp) return false;

	GroupSpec *g = Grp+grp;
	UInt16 vofs = (UInt16)g->nVtx;

	NTVERTEX *v = new NTVERTEX[g->nVtx+nvtx];
	if (g->nVtx) {
		memcpy (v, g->Vtx, g->nVtx*sizeof(NTVERTEX));
	}
	delete []g->Vtx;
	g->Vtx = NULL;
	if (nvtx) {
		memcpy (v+g->nVtx, vtx, nvtx*sizeof(NTVERTEX));
	}
	g->Vtx = v;
	g->nVtx += nvtx;

	UInt16 *i = new UInt16[g->nIdx+nidx];
	if (g->nIdx) {
		memcpy (i, g->Idx, g->nIdx*sizeof(UInt16));
	}
	delete []g->Idx;
	g->Idx = NULL;
	if (nidx) {
		for (UInt32 j = 0; j < nidx; j++)
			i[g->nIdx+j] = idx[j] + vofs;
	}
	g->Idx = i;
	g->nIdx += nidx;

	return true;
}

void Mesh::AddMesh (Mesh &mesh)
{
	for (UInt32 i = 0; i < mesh.nGroup(); i++) {
		NTVERTEX *vtx2;
		UInt16 *idx2;
		GroupSpec *gs = mesh.GetGroup (i);
		// need to copy the vertex and index lists
		vtx2 = new NTVERTEX[gs->nVtx];  memcpy (vtx2, gs->Vtx, gs->nVtx*sizeof(NTVERTEX)); TRACENEW
		idx2 = new UInt16[gs->nIdx];      memcpy (idx2, gs->Idx, gs->nIdx*sizeof(UInt16)); TRACENEW
		AddGroup (vtx2, gs->nVtx, idx2, gs->nIdx);
	}
}

bool Mesh::DeleteGroup (UInt32 grp)
{
	if (nGrp == 1) { // delete the only group
		delete []Grp;
		Grp = NULL;
		nGrp = 0;
	} else if (grp < nGrp && grp > 0) { // delete selected group
		if (Grp[grp].Vtx) { delete []Grp[grp].Vtx; Grp[grp].Vtx = NULL; }
		if (Grp[grp].Idx) { delete []Grp[grp].Idx; Grp[grp].Idx = NULL; }

		// redo group
		GroupSpec * tmp_Grp = new GroupSpec[nGrp - 1]; TRACENEW
		for (UInt32 i = 0, j = 0; i < nGrp; i++)
			if (i != grp) tmp_Grp[j++] = Grp[i];
		delete []Grp;
		Grp = tmp_Grp;
		nGrp--;
	} else {
		return false;
	}
	return true;
}

int Mesh::GetGroup (UInt32 grp, MeshGroupRequest *grs)
{
	static NTVERTEX zero = {0,0,0, 0,0,0, 0,0};
	if (grp >= nGrp) return 1;
	GroupSpec *g = Grp+grp;
	UInt32 nv = g->nVtx;
	UInt32 ni = g->nIdx;
	UInt32 i, vi;
	int ret = 0;

	if (grs->nVtx && grs->Vtx) { // vertex data requested
		if (grs->VtxPerm) { // random access data request
			for (i = 0; i < grs->nVtx; i++) {
				vi = grs->VtxPerm[i];
				if (vi < nv) {
					grs->Vtx[i] = g->Vtx[vi];
				} else {
					grs->Vtx[i] = zero;
					ret = 1;
				}
			}
		} else {
			if (grs->nVtx > nv) grs->nVtx = nv;
			memcpy (grs->Vtx, g->Vtx, grs->nVtx * sizeof(NTVERTEX));
		}
	}

	if (grs->nIdx && grs->Idx) { // index data requested
		if (grs->IdxPerm) { // random access data request
			for (i = 0; i < grs->nIdx; i++) {
				vi = grs->IdxPerm[i];
				if (vi < ni) {
					grs->Idx[i] = g->Idx[vi];
				} else {
					grs->Idx[i] = 0;
					ret = 1;
				}
			}
		} else {
			if (grs->nIdx > ni) grs->nIdx = ni;
			memcpy (grs->Idx, g->Idx, grs->nIdx * sizeof(UInt16));
		}
	}

	grs->MtrlIdx = g->MtrlIdx;
	grs->TexIdx = g->TexIdx;
	return ret;
}

int Mesh::EditGroup (UInt32 grp, MeshGroupEdit *ges)
{
	if (grp >= nGrp) return 1;
	GroupSpec *g = Grp+grp;
	UInt32 i, vi;

	UInt32 flag = ges->flags;
	if (flag & orbiter::production::MeshEdit::SETUSERFLAG)
		g->UsrFlag = ges->UsrFlag;
	else if (flag & orbiter::production::MeshEdit::ADDUSERFLAG)
		g->UsrFlag |= ges->UsrFlag;
	else if (flag & orbiter::production::MeshEdit::DELUSERFLAG)
		g->UsrFlag &= ~ges->UsrFlag;

	if (flag & orbiter::production::MeshEdit::VTXMOD) {
		for (i = 0; i < ges->nVtx; i++) {
			vi = (ges->vIdx ? ges->vIdx[i] : i);
			if (vi < g->nVtx) {
				if      (flag & orbiter::production::MeshEdit::VTXCRDX)    g->Vtx[vi].x   = ges->Vtx[i].x;
				else if (flag & orbiter::production::MeshEdit::VTXCRDADDX) g->Vtx[vi].x  += ges->Vtx[i].x;
				if      (flag & orbiter::production::MeshEdit::VTXCRDY)    g->Vtx[vi].y   = ges->Vtx[i].y;
				else if (flag & orbiter::production::MeshEdit::VTXCRDADDY) g->Vtx[vi].y  += ges->Vtx[i].y;
				if      (flag & orbiter::production::MeshEdit::VTXCRDZ)    g->Vtx[vi].z   = ges->Vtx[i].z;
				else if (flag & orbiter::production::MeshEdit::VTXCRDADDZ) g->Vtx[vi].z +=  ges->Vtx[i].z;
				if      (flag & orbiter::production::MeshEdit::VTXNMLX)    g->Vtx[vi].nx  = ges->Vtx[i].nx;
				else if (flag & orbiter::production::MeshEdit::VTXNMLADDX) g->Vtx[vi].nx += ges->Vtx[i].nx;
				if      (flag & orbiter::production::MeshEdit::VTXNMLY)    g->Vtx[vi].ny  = ges->Vtx[i].ny;
				else if (flag & orbiter::production::MeshEdit::VTXNMLADDY) g->Vtx[vi].ny += ges->Vtx[i].ny;
				if      (flag & orbiter::production::MeshEdit::VTXNMLZ)    g->Vtx[vi].nz  = ges->Vtx[i].nz;
				else if (flag & orbiter::production::MeshEdit::VTXNMLADDZ) g->Vtx[vi].nz += ges->Vtx[i].nz;
				if      (flag & orbiter::production::MeshEdit::VTXTEXU)    g->Vtx[vi].tu  = ges->Vtx[i].tu;
				else if (flag & orbiter::production::MeshEdit::VTXTEXADDU) g->Vtx[vi].tu += ges->Vtx[i].tu;
				if      (flag & orbiter::production::MeshEdit::VTXTEXV)    g->Vtx[vi].tv  = ges->Vtx[i].tv;
				else if (flag & orbiter::production::MeshEdit::VTXTEXADDV) g->Vtx[vi].tv += ges->Vtx[i].tv;
			}
		}
	}
	if (GrpSetup) SetupGroup(grp);
	return 0;
}

int Mesh::AddMaterial (MATERIAL &mtrl)
{
	MATERIAL *tmp_Mtrl = new MATERIAL[nMtrl+1]; TRACENEW
	if (nMtrl) memcpy (tmp_Mtrl, Mtrl, sizeof(MATERIAL)*nMtrl);
	memcpy (tmp_Mtrl+nMtrl, &mtrl, sizeof(MATERIAL));
	if (nMtrl) {
		delete []Mtrl;
		Mtrl = NULL;
	}
	Mtrl = tmp_Mtrl;
	return nMtrl++;
}

bool Mesh::DeleteMaterial (UInt32 matidx)
{
	UInt32 i, j;
	if (matidx >= nMtrl) return false;

	// adjust group material indices
	for (i = 0; i < nGrp; i++) {
		if (Grp[i].MtrlIdx >= matidx) {
			if (Grp[i].MtrlIdx == matidx) Grp[i].MtrlIdx = 0;
			else Grp[i].MtrlIdx--;
		}
	}

	// remove material from the list
	MATERIAL *tmp_Mtrl = 0;
	if (nMtrl > 1) {
		tmp_Mtrl = new MATERIAL[nMtrl-1]; TRACENEW
		for (i = j = 0; i < nMtrl; i++) {
			if (i != matidx) memcpy (tmp_Mtrl+j++, Mtrl+i, sizeof(MATERIAL));
		}
	}
	delete []Mtrl;
	Mtrl = tmp_Mtrl;
	nMtrl--;
	return true;
}

void Mesh::Clear ()
{
	for (UInt32 i = 0; i < nGrp; i++) {
		delete []Grp[i].Vtx;
		delete []Grp[i].Idx;
		Grp[i].Vtx = NULL;
		Grp[i].Idx = NULL;
	}
	if (nGrp) {
		delete []Grp;
		Grp = NULL;
		nGrp = 0;
	}
	if (nMtrl) {
		delete []Mtrl;
		Mtrl = NULL;
		nMtrl = 0;
	}
	if (GrpVis) {
		delete []GrpCnt;
		GrpCnt = NULL;
		delete []GrpRad;
		GrpRad = NULL;
		delete []GrpVis;
		GrpVis = 0;
	}
	if (name) {
		delete []name;
		name = NULL;
	}
	GrpSetup = false;
	ReleaseTextures ();
}

void Mesh::ScaleGroup (UInt32 grp, float sx, float sy, float sz)
{
	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	for (i = 0; i < nv; i++) {
		vtx[i].x *= sx;
		vtx[i].y *= sy;
		vtx[i].z *= sz;
	}
	if (sx == sy && sx == sz) return; // no change in normals
	float snx = sy*sz, sny = sx*sz, snz = sx*sy;
	for (i = 0; i < nv; i++) {
		vtx[i].nx *= snx;
		vtx[i].ny *= sny;
		vtx[i].nz *= snz;
		float ilen = (float)(1.0/sqrt (vtx[i].nx*vtx[i].nx + vtx[i].ny*vtx[i].ny + vtx[i].nz*vtx[i].nz));
		vtx[i].nx *= ilen;
		vtx[i].ny *= ilen;
		vtx[i].nz *= ilen;
	}
	if (GrpSetup) SetupGroup (grp);
}

void Mesh::Scale (float sx, float sy, float sz)
{
	for (UInt32 grp = 0; grp < nGrp; grp++)
		ScaleGroup (grp, sx, sy, sz);
}

void Mesh::TranslateGroup (UInt32 grp, float dx, float dy, float dz)
{
	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	for (i = 0; i < nv; i++) {
		vtx[i].x += dx;
		vtx[i].y += dy;
		vtx[i].z += dz;
	}
	if (GrpSetup) {
		GrpCnt[grp].x += dx;
		GrpCnt[grp].y += dy;
		GrpCnt[grp].z += dz;
	}
}

void Mesh::Translate (float dx, float dy, float dz)
{
	for (UInt32 grp = 0; grp < nGrp; grp++)
		TranslateGroup (grp, dx, dy, dz);
}

void Mesh::RotateGroup (UInt32 grp, RotAxis axis, float angle)
{
	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	float cosa = (float)cos(angle), sina = (float)sin(angle);
	switch (axis) {
	case ROTATE_X:
		for (i = 0; i < nv; i++) {
			float y = vtx[i].y, z = vtx[i].z;
			vtx[i].y = cosa*y - sina*z;
			vtx[i].z = sina*y + cosa*z;
			float ny = vtx[i].ny, nz = vtx[i].nz;
			vtx[i].ny = cosa*ny - sina*nz;
			vtx[i].nz = sina*ny + cosa*nz;
		}
		if (GrpSetup) {
			float y = GrpCnt[grp].y, z = GrpCnt[grp].z;
			GrpCnt[grp].y = cosa*y - sina*z;
			GrpCnt[grp].z = sina*y + cosa*z;
		}
		break;
	case ROTATE_Y:
		for (i = 0; i < nv; i++) {
			float x = vtx[i].x, z = vtx[i].z;
			vtx[i].x = cosa*x - sina*z;
			vtx[i].z = sina*x + cosa*z;
			float nx = vtx[i].nx, nz = vtx[i].nz;
			vtx[i].nx = cosa*nx - sina*nz;
			vtx[i].nz = sina*nx + cosa*nz;
		}
		if (GrpSetup) {
			float x = GrpCnt[grp].x, z = GrpCnt[grp].z;
			GrpCnt[grp].x = cosa*x - sina*z;
			GrpCnt[grp].z = sina*x + cosa*z;
		}
		break;
	case ROTATE_Z:
		for (i = 0; i < nv; i++) {
			float x = vtx[i].x, y = vtx[i].y;
			vtx[i].x = cosa*x - sina*y;
			vtx[i].y = sina*x + cosa*y;
			float nx = vtx[i].nx, ny = vtx[i].ny;
			vtx[i].nx = cosa*nx - sina*ny;
			vtx[i].ny = sina*nx + cosa*ny;
		}
		if (GrpSetup) {
			float x = GrpCnt[grp].x, y = GrpCnt[grp].y;
			GrpCnt[grp].x = cosa*x - sina*y;
			GrpCnt[grp].y = sina*x + cosa*y;
		}
		break;
	}
}

void Mesh::Rotate (RotAxis axis, float angle)
{
	for (UInt32 grp = 0; grp < nGrp; grp++)
		RotateGroup (grp, axis, angle);
}

void Mesh::TransformGroup (UInt32 grp, const MeshTransform4 &mat)
{
	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	float x, y, z, w;

	for (i = 0; i < nv; i++) {
		NTVERTEX &v = vtx[i];
		x = v.x*mat._11 + v.y*mat._21 + v.z* mat._31 + mat._41;
		y = v.x*mat._12 + v.y*mat._22 + v.z* mat._32 + mat._42;
		z = v.x*mat._13 + v.y*mat._23 + v.z* mat._33 + mat._43;
		w = v.x*mat._14 + v.y*mat._24 + v.z* mat._34 + mat._44;
    	v.x = x/w;
		v.y = y/w;
		v.z = z/w;

		x = v.nx*mat._11 + v.ny*mat._21 + v.nz* mat._31;
		y = v.nx*mat._12 + v.ny*mat._22 + v.nz* mat._32;
		z = v.nx*mat._13 + v.ny*mat._23 + v.nz* mat._33;
		w = 1.0f/(float)sqrt (x*x + y*y + z*z);
		v.nx = x*w;
		v.ny = y*w;
		v.nz = z*w;
	}
	if (GrpSetup) SetupGroup (grp);
}

void Mesh::Transform (const MeshTransform4 &mat)
{
	for (UInt32 grp = 0; grp < nGrp; grp++)
		TransformGroup (grp, mat);
}

void Mesh::TexScaleGroup (UInt32 grp, float su, float sv)
{
	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	for (i = 0; i < nv; i++) {
		vtx[i].tu *= su;
		vtx[i].tv *= sv;
	}
}

void Mesh::TexScale (float su, float sv)
{
	for (UInt32 grp = 0; grp < nGrp; grp++)
		TexScaleGroup (grp, su, sv);
}

void Mesh::CalcNormals (UInt32 grp, bool missingonly)
{
	orbiter::production::CalculateMeshNormals(Grp[grp].Vtx, Grp[grp].Idx,
		Grp[grp].nVtx, Grp[grp].nIdx/3, missingonly);
}

void Mesh::CalcTexCoords (UInt32 grp)
{
	// quick hack. not globally usable

	int i, nv = Grp[grp].nVtx;
	NTVERTEX *vtx = Grp[grp].Vtx;
	double ipi = 1.0/Pi, i2pi = 0.5/Pi;

	for (i = 0; i < nv; i++) {
		MeshVector3 pos = {vtx[i].x, vtx[i].y, vtx[i].z};
		orbiter::production::NormalizeMeshVector(pos);
		double tht = acos (pos.y);
		double phi = atan2 (pos.z, pos.x);
		vtx[i].tu = (float)(phi >= 0.0 ? phi*i2pi : (phi+Pi2)*i2pi);
		vtx[i].tv = (float)(tht*ipi);
	}
}

int Mesh::AddTexture (MeshSurface tex)
{
	UInt32 i;

	// check if already present
	for (i = 0; i < nTex; i++)
		if (Tex[i] == tex) return i;

	MeshSurface *tmp = new MeshSurface[nTex+1]; TRACENEW
	if (nTex) {
		memcpy (tmp, Tex, nTex*sizeof(MeshSurface));
		delete []Tex;
		Tex = NULL;
	}
	Tex = tmp;
	Tex[nTex] = tex;
	textureSources.resize(nTex+1);
	return nTex++;
}

bool Mesh::SetTexture (UInt32 texidx, MeshSurface tex, bool release_old)
{
	if (texidx >= nTex) return false;  // index out of range
	if (Tex[texidx] && release_old) {
		const auto& services=GetMeshServices();
		services.releaseTexture(services.context, Tex[texidx]);
	}
	Tex[texidx] = tex;
	if (texidx < textureSources.size()) textureSources[texidx] = {};
	return true;
}

void Mesh::ReleaseTextures ()
{
	textureSources.clear();
	if (nTex) {
		for (UInt32 i = 0; i < nTex; i++)
			if (Tex[i]) {
				const auto& services=GetMeshServices();
				services.releaseTexture(services.context, Tex[i]);
			}
		delete []Tex;
		Tex = NULL;
		nTex = 0;
	}
}

void Mesh::SetTexMixture (UInt32 grp, UInt32 ntex, float mix)
{
	if (grp < nGrp && --ntex < MeshExtraTextures && Grp[grp].TexIdxEx[ntex] != SPEC_DEFAULT)
		Grp[grp].TexMixEx[ntex] = mix;
}

void Mesh::SetTexMixture (UInt32 ntex, float mix)
{
	if (--ntex < MeshExtraTextures) {
		for (UInt32 grp = 0; grp < nGrp; grp++)
			if (Grp[grp].TexIdxEx[ntex] != SPEC_DEFAULT)
				Grp[grp].TexMixEx[ntex] = mix;
	}
}

void Mesh::GlobalEnableSpecular (bool enable)
{
	bEnableSpecular = enable;
}

void Mesh::EnableMatAlpha (bool enable)
{
	bModulateMatAlpha = enable;
}

const char* Mesh::GetName() const
{
	return name;
}

void Mesh::SetName(const char* n)
{
	if (n) {
		int len = strlen(n) + 1;
		name = new char[len];
		memcpy(name, n, len);
	}
}

// Host resource adapter for the shared production parser.
class EngineMeshSink {
public:
	using Vertex = NTVERTEX;
	using Index = UInt16;
	using Material = MATERIAL;
	explicit EngineMeshSink(Mesh& value) : mesh(value) {}
	void Clear() { mesh.Clear(); }
	void AddGroup(Vertex* vertices, int nv, Index* indices, int ni,
		UInt32 material, UInt32 texture, UInt16 bias)
	{ mesh.AddGroup(vertices, nv, indices, ni, material, texture, bias); }
	void SetGroupFlags(int group, UInt16 flags, UInt32 user)
	{ mesh.Grp[group].Flags = flags; mesh.Grp[group].UsrFlag = user; }
	void CalcNormals(int group, bool missingOnly) { mesh.CalcNormals(group, missingOnly); }
	void AddMaterial(Material& material) { mesh.AddMaterial(material); }
	void ReleaseTextures() { mesh.ReleaseTextures(); }
	void CreateTextures(int count) { mesh.nTex=count; mesh.Tex = count ? new MeshSurface[count]() : nullptr; mesh.textureSources.resize(count); }
	void LoadTexture(int index, const char* name, UInt32 flags)
	{
		mesh.textureSources.at(index) = {name, static_cast<std::uint32_t>(flags)};
		const auto& services = GetMeshServices();
		mesh.Tex[index] = services.loadTexture(services.context, name, flags);
	}

	void Setup() { mesh.Setup(); }
private:
	Mesh& mesh;
};

istream &operator>> (istream &is, Mesh &mesh)
{
	EngineMeshSink sink(mesh);
	return orbiter::production::ReadMesh(is, sink);
}

ostream &operator<< (ostream &os, const Mesh &mesh)
{
	UInt32 g, i, ntri;

	os << "MSHX1" << endl;
	os << "GROUPS " << mesh.nGrp << endl;
	for (g = 0; g < mesh.nGrp; g++) {
		if (mesh.Grp[g].MtrlIdx != SPEC_INHERIT)
			os << "MATERIAL "
			   << (mesh.Grp[g].MtrlIdx == SPEC_DEFAULT ? 0 : mesh.Grp[g].MtrlIdx+1)
			   << endl;
		if (mesh.Grp[g].TexIdx != SPEC_INHERIT)
			os << "TEXTURE "
			   << (mesh.Grp[g].TexIdx == SPEC_DEFAULT ? 0 : mesh.Grp[g].TexIdx)
			   << endl;
		if (mesh.Grp[g].zBias)
			os << "ZBIAS " << mesh.Grp[g].zBias << endl;
		if (mesh.Grp[g].Flags & 0x03) {
			os << "TEXWRAP ";
			if (mesh.Grp[g].Flags & 0x01) os << 'U';
			if (mesh.Grp[g].Flags & 0x02) os << 'V';
			os << endl;
		}
		if (mesh.Grp[g].UsrFlag)
			os << "FLAG " << hex << mesh.Grp[g].UsrFlag << dec << endl;
		ntri = mesh.Grp[g].nIdx/3;
		os << "GEOM " << mesh.Grp[g].nVtx << ' ' << ntri << endl;
		for (i = 0; i < mesh.Grp[g].nVtx; i++)
			os << mesh.Grp[g].Vtx[i].x << ' '
			   << mesh.Grp[g].Vtx[i].y << ' '
			   << mesh.Grp[g].Vtx[i].z << ' '
			   << mesh.Grp[g].Vtx[i].nx << ' '
			   << mesh.Grp[g].Vtx[i].ny << ' '
			   << mesh.Grp[g].Vtx[i].nz << ' '
			   << mesh.Grp[g].Vtx[i].tu << ' '
			   << mesh.Grp[g].Vtx[i].tv << endl;
		for (i = 0; i < ntri; i++)
			os << mesh.Grp[g].Idx[i*3] << ' '
			   << mesh.Grp[g].Idx[i*3+1] << ' '
			   << mesh.Grp[g].Idx[i*3+2] << endl;
	}
	if (mesh.nMtrl) {
		os << "MATERIALS " << mesh.nMtrl << endl;
		for (i = 0; i < mesh.nMtrl; i++)
			os << "Material" << i << endl; // note: original material names are not preserved
		for (i = 0; i < mesh.nMtrl; i++) {
			os << "MATERIAL Material" << i << endl;
			os << mesh.Mtrl[i].diffuse.r << ' '
			   << mesh.Mtrl[i].diffuse.g << ' '
			   << mesh.Mtrl[i].diffuse.b << ' '
			   << mesh.Mtrl[i].diffuse.a << endl;
			os << mesh.Mtrl[i].ambient.r << ' '
			   << mesh.Mtrl[i].ambient.g << ' '
			   << mesh.Mtrl[i].ambient.b << ' '
			   << mesh.Mtrl[i].ambient.a << endl;
			os << mesh.Mtrl[i].specular.r << ' '
			   << mesh.Mtrl[i].specular.g << ' '
			   << mesh.Mtrl[i].specular.b << ' '
			   << mesh.Mtrl[i].specular.a;
			if (mesh.Mtrl[i].power) os << ' ' << mesh.Mtrl[i].power;
			os << endl;
			os << mesh.Mtrl[i].emissive.r << ' '
			   << mesh.Mtrl[i].emissive.g << ' '
			   << mesh.Mtrl[i].emissive.b << ' '
			   << mesh.Mtrl[i].emissive.a << endl;
		}
	}
	if (mesh.nTex) {
		os << "TEXTURES " << mesh.nTex << endl;
		for (i = 0; i < mesh.nTex; i++)
			os << "0" << endl; // DUMMY - texture names are not preserved!
	}
	return os;
}

bool Mesh::bEnableSpecular = false;

// =======================================================================
// Class MeshManager

MeshManager::MeshManager()
{
	nmlist = nmlistbuf = 0;
}

MeshManager::~MeshManager()
{
	Flush();
}

void MeshManager::Flush()
{
	for (int i = 0; i < nmlist; i++)
		delete mlist[i].mesh;
	if (nmlistbuf) {
		delete []mlist;
		nmlist = nmlistbuf = 0;
	}
}

const Mesh *MeshManager::LoadMesh (const char *fname, bool *firstload)
{
	int i;
	UInt64 crc = Str2Crc (fname);
	for (i = 0; i < nmlist; i++) {
		if (crc == mlist[i].crc && !orbiter::production::ComparePrefix (fname, mlist[i].fname, 32)) {
			if (firstload) *firstload = false;
			return mlist[i].mesh; // found it
		}
	}
	// not found, so load from file
	ifstream ifs (GetMeshServices().path(GetMeshServices().context, fname), ios::in);
	auto mesh = std::make_unique<Mesh>(); TRACENEW
	ifs >> *mesh;
	if (!ifs || !mesh->nGroup()) { // load error
		const auto& services=GetMeshServices();
		const std::string message = fname[0] ? "Mesh not found or invalid: " + services.path(services.context, fname).string() : "Mesh file name not provided";
		services.error(services.context, message.c_str());
		//g_pOrbiter->TerminateOnError ();
		return 0;
	}
	if (nmlist == nmlistbuf) { // need to allocate buffer
		MeshBuffer *tmp = new MeshBuffer[nmlistbuf += 32]; TRACENEW
		if (nmlist) {
			memcpy (tmp, mlist, nmlist*sizeof(MeshBuffer));
			delete []mlist;
			mlist = NULL;
		}
		mlist = tmp;
	}
	mesh->SetName(fname);
	mlist[nmlist].mesh = mesh.get();
	mlist[nmlist].crc  = crc;
	strncpy (mlist[nmlist].fname, fname, 32);
	nmlist++;
	if (firstload) *firstload = true;
	return mesh.release();
}

// =======================================================================
// Nonmember functions

bool LoadMesh (const char *meshname, Mesh &mesh)
{
	ifstream ifs (GetMeshServices().path(GetMeshServices().context, meshname), ios::in);
	ifs >> mesh;
	if (ifs.good()) {
		mesh.SetName(meshname);
		return true;
	} else {
		const auto& services=GetMeshServices();
		const std::string message = "Mesh not found or invalid: " + services.path(services.context, meshname).string();
		services.error(services.context, message.c_str());
		//g_pOrbiter->TerminateOnError ();
		return false;
	}
}


// =======================================================================
// Create a sphere patch.
// nlng is the number of patches required to span the full 360° in longitude
// nlat is the number of patches required to span the latitude range from 0 to 90°
// 0 <= ilat < nlat is the actual latitude strip the patch is to cover
// res >= 1 is the resolution of the patch (= number of internal latitude strips in the patch)
// bseg, if given, is the number of of polygon segments on the lower base line of the patch.
// Default is (nlat-ilat)*res. bseg is ignored for triangular patches (i.e. where upper
// latitude is 90°)

void CreateSpherePatch (Mesh &mesh, int nlng, int nlat, int ilat, int res, int bseg, bool reduce, bool outside)
{
	const float c1 = 1.0f, c2 = 0.0f; // -1.0f/512.0f; // assumes 256x256 texture patches
	//const float c1 = 1.0f-1.0f/256.0f, c2 = 1.0f/512.f;
	int i, j, nVtx, nIdx, nseg, n, nofs0, nofs1;
	double minlat, maxlat, lat, minlng, maxlng, lng;
	double slat, clat, slng, clng;
	UInt16 tmp;
	
	minlat = Pi05 * (double)ilat/(double)nlat;
	maxlat = Pi05 * (double)(ilat+1)/(double)nlat;
	minlng = 0;
	maxlng = Pi2/(double)nlng;
	if (bseg < 0 || ilat == nlat-1) bseg = (nlat-ilat)*res;

	// generate nodes
	nVtx = (bseg+1)*(res+1);
	if (reduce) nVtx -= ((res+1)*res)/2;
	NTVERTEX *Vtx = new NTVERTEX[nVtx]; TRACENEW

	for (i = n = 0; i <= res; i++) {  // loop over longitudinal strips
		lat = minlat + (maxlat-minlat) * (double)i/(double)res;
		slat = sin(lat), clat = cos(lat);
		nseg = (reduce ? bseg-i : bseg);
		for (j = 0; j <= nseg; j++) {
			lng = (nseg ? minlng + (maxlng-minlng) * (double)j/(double)nseg : 0.0);
			slng = sin(lng), clng = cos(lng);
			Vtx[n].x = Vtx[n].nx = (float)(clat*clng);
			Vtx[n].y = Vtx[n].ny = (float)(slat);
			Vtx[n].z = Vtx[n].nz = (float)(clat*slng);
			Vtx[n].tu = (float)(nseg ? (c1*j)/nseg+c2 : 0.5); // overlap to avoid seams
			Vtx[n].tv = (float)((c1*(res-i))/res+c2);

			if (!outside) {
				Vtx[n].nx = - Vtx[n].nx;
				Vtx[n].ny = - Vtx[n].ny;
				Vtx[n].nz = - Vtx[n].nz;
			}

			n++;
		}
	}

	// generate faces
	nIdx = (reduce ? res * (2*bseg-res) : 2*res*bseg) * 3;
	UInt16 *Idx = new UInt16[nIdx]; TRACENEW

	for (i = n = nofs0 = 0; i < res; i++) {
		nseg = (reduce ? bseg-i : bseg);
		nofs1 = nofs0+nseg+1;
		for (j = 0; j < nseg; j++) {
			Idx[n++] = nofs0+j;
			Idx[n++] = nofs1+j;
			Idx[n++] = nofs0+j+1;
			if (reduce && j == nseg-1) break;
			Idx[n++] = nofs0+j+1;
			Idx[n++] = nofs1+j;
			Idx[n++] = nofs1+j+1;
		}
		nofs0 = nofs1;
	}
	if (!outside)
		for (i = 0; i < nIdx/3; i += 3)
			tmp = Idx[i+1], Idx[i+1] = Idx[i+2], Idx[i+2] = tmp;

	mesh.Clear();
	mesh.AddGroup (Vtx, nVtx, Idx, nIdx, SPEC_INHERIT, SPEC_INHERIT);
	mesh.Setup ();
}
