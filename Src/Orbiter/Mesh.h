// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// =======================================================================
// Production CPU mesh data and operations:
// Triangle, Mesh
// =======================================================================

#ifndef __MESH_H
#define __MESH_H

#include <iostream>
#include <vector>
#include "OrbiterMeshData.h"
#include "Production/MeshServices.h"
#include "Production/MeshTypes.h"
#include "Production/MeshEditFlags.h"
#include "Production/MeshData.h"
using orbiter::production::UInt32;
using orbiter::production::UInt16;
using orbiter::production::UInt64;
using orbiter::production::MeshSurface;
using orbiter::production::MeshVector3;
using orbiter::production::MeshTransform4;
using orbiter::production::MeshGroupRequest;
using orbiter::production::MeshGroupEdit;
using orbiter::production::MeshExtraTextures;

typedef char Str256[256];

const UInt32 SPEC_DEFAULT = (UInt32)(-1); // "default" material/texture flag
const UInt32 SPEC_INHERIT = (UInt32)(-2); // "inherit" material/texture flag

// =======================================================================
// Class Triangle
// triangular surface patch

class ORBITER_PRODUCTION_API Triangle {
public:
	Triangle ();
	Triangle (const Triangle &tri);
	Triangle (int n0, int n1, int n2);

	void SetNodes (int n0, int n1, int n2);

	int nd[3];  // node index list
	int nm[3];  // normal index list

	bool hasNodes;   // true if nd[] is valid
	bool hasNormals; // true if nm[] is valid
};

// =======================================================================
// mesh group descriptor

typedef struct {
	NTVERTEX  *Vtx;
	UInt16      *Idx;
	UInt32     nVtx;
	UInt32     nIdx;
	UInt32     MtrlIdx;
	UInt32     TexIdx;
	UInt32     UsrFlag;
	UInt16      zBias;
	UInt16      Flags;
	UInt32     TexIdxEx[MeshExtraTextures];
	float     TexMixEx[MeshExtraTextures];
} GroupSpec;

// =======================================================================
// Class Mesh

class ORBITER_PRODUCTION_API Mesh {
	friend class EngineMeshSink;
public:
	Mesh ();
	// Create an empty mesh

	Mesh (NTVERTEX *vtx, UInt32 nvtx, UInt16 *idx, UInt32 nidx,
		UInt32 matidx = SPEC_DEFAULT, UInt32 texidx = SPEC_DEFAULT);
	// Create a single-group mesh

	Mesh (const Mesh &mesh);
	// copy constructor

	~Mesh ();

	void Set (const Mesh &mesh);

	void Setup ();
	// call after all groups are assembled or whenever groups change,
	// to set up group parameters

	const char* GetName() const;
	void SetName(const char* name);

	UInt32 GetFlags () const { return Flags; }
	void SetFlags (UInt32 flags) { Flags = flags; }

	void SetupGroup (UInt32 grp);
	// Re-apply setup for a particular group (e.g. after transformation)

	inline UInt32 nGroup() const { return nGrp; }
	// Number of groups

	inline UInt32 nMaterial() const { return nMtrl; }
	// Number of materials

	inline UInt32 nTexture() const { return nTex; }
	const std::vector<orbiter::production::MeshTexture>& TextureSources() const { return textureSources; }
	// Number of textures

	inline GroupSpec *GetGroup (UInt32 grp) { return (grp < nGrp ? Grp+grp : 0); }
	// return a pointer to the group specification for group grp

	inline UInt32 GetGroupUsrFlag (UInt32 grp) const { return (grp < nGrp ? Grp[grp].UsrFlag : 0); }
	// return the user-defined flag for group grp

	int AddGroup (NTVERTEX *vtx, UInt32 nvtx, UInt16 *idx, UInt32 nidx,
		UInt32 mtrl_idx = SPEC_INHERIT, UInt32 tex_idx = SPEC_INHERIT,
		UInt16 zbias = 0, UInt32 flag = 0, bool deepcopy = false);
	// Add new group to the mesh and return its group index
	// The vtx and idx lists must have been dynamically allocated. They
	// are shallow-copied, and the mesh takes ownership.
	// The calling program must not delete them.

	bool AddGroupBlock (UInt32 grp, const NTVERTEX *vtx, UInt32 nvtx, const UInt16 *idx, UInt32 nidx);
	// Add geometry (vertices and indices) to an existing group.
	// Indices (idx) are zero-based. When adding them to the group, index
	// offsets are added automatically.

	bool DeleteGroup (UInt32 grp);
	// Delete group 'grp'. Note that the indices of the other
	// groups may change as a result.
	// Return value is false if grp index is out of range

	int GetGroup (UInt32 grp, MeshGroupRequest *grs);
	// retrieve vertex and index data (deep copy)

	int EditGroup (UInt32 grp, MeshGroupEdit *ges);
	// edit/replace parts of the group

	void AddMesh (Mesh &mesh);
	// Merge "mesh" into "this", by adding all groups of "mesh"
	// Currently this does not use the materials and textures of "mesh"

