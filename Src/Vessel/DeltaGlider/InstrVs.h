// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//                ORBITER MODULE: DeltaGlider
//                  Part of the ORBITER SDK
//
// InstrVs.h
// Vertical speed tape instrument for the Delta-Glider
// ==============================================================

#ifndef __INSTRVS_H
#define __INSTRVS_H

#include "../Common/Instrument.h"

class InstrVS: public PanelElement {
public:
	InstrVS (VESSEL3 *v);
	~InstrVS ();
	void Reset2D (int panelid, MESHHANDLE hMesh);
	void ResetVC (DEVMESHHANDLE hMesh);
	void AddMeshData2D (MESHHANDLE hMesh, oapi::UInt32 grpidx);
	bool Redraw2D (SURFHANDLE surf);
	bool RedrawVC (DEVMESHHANDLE hMesh, SURFHANDLE surf);

private:
	void Redraw (NTVERTEX *vtx, NTVERTEX *vtxr);
	int pvmin;
	SURFHANDLE sf;
	GROUPREQUESTSPEC vc_grp;         ///< Buffered VC vertex data (tape)
	GROUPREQUESTSPEC vc_grp_readout; ///< Buffered VC vertex data (readout)
	oapi::UInt16 vperm[4];
	oapi::UInt16 vperm_readout[20];
};

#endif // !__INSTRVS_H