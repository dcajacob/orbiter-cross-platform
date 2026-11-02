// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "Production/Random.h"
#include "Production/SurfaceServices.h"
#include "Production/CelestialServices.h"
#include "Production/Text.h"
#include "Base.h"
#include "Baseobj.h"
#include "Planet.h"
#include "AstroMath.h"
#include "Production/SurfaceNavigation.h"
#include "TimeData.h"
#include "Mesh.h"
#include <fstream>

using namespace std;
using namespace orbiter::production;


static int refcount = 0;

// ==========================================================
// static resources

Mesh       *Base::generic_obj_mesh = 0;
char      **Base::generic_mesh_name = 0;
int         Base::ngenericmesh = 0;
SURFHANDLE *Base::generic_dtex = 0;
SURFHANDLE *Base::generic_ntex = 0;
char      **Base::generic_tex_name = 0;
SurfaceName   *Base::generic_tex_id = 0;
int         Base::ngenerictex = 0;

// ==========================================================
// class Base

Base::Base (char *fname, Planet *_planet, double _lng, double _lat)
: Body (fname), lng (_lng), lat (_lat)
{
	char cbuf[256];
	int texid = 0, bias = 0;
	obj=nullptr; lspec=nullptr; rwy=nullptr; vor=nullptr;
	genmsh_os=genmsh_us=genmsh_col=nullptr;
	objmsh_os=objmsh_us=objmsh_sh=objmsh_col=nullptr;
	sh_elev=nullptr; nobjmsh_os=nobjmsh_us=nobjmsh_sh=nobjmsh_col=0;
	objmsh_valid=false; tile=nullptr; ntile=ntilebuf=0;
	padfree=0; objscale=100.0; bObjmapsphere=false;
	//visual = 0;
	sundir.Set(0,-1,0);
	sundir_updt = 0.0;

	InitDeviceObjects ();

	ifstream ifs (GetBodyServices().ConfigPath(fname));

	// read location information from file, if available
	if (ifs && GetItemString (ifs, "LOCATION", cbuf)) {
		sscanf (cbuf, "%lf%lf", &lng, &lat);
		lng *= RAD; lat *= RAD;
	}

	Attach (_planet);

	// read list of objects
	nobj = npad = nrwy = nnav = nvor = 0;
	if (!ifs) return;

	// default base object size scale
	if (!GetItemReal (ifs, "OBJECTSIZE", objscale)) objscale = 100.0;

	// map base objects onto sphere (take into account planet curvature)?
	if (!GetItemBool (ifs, "MAPOBJECTSTOSPHERE", bObjmapsphere)) bObjmapsphere = false;

	// read list of VOR transmitters into planet data base
	if (FindLine (ifs, "BEGIN_NAVBEACON")) {
		char cbuf[256];
		for (;;) {
			if (!ifs.getline (cbuf, 256) || !ComparePrefix (cbuf, "END_NAVBEACON", 13)) break;
			Nav *nv = ParseNav (cbuf, _planet);
			if (nv) {
				_planet->NavMgr().AddNav (nv);
				Nav **tmp = new Nav*[nvor+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
				if (nvor) {
					memcpy (tmp, vor, nvor*sizeof(Nav*));
					delete []vor;
					vor = NULL;
				}
				vor = tmp;
				vor[nvor++] = nv;
			}
		}
	}

	genmsh_os = genmsh_us = genmsh_col = 0;
	objmsh_os = objmsh_us = 0;
	objmsh_sh = 0; sh_elev = 0;
	objmsh_col = 0;
	nobjmsh_os = nobjmsh_us = nobjmsh_sh = nobjmsh_col = 0;
	objmsh_valid = false;

	if (FindLine (ifs, "BEGIN_OBJECTLIST")) {
		BaseObject *bo;
		while (bo = BaseObject::Create (this, ifs)) {
			BaseObject **tmp = new BaseObject*[nobj+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
			if (nobj) memcpy (tmp, obj, nobj*sizeof(BaseObject*));
			if (nobj) delete []obj;
			obj = tmp;
			obj[nobj++] = bo;
			// register landing pads
			if (bo->GetSpecs() & OBJSPEC_LPAD) {
				((Lpad*)bo)->SetPadno (npad);
				LpadSpec *tmp = new LpadSpec[npad+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
				if (npad) memcpy (tmp, lspec, npad*sizeof(LpadSpec)), delete []lspec;
				lspec = tmp;
				const Vector &pos = ((Lpad*)bo)->GetPos();
				lspec[npad].relpos.Set (pos.x, pos.y, pos.z);
				lspec[npad].status = 0;
				lspec[npad].vessel = 0;
				if (float freq = ((Lpad*)bo)->GetILSfreq()) {
					double plng, plat;
					Rel_EquPos (lspec[npad].relpos, plng, plat);
					navlist.AddNav (lspec[npad].nav = new Nav_VTOL (this, npad, plng, plat, freq)); TraceSurfaceAllocation(__FILE__,__LINE__);
				} else lspec[npad].nav = 0;
				npad++;
			} else if (bo->GetSpecs() & OBJSPEC_RWY) {
				Runway *prwy = (Runway*)bo;
				RwySpec *tmp = new RwySpec[nrwy+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
				if (nrwy) memcpy (tmp, rwy, nrwy*sizeof(RwySpec)), delete []rwy;
				rwy = tmp;
				Vector p1 (Vector (prwy->end1.x, prwy->end1.y, prwy->end1.z));
				Vector p2 (Vector (prwy->end2.x, prwy->end2.y, prwy->end2.z));
				Rel_EquPos (p1, rwy[nrwy].lng1, rwy[nrwy].lat1);
				Rel_EquPos (p2, rwy[nrwy].lng2, rwy[nrwy].lat2);
				Orthodome (rwy[nrwy].lng1, rwy[nrwy].lat1, rwy[nrwy].lng2, rwy[nrwy].lat2, rwy[nrwy].length, rwy[nrwy].appr1);
				rwy[nrwy].appr1 = SurfacePositiveAngle (rwy[nrwy].appr1);
				rwy[nrwy].length *= cbody->Size();
				if (float freq = prwy->GetILSfreq(0)) {
					navlist.AddNav (rwy[nrwy].ils1 = new Nav_ILS (this, rwy[nrwy].appr1, rwy[nrwy].lng1, rwy[nrwy].lat1, freq)); TraceSurfaceAllocation(__FILE__,__LINE__);
				}
				else rwy[nrwy].ils1 = 0;
				if (float freq = prwy->GetILSfreq(1)) {
					navlist.AddNav (rwy[nrwy].ils2 = new Nav_ILS (this, SurfacePositiveAngle (rwy[nrwy].appr1+Pi), rwy[nrwy].lng2, rwy[nrwy].lat2, freq)); TraceSurfaceAllocation(__FILE__,__LINE__);
				}
				else rwy[nrwy].ils2 = 0;
				nrwy++;
			}
		}
	}
	nnav = navlist.nNav();
	padfree = npad;

	// read list of surface tiles
	ntile = ntilebuf = 0;
	if (FindLine (ifs, "BEGIN_SURFTILELIST")) {
		char cbuf[256];
		int res, texflag, ilng, ilat;
		for (;;) {
			if (!ifs.getline(cbuf,256) || !ComparePrefix (cbuf, "END_SURFTILELIST", 16)) break;
			sscanf (cbuf, "%d%d%d%d", &res, &ilng, &ilat, &texflag);
			if (ntile == ntilebuf) {
				SurftileSpec *tmp = new SurftileSpec[ntilebuf+32]; TraceSurfaceAllocation(__FILE__,__LINE__);
				if (ntile) {
					memcpy (tmp, tile, ntile*sizeof(SurftileSpec));
					delete []tile;
				}
				tile = tmp;
				ntilebuf += 32;
			}
			tile[ntile].res     = res;
			tile[ntile].texflag = texflag;
			tile[ntile].ilng    = ilng;
			tile[ntile].ilat    = ilat;
			tile[ntile].mesh    = NULL;
			tile[ntile].tex     = NULL;
			ntile++;
		}
	}
}

Base::~Base ()
{
	if (npad) {	delete []lspec; lspec = NULL; }
	if (nrwy) { delete []rwy; rwy = NULL; }
	if (nobj) { 
		for (int i = 0; i < nobj; i++) {
			delete obj[i];
		}
		delete []obj;
		obj = NULL;
	}
	if (nvor) { delete []vor; vor = NULL; }
	// The generated meshes borrow static textures; release their CPU geometry
	// without releasing the shared surfaces. Object meshes belong to obj[].
	for (Mesh* mesh : {genmsh_os,genmsh_us,genmsh_col}) if (mesh) {
		for (UInt32 texture=0;texture<mesh->nTexture();++texture) mesh->SetTexture(texture,nullptr,false);
		delete mesh;
	}
	for (UInt32 shadow=0;shadow<nobjmsh_sh;++shadow) delete objmsh_sh[shadow];

	if (objmsh_os) { delete []objmsh_os; objmsh_os = NULL; }
	if (objmsh_us) { delete []objmsh_us; objmsh_us = NULL; }
	if (objmsh_sh) { delete []objmsh_sh; objmsh_sh = NULL; }
	if (objmsh_col) { delete []objmsh_col; objmsh_col = NULL; }
	if (sh_elev) { delete []sh_elev; sh_elev = NULL; }
}

void Base::CreateStaticDeviceObjects ()
{
	ngenericmesh = 0;
	ngenerictex  = 0;
	ifstream ifs (GetBodyServices().ConfigPath ("Base"));
	if (ifs) {
		char cbuf[256], **tmp_list;
		SurfaceName *tmp_id;
		// load list of generic texture names
		if (FindLine (ifs, "begin_textures")) {
			for (;;) {
				if (!ifs.getline (cbuf, 256) || !ComparePrefix (cbuf, "end_textures", 12)) break;
				char *str = trim_string (cbuf);
				if (*str) {
					tmp_list = new char*[ngenerictex+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
					tmp_id   = new SurfaceName[ngenerictex+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
					if (ngenerictex) {
						memcpy (tmp_list, generic_tex_name, ngenerictex*sizeof(char*));
						delete []generic_tex_name;
						generic_tex_name = NULL;
						memcpy (tmp_id, generic_tex_id, ngenerictex*sizeof(SurfaceName));
						delete []generic_tex_id;
						generic_tex_id = NULL;
					}
					generic_tex_name = tmp_list;
					generic_tex_id = tmp_id;
					int len = strlen(str);
					generic_tex_name[ngenerictex] = new char[len+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
					strcpy (generic_tex_name[ngenerictex], str);
					generic_tex_id[ngenerictex] = NameToId (str);
				    ngenerictex++;
				}
			}
		}
		// load generic textures
		if (ngenerictex) {
			generic_dtex = new SURFHANDLE[ngenerictex]; TraceSurfaceAllocation(__FILE__,__LINE__);
			generic_ntex = new SURFHANDLE[ngenerictex]; TraceSurfaceAllocation(__FILE__,__LINE__);
			// the actual load is performed by InitStaticDeviceObjects
		}
	}

	const bool graphics = GetSurfaceServices().HasGraphics();
	char fname[256];

	for (int i = 0; i < ngenerictex; i++) {
		if (graphics) {
			sprintf (fname, "%s.dds", generic_tex_name[i]);
			generic_dtex[i] = GetSurfaceServices().LoadTexture (fname,false);
			sprintf (fname, "%s_n.dds", generic_tex_name[i]);
			generic_ntex[i] = GetSurfaceServices().LoadTexture (fname,false);
		} else {
			generic_dtex[i] = NULL;
			generic_ntex[i] = NULL;
		}
	}
}
	
void Base::DestroyStaticDeviceObjects ()
{
	// CPU resource names/arrays also exist in a headless session.
	const bool graphics=GetSurfaceServices().HasGraphics();
	for (int i=0;i<ngenerictex;++i) {
		if (graphics && generic_dtex[i]) GetSurfaceServices().ReleaseTexture(generic_dtex[i],false);
		if (graphics && generic_ntex[i]) GetSurfaceServices().ReleaseTexture(generic_ntex[i],false);
		delete []generic_tex_name[i];
	}
	delete []generic_tex_name; generic_tex_name=nullptr;
	delete []generic_tex_id; generic_tex_id=nullptr;
	delete []generic_dtex; generic_dtex=nullptr;
	delete []generic_ntex; generic_ntex=nullptr;
	ngenerictex=0;
}

void Base::InitDeviceObjects ()
{
	Body::InitDeviceObjects();
}

void Base::DestroyDeviceObjects ()
{
	DestroySurfaceTiles ();
	Body::DestroyDeviceObjects ();
}

void Base::Setup ()
{
	elev = RefPlanet()->Elevation (lng, lat); 
	if (elev) {
		rad += elev;
		cbody->EquatorialToLocal (lng, lat, rad, rpos);
	}

	for (UInt32 i = 0; i < nobj; i++)
		obj[i]->Setup();
}

bool Base::InitSurfaceTiles () const
{
	if (!ntile) return false;

	static UInt32 nlat[10] = {128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536};
	UInt32 i;
	float r = (float)rad;
	float cphi = (float)cos (lng), sphi = (float)sin (lng);
	float ctht = (float)cos (lat), stht = (float)sin (lat);

	orbiter::production::MeshTransform4 R = {(float)rrot.m11, (float)rrot.m12, (float)rrot.m13, 0,
		           (float)rrot.m21, (float)rrot.m22, (float)rrot.m23, 0,
				   (float)rrot.m31, (float)rrot.m32, (float)rrot.m33, 0,
				   0,               0,               0,               1};

	for (i = 0; i < ntile; i++) {

		// 1. Create the tile meshes
		if (!tile[i].mesh) {
			Mesh *mesh = new Mesh; TraceSurfaceAllocation(__FILE__,__LINE__);
			tile[i].mesh = (MESHHANDLE)mesh;
			int n = nlat[tile[i].res], n4 = n*4;
			int alat = tile[i].ilat;
			bool south = (alat < 0);
			if (south) alat = -alat - 1;
			CreateSpherePatch (*mesh, n4, n, alat, 4, 4, false, true);
			mesh->Scale (r, r, r);
			if (south) mesh->Rotate (Mesh::ROTATE_X, (float)Pi);
			mesh->Rotate (Mesh::ROTATE_Y, (float)(Pi05*(tile[i].ilng + (south ? 1:0)))/(float)n);
			mesh->Translate (-r*ctht*cphi, -r*stht, -r*ctht*sphi);
			mesh->Transform (R);
		}

		// 2. Load the textures
		if (!tile[i].tex && (tile[i].texflag & 1)) {
			char cbuf[256];
			sprintf (cbuf, "%s_%d_%c%04d_%c%04d.dds", cbody->Name(), tile[i].res,
				tile[i].ilng >= 0 ? 'e':'w', abs(tile[i].ilng),
				tile[i].ilat >= 0 ? 'n':'s', abs(tile[i].ilat));
			tile[i].tex = GetSurfaceServices().LoadTexture (cbuf,true);
		}
	}

	return true;
}

void Base::DestroySurfaceTiles ()
{
	if (ntilebuf) {
		for (UInt32 i = 0; i < ntile; i++) {
			if (tile[i].mesh) {
				delete (Mesh*)tile[i].mesh;
				tile[i].mesh = NULL;
			}
			if (tile[i].tex) {
				GetSurfaceServices().ReleaseTexture (tile[i].tex,true);
				tile[i].tex = NULL;
			}
		}
		delete []tile;
		tile = NULL;
		ntile = ntilebuf = 0;
	}
}

void Base::Attach (Planet *_parent)
{
	cbody = _parent;

	// Set local parameters
	double slng = sin(lng), clng = cos(lng);
	double slat = sin(lat), clat = cos(lat);
	rad = cbody->Size(); // dist from planet centre
	elev = 0.0;
	cbody->EquatorialToLocal (slng, clng, slat, clat, rad, rpos);
	s0->vel.Set (0,0,0);                         // base is fixed to ground
	rrot.Set ( clng*slat, clng*clat, -slng,   // rotate from local
		      -clat,      slat,       0,      // base to local
			   slng*slat, slng*clat,  clng);  // planet coords

	double v = Pi2*rad*clat / cbody->RotT(); // surface velocity
	rotvel.Set (-v*slng, 0.0, v*clng);        // velocity vector in non-rotating planet coords
}

UInt32 Base::GetTileList (const SurftileSpec **_tile) const
{
	if (ntile && !tile[0].mesh)
		InitSurfaceTiles();
	*_tile = tile; return ntile;
}

void Base::ExportBaseStructures (Mesh ***mesh_us, UInt32 *nmesh_us, Mesh ***mesh_os, UInt32 *nmesh_os) const
{
	ScanObjectMeshes();
	*mesh_os = objmsh_os;  *nmesh_os = nobjmsh_os;
	*mesh_us = objmsh_us;  *nmesh_us = nobjmsh_us;
}

void Base::ExportShadowGeometry (Mesh ***mesh_shadow, double **elev, UInt32 *nmesh_shadow) const
{
	ScanObjectMeshes();
	*mesh_shadow = objmsh_sh;
	*elev = sh_elev;
	*nmesh_shadow = nobjmsh_sh;
}

void Base::ExportCollisionMeshes (Mesh ***mesh_col, UInt32 *nmesh_col) const
{
	ScanObjectMeshes();
	*mesh_col = objmsh_col;
	*nmesh_col = nobjmsh_col;
}

void Base::ScanObjectMeshes () const
{
	if (objmsh_valid) return; // done already

	UInt32 i, j, k, ng, spec, nvtx, nidx;
	SurfaceName texid;
	bool undersh, groundsh;
	GroupSpec *grp_os = 0, *grp_us = 0, *grp_col = 0; // mesh groups for the meshes compiled from generic primitives (over and under shadows)
	UInt32 ngrp_os = 0, ngrp_us = 0, ngrp_col = 0;
	nobjmsh_os = nobjmsh_us = nobjmsh_sh = nobjmsh_col = 0;
	bool bshadow = GetSurfaceServices().Configuration().CfgVisualPrm.bShadows;

	for (i = 0; i < nobj; i++) {
		BaseObject *bo = obj[i];
		bo->Activate();
		spec = bo->GetSpecs();
		if (spec & OBJSPEC_EXPORTVERTEX) {
			ng = bo->nGroup();
			for (j = 0; j < ng; j++) {
				if (bo->GetGroupSpec (j, nvtx, nidx, texid, undersh, groundsh)) {
					UInt32 &ngrp     = (undersh ? ngrp_us : ngrp_os);
					GroupSpec *&grp = (undersh ? grp_us : grp_os);
					UInt32 texidx = GetGenericTextureIdx (texid);
					for (k = 0; k < ngrp; k++) {
						if (grp[k].TexIdx == texidx && (grp[k].UsrFlag & 0x1) != groundsh) {
							grp[k].nVtx += nvtx;
							grp[k].nIdx += nidx;
							break;
						}
					}
					if (k == ngrp) { // a new vertex group
						GroupSpec *tmp = new GroupSpec[ngrp+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
						if (ngrp) {
							memcpy (tmp, grp, ngrp*sizeof(GroupSpec));
							delete []grp;
						}
						grp = tmp;
						grp[ngrp].nVtx = nvtx;
						grp[ngrp].nIdx = nidx;
						grp[ngrp].TexIdx = texidx;
						grp[ngrp].UsrFlag = (groundsh ? 0:1);
						ngrp++;
					}
				}
			}
		}
		if ((spec & OBJSPEC_COLLISION) && (spec & OBJSPEC_EXPORTVERTEX)) {
			ng = bo->nGroup();
			for (j = 0; j < ng; j++) {
				if (bo->GetGroupSpec (j, nvtx, nidx, texid, undersh, groundsh)) {
					UInt32 texidx = GetGenericTextureIdx (texid);
					for (k = 0; k < ngrp_col; k++) {
						if (grp_col[k].TexIdx == texidx && (grp_col[k].UsrFlag & 0x1) != groundsh) {
							grp_col[k].nVtx += nvtx;
							grp_col[k].nIdx += nidx;
							break;
						}
					}
					if (k == ngrp_col) {
						GroupSpec *tmp = new GroupSpec[ngrp_col+1]; TraceSurfaceAllocation(__FILE__,__LINE__);
						if (ngrp_col) {
							memcpy (tmp, grp_col, ngrp_col*sizeof(GroupSpec));
							delete []grp_col;
						}
						grp_col = tmp;
						grp_col[ngrp_col].nVtx = nvtx;
						grp_col[ngrp_col].nIdx = nidx;
						grp_col[ngrp_col].TexIdx = texidx;
						grp_col[ngrp_col].UsrFlag = (groundsh ? 0:1);
						ngrp_col++;
					}
				}
			}
		}
		if (spec & OBJSPEC_EXPORTMESH) {
			if (spec & OBJSPEC_UNDERSHADOW) nobjmsh_us++;
			else                            nobjmsh_os++;
		}
		if ((spec & OBJSPEC_COLLISION) && (spec & OBJSPEC_EXPORTMESH)) nobjmsh_col++;
		if (bshadow && (spec & OBJSPEC_EXPORTSHADOWMESH)) nobjmsh_sh++;
	}

	for (i = 0; i < 3; i++) {
		UInt32 &ngrp = (i==0 ? ngrp_us : (i==1 ? ngrp_os : ngrp_col));
		if (!ngrp) continue;
		GroupSpec *&grp = (i==0 ? grp_us : (i==1 ? grp_os : grp_col));
		for (j = 0; j < ngrp; j++) {
			grp[j].Vtx = new NTVERTEX[grp[j].nVtx]; TraceSurfaceAllocation(__FILE__,__LINE__);
			grp[j].Idx = new UInt16[grp[j].nIdx]; TraceSurfaceAllocation(__FILE__,__LINE__);
			grp[j].nVtx = 0;
			grp[j].nIdx = 0;
		}
	}
	if (ngrp_os) nobjmsh_os++;
	if (ngrp_us) nobjmsh_us++;
	if (ngrp_col) nobjmsh_col++;
	if (nobjmsh_os) { objmsh_os = new Mesh*[nobjmsh_os]; nobjmsh_os = 0; TraceSurfaceAllocation(__FILE__,__LINE__); }
	if (nobjmsh_us) { objmsh_us = new Mesh*[nobjmsh_us]; nobjmsh_us = 0; TraceSurfaceAllocation(__FILE__,__LINE__); }
	if (nobjmsh_sh) { objmsh_sh = new Mesh*[nobjmsh_sh]; sh_elev = new double[nobjmsh_sh]; nobjmsh_sh = 0; TraceSurfaceAllocation(__FILE__,__LINE__); }
	if (nobjmsh_col) { objmsh_col = new Mesh*[nobjmsh_col]; nobjmsh_col = 0; TraceSurfaceAllocation(__FILE__,__LINE__); }

	for (i = 0; i < nobj; i++) {
		BaseObject *bo = obj[i];
		spec = bo->GetSpecs();
		if (spec & OBJSPEC_EXPORTVERTEX) {
			ng = bo->nGroup();
			for (j = 0; j < ng; j++) {
				bo->GetGroupSpec (j, nvtx, nidx, texid, undersh, groundsh);
				UInt32 &ngrp     = (undersh ? ngrp_us : ngrp_os);
				GroupSpec *&grp = (undersh ? grp_us : grp_os);
				UInt32 texidx = GetGenericTextureIdx (texid);
				for (k = 0; k < ngrp; k++) {
					if (grp[k].TexIdx == texidx && (grp[k].UsrFlag & 0x1) != groundsh) break;
				}
				bo->ExportGroup (j, grp[k].Vtx+grp[k].nVtx, grp[k].Idx+grp[k].nIdx, grp[k].nVtx);
				grp[k].nVtx += nvtx;
				grp[k].nIdx += nidx;
			}
		}
		if ((spec & OBJSPEC_COLLISION) && (spec & OBJSPEC_EXPORTVERTEX)) {
			ng = bo->nGroup();
			for (j = 0; j < ng; j++) {
				bo->GetGroupSpec (j, nvtx, nidx, texid, undersh, groundsh);
				UInt32 texidx = GetGenericTextureIdx (texid);
				for (k = 0; k < ngrp_col; k++) {
					if (grp_col[k].TexIdx == texidx && (grp_col[k].UsrFlag & 0x1) != groundsh) break;
				}
				bo->ExportGroup (j, grp_col[k].Vtx+grp_col[k].nVtx, grp_col[k].Idx+grp_col[k].nIdx, grp_col[k].nVtx);
				grp_col[k].nVtx += nvtx;
				grp_col[k].nIdx += nidx;
			}
		}
		if (spec & OBJSPEC_EXPORTMESH) {
			if (spec & OBJSPEC_UNDERSHADOW) objmsh_us[nobjmsh_us++] = bo->ExportMesh();
			else                            objmsh_os[nobjmsh_os++] = bo->ExportMesh();
		}
		if ((spec & OBJSPEC_COLLISION) && (spec & OBJSPEC_EXPORTMESH)) {
			Mesh *col_msh = bo->ExportMesh();
			if (col_msh) objmsh_col[nobjmsh_col++] = col_msh;
		}
		if (bshadow && (spec & OBJSPEC_EXPORTSHADOWMESH)) {
			Mesh *shmsh = bo->ExportShadowMesh (sh_elev[nobjmsh_sh]);
			if (shmsh) objmsh_sh[nobjmsh_sh++] = shmsh;
		}
	}

	for (i = 0; i < 3; i++) {
		UInt32 &ngrp = (i==0 ? ngrp_us : (i==1 ? ngrp_os : ngrp_col));
		if (!ngrp) continue;
		GroupSpec *&grp = (i==0 ? grp_us : (i==1 ? grp_os : grp_col));
		Mesh *mesh = new Mesh; TraceSurfaceAllocation(__FILE__,__LINE__);
		if (i==0) genmsh_us = mesh;
		else if (i==1) genmsh_os = mesh;
		else genmsh_col = mesh;

		for (j = 0; j < ngrp; j++) {
			UInt32 texidx = grp[j].TexIdx;
			int tidx = (texidx != (UInt32)-1 ? mesh->AddTexture (generic_dtex[texidx]) : SPEC_DEFAULT);
			int gidx = mesh->AddGroup (grp[j].Vtx, grp[j].nVtx, grp[j].Idx, grp[j].nIdx, SPEC_DEFAULT, tidx);
			mesh->GetGroup(gidx)->UsrFlag = grp[j].UsrFlag;
			if (texidx != (UInt32)-1 && generic_ntex[texidx]) {
				tidx = mesh->AddTexture (generic_ntex[texidx]);
				mesh->GetGroup(gidx)->TexIdxEx[0] = tidx;
			}
		}
		delete []grp;
		grp = NULL;
		if (i==0) objmsh_us[nobjmsh_us++] = mesh;
		else if (i==1) objmsh_os[nobjmsh_os++] = mesh;
		else objmsh_col[nobjmsh_col++] = mesh;
	}
	objmsh_valid = true;
}
void Base::Update (bool force)
{
	s1->R.Set (rrot);
	s1->R.premul (cbody->s1->R);
	s1->Q.Set (s1->R);
	// WARNING: this should work the other way round: combine the
	// two quaternions and extract grot

	s1->pos.Set (mul (cbody->s1->R, rpos) + cbody->s1->pos);
	s1->vel.Set (mul (cbody->s1->R, rotvel) + cbody->s1->vel);

	// periodically update some secondary parameters
	if (CelestialClock().SimT1 > sundir_updt || force) {
		sundir = SunDirection();
		double csun = sundir.y;
		sundir_updt = CelestialClock().SimT1 + (csun < -0.1 ? 50.0 : csun > 0.1 ? 10.0 : 2.0);
	}
}

void Base::Rel_EquPos (const Vector &relpos, double &_lng, double &_lat) const
{
	_lng = lng + relpos.z/(cbody->Size()*cos(lat));
	_lat = lat - relpos.x/cbody->Size();
}

void Base::Pad_EquPos (UInt32 padno, double &_lng, double &_lat) const
{
	_lng = lng;
	_lat = lat;
	if (padno < npad) {
		_lng += lspec[padno].relpos.z/(cbody->Size()*cos(lat));
		_lat -= lspec[padno].relpos.x/cbody->Size();
	}
}

bool Base::GetGenericTexture (SurfaceName id, SURFHANDLE &daytex, SURFHANDLE &nighttex) const
{
	for (int i = 0; i < ngenerictex; i++)
		if (id == generic_tex_id[i]) {
			daytex   = generic_dtex[i];
			nighttex = generic_ntex[i];
			return true;
		}
	daytex = nighttex = 0;
	return false;
}

UInt32 Base::GetGenericTextureIdx (SurfaceName id) const
{
	for (UInt32 i = 0; i < ngenerictex; i++)
		if (id == generic_tex_id[i])
			return i;
	return (UInt32)-1;
}

int Base::OccupyPad (Vessel *vessel, int pad, bool forcepad)
{
	int pd;
	UInt32 i;

	if (forcepad) {
		if (pad < 0) return -1;
		if (lspec[pad].status == 0) padfree--;
		lspec[pad].status = 1;
		lspec[pad].vessel = GetSurfaceServices().VesselState(vessel);
		return pad;
	}
	if (!padfree) return -1;
	if (pad >= 0 && lspec[pad].status == 0) {
		lspec[pad].status = 1;
		lspec[pad].vessel = GetSurfaceServices().VesselState(vessel);
		padfree--;
		return pad;
	}
	// pick random free pad
	pd = (static_cast<std::int64_t>(orbiter::production::RandomInteger())*padfree)/(static_cast<std::int64_t>(orbiter::production::RandomMaximum)+1);
	for (i = 0; i < npad; i++) {
		if (lspec[i].status == 0) {
			if (!pd--) {
				lspec[i].status = 1;
				lspec[i].vessel = GetSurfaceServices().VesselState(vessel);
				padfree--;
				return (int)i;
			}
		}
	}
	// should not get here
	return -1;
}

int Base::OccupyPad (Vessel *vessel, double _lng, double _lat)
{
	const double padrad = 20.0; // landing pad size
	double plng, plat, dist, bdir;
	for (UInt32 i = 0; i < npad; i++) {
		Pad_EquPos (i, plng, plat);
		Orthodome (_lng, _lat, plng, plat, dist, bdir);
		dist *= cbody->Size();
		if (dist < padrad) {
			if (lspec[i].status == 0) {
				lspec[i].status = 1;
				lspec[i].vessel = GetSurfaceServices().VesselState(vessel);
				padfree--;
				return (int)i;
			}
		}
	}
	return -1; // failure: pad not free
}

void Base::ClearPad (Vessel *vessel)
{
	for (UInt32 i = 0; i < npad; i++)
		if (lspec[i].status && lspec[i].vessel == GetSurfaceServices().VesselState(const_cast<Vessel*>(vessel))) {
			lspec[i].status = 0;
			lspec[i].vessel = 0;
			padfree++;
		}
}

int Base::LandedAtPad (const Vessel *vessel) const
{
	for (UInt32 i = 0; i < npad; i++)
		if (lspec[i].status == 1 && lspec[i].vessel == GetSurfaceServices().VesselState(const_cast<Vessel*>(vessel)))
			return (int)i;
	return -1;
}

int Base::RequestLanding (Vessel *vessel, UInt32 &padno)
{
	if (orbiter::production::RandomInteger() < orbiter::production::RandomMaximum/2) return 2; // keep pending
	if (!padfree) return 1;     // deny
	int pd = (static_cast<std::int64_t>(orbiter::production::RandomInteger())*padfree)/(static_cast<std::int64_t>(orbiter::production::RandomMaximum)+1);
	for (UInt32 i = 0; i < npad; i++) {
		if (lspec[i].status == 0) {
			if (!pd--) {
				lspec[i].status = 2;
				lspec[i].vessel = GetSurfaceServices().VesselState(vessel);
				padfree--;
				padno = i;
				return 4; // grant clearance
			}
		}
	}
	// should not get here
	return 2;
}

int Base::RequestTakeoff ()
{
	if (orbiter::production::RandomInteger() < orbiter::production::RandomMaximum/2) return 3; // keep pending
	return 5;                   // grant clearance
}

void Base::ReportTakeoff (Vessel *vessel)
{
	for (UInt32 i = 0; i < npad; i++) {
		if (lspec[i].status == 1 && lspec[i].vessel == GetSurfaceServices().VesselState(const_cast<Vessel*>(vessel))) {
			lspec[i].status = 0;
			lspec[i].vessel = 0;
			padfree++;
		}
	}
}

int Base::ReportTouchdown (VesselBase *vessel, double vlng, double vlat)
{
	const double padrad = 30.0; // landing pad size
	double plng, plat, dist, bdir;
	UInt32 i, padno = (UInt32)-1;
	for (i = 0; i < npad; i++) {
		Pad_EquPos (i, plng, plat);
		Orthodome (vlng, vlat, plng, plat, dist, bdir);
		dist *= cbody->Size();
		if (dist < padrad) {
			if (lspec[i].status == 0) padfree--;
			// else lspec[i].vessel->CancelClearance();
			lspec[i].status = 1;
			lspec[i].vessel = vessel;
			padno = i;
			break;
		}
	}
	if (padno != (UInt32)-1) { // cancel all other requests for this vessel
		if (GetSurfaceServices().Configuration().CfgLogicPrm.bPadRefuel)
			GetSurfaceServices().Refuel(*vessel);
		for (i = 0; i < npad; i++) {
			if (i == padno) continue;
			if (lspec[i].status && lspec[i].vessel == vessel) {
				lspec[i].status = 0;
				lspec[i].vessel = 0;
				padfree++;
			}
		}
	}
	return (int)padno;
}

double Base::CosSunAlt () const
{
	return (s0->R.m12*s0->pos.x + s0->R.m22*s0->pos.y + s0->R.m32*s0->pos.z) / (-s0->pos.length());
}