	inline MATERIAL *GetMaterial (UInt32 matidx)
	{ return (matidx < nMtrl ? Mtrl+matidx : 0); }
	// return a material pointer

	int AddMaterial (MATERIAL &mtrl);
	// Add new material to the mesh and return its list index

	bool DeleteMaterial (UInt32 matidx);
	// Delete material with index 'matidx' from the list. Any groups
	// using that material are reset to material 0. Any group material
	// indices > matidx are decremented to account for changed list

	int AddTexture (MeshSurface tex);
	// Add new texture to the mesh and return its list index
	// If the texture exists already, it is not added again, but the index
	// of the existing texture is returned

	bool SetTexture (UInt32 texidx, MeshSurface tex, bool release_old = true);
	// replace a texture

	inline MeshSurface GetTexture (UInt32 texidx)
	{ return (texidx < nTex ? Tex[texidx] : 0); }
	// return a texture pointer

	void SetTexMixture (UInt32 grp, UInt32 ntex, float mix);
	void SetTexMixture (UInt32 ntex, float mix);

	void ScaleGroup (UInt32 grp, float sx, float sy, float sz);
	void Scale (float sx, float sy, float sz);
	// scale an individual group or the whole mesh

	void TranslateGroup (UInt32 grp, float dx, float dy, float dz);
	void Translate (float dx, float dy, float dz);
	// translate an individual group or the whole mesh

	enum RotAxis { ROTATE_X, ROTATE_Y, ROTATE_Z };
	void RotateGroup (UInt32 grp, RotAxis axis, float angle);
	void Rotate (RotAxis axis, float angle);
	// rotate the mesh 'angle' rad around a coordiate axis

	void TransformGroup (UInt32 grp, const MeshTransform4 &mat);
	void Transform (const MeshTransform4 &mat);
	// rotate mesh using the provided rotation matrix

	void TexScaleGroup (UInt32 grp, float su, float sv);
	void TexScale (float su, float sv);
	// scale the texture coordinates of an individual group or the whole mesh

	void CalcNormals (UInt32 grp, bool missingonly);
	// automatic calculation of vertex normals for group grp
	// if missingonly=true then only normals with zero length are calculated

	void CalcTexCoords (UInt32 grp);
	// under construction

	void Clear ();

	static void GlobalEnableSpecular (bool enable);
	void EnableMatAlpha (bool enable);

	friend std::istream &operator>> (std::istream &is, Mesh &mesh);
	// read mesh from file

	friend std::ostream &operator<< (std::ostream &os, const Mesh &mesh);
	// write mesh to file

protected:
	void ReleaseTextures ();
	// Release textures acquired by the mesh

private:
	UInt32 nGrp;         // number of groups
	GroupSpec *Grp;     // list of group specs	

	UInt32 nMtrl;        // number of materials
	MATERIAL *Mtrl; // list of materials used by the mesh

	UInt32 nTex;         // number of textures
	MeshSurface *Tex;    // host-owned texture handles
	std::vector<orbiter::production::MeshTexture> textureSources;

	bool GrpSetup;      // true if the following arrays are allocated
	MeshVector3 *GrpCnt;  // list of barycentres for each group (local coords)
	float *GrpRad;   // list of max. radii for each group
	UInt32 *GrpVis;      // visibility flags for each group
	char* name;

	// global mesh flags
	static bool bEnableSpecular;   // enable specular reflection
	bool bModulateMatAlpha;
	// modulate material alpha with texture alpha (if disabled, any groups
	// that use textures ignore the material alpha values)
	UInt32 Flags = 0;    // bit | effect
	                    // 0   | set: mesh casts shadow (used for base object meshes)
						// 1   | set: use global shadow flag (bit 0) for all groups; unset: use individual group flags
};

// =======================================================================
// Class MeshManager: globally managed meshes

class ORBITER_PRODUCTION_API MeshManager {
public:
	MeshManager();
	~MeshManager();
	void Flush();

	const Mesh *LoadMesh (const char *fname, bool *firstload = NULL);
	// Load a mesh from file (or just return a handle if loaded already.
	// If firstload is used, it is set to true if the mesh was loaded from
	// file, and false if the mesh was in memory already

private:
	struct MeshBuffer {
		Mesh *mesh;
		UInt64 crc;
		char fname[32];
	} *mlist;
	int nmlist, nmlistbuf;
};

// =======================================================================
// Nonmember functions

bool LoadMesh (const char *meshname, Mesh &mesh);
// Load an unmanaged mesh (caller is responsible for deleting after use)
// meshname is relative to MeshPath directory.
// Returns true if mesh was loaded, false if not found.

void CreateSpherePatch (Mesh &mesh, int nlng, int nlat, int ilat, int res,
	int bseg = -1, bool reduce = true, bool outside = true);
// Create a mesh representing a rectangular patch on a sphere at a given
// position and resolution

#endif // !__MESH_H
