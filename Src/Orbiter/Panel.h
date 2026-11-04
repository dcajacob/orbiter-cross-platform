// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// =======================================================================
// class Panel
// Custom instrument panels
// =======================================================================

#ifndef __PANEL_H
#define __PANEL_H

#define STRICT 1
#ifdef _WIN32
#include <windows.h>
#else
#include "OrbiterSdkDrawingTypes.h"
#endif
#include <fstream>
#include "Production/CockpitGraphics.h"

// =======================================================================
// class Panel

class Panel {
	friend class Pane;

public:
	Panel (int _id, const Pane *_pane, double _scale = 1.0);
	~Panel ();

	void Setup ();

	inline int GetId (void) const { return id; }
	// panel id (>= 0)

	void SetConnections (int left, int right, int top, int bottom);
	// define panel neighbours in four directions. -1=none

	inline int Connect (int dir) const { return connect[dir]; }
	// return connected panel id for specified direction

	inline SURFHANDLE GetSurface() const { return surf; }
	// panel surface

	inline double GetScale() const { return scale; }
	// panel scaling factor

	void Display (SURFHANDLE pdds);
	// map panel to screen

	void Move (oapi::SdkCoordinate dx, oapi::SdkCoordinate dy);
	// scrolls panel by the specified amount in x and y

	void Point2Screen (oapi::SdkCoordinate srcX, oapi::SdkCoordinate srcY, oapi::SdkCoordinate &tgtX, oapi::SdkCoordinate &tgtY) const;
	// converts point from unscaled panel space to viewport space

	void Area2Screen (const oapi::SdkRectangle &srcR, oapi::SdkRectangle &tgtR) const;
	// converts rectangle from unscaled panel space to viewport space

#ifdef _WIN32
	void DefineBackground (HBITMAP hBmp, oapi::UInt32 flag, oapi::UInt32 ck = (oapi::UInt32)-1);
#else
	void DefineBackground (SURFHANDLE bitmap, oapi::UInt32 flag, oapi::UInt32 ck = (oapi::UInt32)-1);
#endif

	void DefineArea (int aid, const oapi::SdkRectangle &pos, int draw_mode, int mouse_mode, int bkmode);
	void ReleaseAreas ();

	SURFHANDLE GetArea (int idx);
	// returns a drawing surface for the area. The contents of the surface
	// depend on the bkmode setting for the area:
	// PANEL_MAP_NONE or PANEL_MAP_BGONREQUEST: surface contents undefined
	// PANEL_MAP_BACKGROUND: surface contains the original area background
	// PANEL_MAP_CURRENT: surface contains the current status

	bool BltAreaBackground (int idx, SURFHANDLE s);
	// If area bkmode is PANEL_MAP_BGONREQUEST, this blits the area background
	// into surface s and returns true. Otherwise it does nothing and returns
	// false. s must be of appropriate size (e.g. the surface obtained from
	// GetArea)

	void SetArea (int idx, SURFHANDLE s);
	void RedrawArea (int idx, int event);
	void RedrawAllAreas (int event);

	void RegisterMFD (int id, const MFDSPEC &spec);

	inline void MFDSize (int id, int &w, int &h) const
	{ w = mfd[id].w, h = mfd[id].h; }

	bool ProcessMouse (oapi::UInt event, oapi::UInt32 state, int x, int y);

	void GetMouseState (int &idx, int &state, int &mx, int &my) const;
	//{ idx = idx_mfocus; state = mstate; mx = mousex, my = mousey; }

	inline void ClearMouseState () { mstate = 0; }
	inline void SetMouseState (int state) { mstate = state; }

	static bool Read (std::ifstream &ifs);
	void Write (std::ostream &ofs) const;

private:
	inline int AreaIndex (int aid) const
	{ 
		for (int i = 0; i < narea; i++) if (area[i]->id == aid) return i;
		return -1;
	}
	// returns list index of area given by its identifier (or -1 if doesn't exist)

	void MFDMoved ();

	const Pane *pane;
	oapi::CockpitClient *gc;
	int id;                     // panel id
	SURFHANDLE surf;            // drawing surface
	oapi::SdkCoordinate tgtW, tgtH;            // panel target width, height
	oapi::SdkCoordinate srcW, srcH;            // panel source width, height
	oapi::SdkCoordinate X0, Y0;                // coordinates of upper left corner of scaled source rectangle in target space
#ifdef _WIN32
	HWND cwnd;                  // window handle for mouse position offset calculations
#endif
	double scale, iscale;       // panel scaling factor src->tgt and tgt->src
	oapi::SdkRectangle tgtRect;               // corners of visible part of target rectangle
	oapi::SdkRectangle srcRect;				// visible panel area in source rectangle
	bool visible;				// panel is visible?
	bool scaled;                // true if scale != 1
	bool has_ck;                // flag if color key is used for blitting
	oapi::UInt32 ck;                   // color key for blitting
	oapi::UInt32 bltflag;              // blitting flag
	oapi::UInt32 shiftflag;            // bitflags for shifting modes
	int connect[4];             // connected panels (left,right,up,down) -1=none

	struct Area {
		int id;       // area identifier
		oapi::SdkRectangle pos;     // area rectangle in source panel
		int w, h;     // width, height of area
		int bltmode;  // blt mode: 0=return black surface, 1=return background, 2=return current panel state
		int redraw;   // redraw trigger code: 0=no redraw, 1=each frame, 2=on mouseclick in area
		int mouse;    // mouse states to cause callbacks
		SURFHANDLE surf, bksurf; // area surface, background surface
	} **area;
	int narea, nareabuf;

	int aid_mfocus;   // id of area currently receiving mouse focus
	int idx_mfocus;   // index of area currently receiving mouse focus
	int mstate;       // current mouse state
	mutable int mousex, mousey; // mouse position at last event

	struct MFD {
		bool exist;      // MFD defined for this panel?
		bool visible;    // MFD currently visible on screen
		oapi::SdkRectangle panel_pos;  // full area of MFD in scaled panel
		int w, h;        // MFD size in scaled panel
		oapi::SdkRectangle src_vis;    // visible part of MFD source rectangle
		int tgtx, tgty;  // upper left corner of visible part of MFD in screen coords
	} mfd[MAXMFD];
};

#endif // !__PANEL_H