// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//                 ORBITER MODULE: SolarSail
//                  Part of the ORBITER SDK
//
// SolarSail.h
// SolarSail class interface
// ==============================================================

#ifndef __SOLARSAIL_H
#define __SOLARSAIL_H

#define STRICT 1
#include "../StockVesselPlatform.h"

#define MAXNBHR 6 // max node neighbours

struct NBHR {            // node neigbourhood structure
	oapi::UInt32 nnd;              // number of neighbours
	oapi::UInt32 nd[MAXNBHR];      // neighbour index list
	double dst0[MAXNBHR];   // neighbour distance list
	bool fix;               // fix node position
};

// ==============================================================
// SolarSail interface

class SolarSail: public VESSEL3 {
public:
	SolarSail (OBJHANDLE hVessel, int flightmodel);
	virtual ~SolarSail();

	// one-time global setup across all instances
	static void GlobalSetup();

	void clbkSetClassCaps (FILEHANDLE cfg);
	void clbkPreStep (double simt, double simdt, double mjd);
	void clbkPostStep (double simt, double simdt, double mjd);
	void clbkGetRadiationForce (const VECTOR3 &mflux, VECTOR3 &F, VECTOR3 &pos);
	void clbkVisualCreated (VISHANDLE vis, int refcount);
	void clbkVisualDestroyed (VISHANDLE vis, int refcount);
	int  clbkGeneric (int msgid, int prm, void *context);

	// update sail nodal displacements
	void UpdateSail (const VECTOR3 *rpressure);
	void SetPaddle (int p, double pos);

	static inline oapi::UInt16 *sail_idx[4]; // index cache for each sail group
private:
	DEVMESHHANDLE hMesh;           // mesh instance handle
	VECTOR3 mf;                    // radiation mass flux
	oapi::UInt anim_paddle[4];           // steering paddle animation identifiers
	double paddle_rot[4];          // paddle logical rotation state (0-1, 0.5=neutral)
	double paddle_vis[4];          // paddle visual rotation state

	void DefineAnimations();

	// script interface-related methods
	int Lua_InitInterpreter (void *context);
	int Lua_InitInstance (void *context);

	static void SetupElasticity (MESHHANDLE hMeshTemplate);
	static MESHHANDLE hMeshTpl; // global mesh template
	static oapi::UInt32 sail_nvtx, sail_ntri;
	static NBHR *nbhr;
	static VECTOR3 *sail_vbuf;   // vertex temporary buffer
	NTVERTEX *sail_vtx[4];       // vertex cache for each sail group

};

#endif // !__SOLARSAIL_H