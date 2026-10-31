// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//   ORBITER VISUALISATION PROJECT (OVP)
//   OGL Client module
// ==============================================================

// ==============================================================
// MeshMgr.h
// Mesh management and storage
// ==============================================================

#ifndef __OGLMESHMGR_H
#define __OGLMESHMGR_H

#include "OGLClient.h"
#include <map>
#include <string>

// ==============================================================
// class MeshManager (interface)
// ==============================================================
/**
 * \brief Simple management of persistent mesh templates
 */

class OGLMesh;
class OGLMeshManager {
public:
	OGLMeshManager ();
	~OGLMeshManager();
	void Flush();
	void StoreMesh (MESHHANDLE hMesh,const char *filename);
	const char *GetMeshName(MESHHANDLE mesh) const;
	const OGLMesh *GetMesh (MESHHANDLE hMesh);

private:
    std::map<MESHHANDLE,std::string> names;
	struct MeshBuffer {
		MESHHANDLE hMesh;
		OGLMesh *mesh;
	} *mlist;
	int nmlist, nmlistbuf;
};

#endif // !__OGLMESHMGR_H
