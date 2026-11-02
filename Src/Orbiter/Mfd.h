// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
// Steps for implementing a new default Instrument:
// - Add an MFD id (MFD_xxx) in orbitersdk.h
// - Increment BUILTIN_MFD_MODES in orbitersdk.h
// - Implement the Instrument class derived from Instrument
// - Add entries in Instrument::Create (both versions)
// - Add entry in Instrument::RegisterBuiltinModes()
// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#ifndef __MFD_H
#define __MFD_H

#define STRICT 1
#ifdef _WIN32
#include "OrbiterAPI.h"
#else
#include "NativeVesselAPI.h"
#endif
#include "Production/CockpitGraphics.h"
#include "Vessel.h"
#include "Element.h"
#include "Select.h"
#ifdef _WIN32
#include <d3d.h>
#endif

#include "MfdOrbitGeometry.h"

const int MAXPEN = 6;
const int MAXBRUSH = 10;
const int MAXDEFCOL = 5;

struct MFDMODE {          // MFD mode (for builtin and user-defined modes)
	MFDMODESPECEX *spec;  // mode specs
	MFDMODESPEC *oldspec; // obsolete
	int id;               // mode id

public:
	inline int Id() const { return id; }
	inline const MFDMODESPECEX *Spec() const { return spec; }
	inline const MFDMODESPEC *Oldspec() const { return oldspec; }
};

class Pane;

static char work_kstate[256];
inline char *KstateSet (int key) {
	memset (work_kstate, 0, 256);
	work_kstate[key] = (char)0x80;
	return work_kstate;
}

// =======================================================================
// class Instrument
// base class for virtual instrument types

class Instrument {
	friend class MFD;
	friend class MFD2;

public:
	struct Spec {
		int w, h;       // MFD display size
		int nbtl, nbtr; // number of buttons on left and right side of display
		int bt_y0;      // y-offset of top button centreline from top edge of display
		int bt_dy;      // y-distance between buttons
		oapi::UInt32 flag;     // bit flags
	};

	Instrument (Pane *_pane, std::intptr_t _id, const Spec &spec, Vessel *_vessel, bool defer_alloc=false);
	virtual ~Instrument ();
#ifdef _WIN32
	virtual void RestoreDeviceObjects (LPDIRECT3D7 d3d, LPDIRECT3DDEVICE7 dev) {}
#endif
	virtual int Type () const = 0;                 // mode id
	virtual char ModeSelKey () const = 0;          // mode selection key
	virtual HELPCONTEXT *HelpTopic () const { return 0; } // help topic (CHM file address) if available
	bool ConsumeKeyImmediate (char *kstate);
	bool ConsumeKeyBuffered (oapi::UInt32 key);
	bool ConsumeButton (int bt, int event);
	virtual bool KeyImmediate (char *kstate) { return false; }
	virtual bool KeyBuffered (oapi::UInt32 key) { return false; }

	/**
	 * \brief Called when the user interactively changes a simulation option
	 * \param cat option category (see \ref optcat)
	 * \param item option item (see \ref optitem)
	 */
	virtual void OptionChanged(oapi::UInt32 cat, oapi::UInt32 item);

	virtual bool ProcessButton (int bt, int event) { return false; }
	// used to process buttons in the frame of the MFD (panel mode)

	const char *ButtonLabel (int bt);
	// returns the label to print on the specified MFD button or 0 if not assigned

	virtual const char *BtnLabel (int bt) const { return 0; }
	// overwritten by derived MFDs to specify their button labels
	// bt is 'logical' button number (already contains menu page)

	virtual char *ModeLabel (int bt);
	// button label for MFD mode displayed at button bt. By default, this
	// returns the first 3 characters of the MFD name.

	virtual int BtnMenu (const MFDBUTTONMENU **menu) const
	{ return 0; }

	virtual int ProcessMessage (int msg, void *data)
	{ return 0; }

	virtual bool Update (double upDTscale);
	virtual void UpdateDraw (oapi::Sketchpad *skp) = 0;
#ifdef _WIN32
	virtual void UpdateDraw (oapi::SdkDrawContext hDC) {}
#endif
	virtual void UpdateBlt () {}
	virtual void Timejump ();
	void Refresh (); // force refresh
	void RepaintButtons ();
	Vessel *GetVessel () const { return vessel; }
	virtual void VesselChanged (Vessel *_vessel);
	void SetSize (const Spec &spec, bool defer_alloc = false);
	SURFHANDLE Surface () { return surf; }
	SURFHANDLE Texture () { return tex; }

	bool IsRuningInExternMFD() const { return (id > MAXMFD || id < 0); }

	void DisplayTitle (oapi::Sketchpad *skp, const char *title) const;
	// to be called from UpdateDraw

	void DisplayTitle (oapi::SdkDrawContext hDC, const char *title) const;
	// obsolete

	void DisplayModes (int page);

	oapi::Sketchpad *BeginDraw ();
	void EndDraw (oapi::Sketchpad *skp);
	// Call at the beginning/end of GDI calls to the rendering surface
	// BeginDraw also draws a rectangle around the border of the instrument
	// note that BLT operations are not allowed between Begin and End

	oapi::SdkDrawContext BeginDrawHDC ();
	void EndDrawHDC (oapi::SdkDrawContext hDC);
	// Compatibility versions

	// ******************************************************************
	// **** Default Instrument registration: these functions must be ****
	// ****     updated when a new builtin instrument is defined     ****
	// ******************************************************************

	static Instrument *Create (int type, Pane *_pane,
		std::intptr_t _id, const Spec &spec, Vessel *_vessel, bool restore = true);
	// create instrument of the required type
	// if restore==true then parameters are restored from static saved

	static Instrument *Create (std::ifstream &ifs, Pane *_pane,
		std::intptr_t _id, const Spec &spec, Vessel *_vessel);
	// create instrument from stream

	static void RegisterBuiltinModes ();
	// Define builtin MFD modes. This must be called before registering
	// any user-defined modes.

	// ******************************************************************
	// ****            End default Instrument registration           ****
	// ******************************************************************

	static int RegisterUserMode (MFDMODESPEC *mode);
	// Register a user-defined mode. Must be called after builtin modes
	// have been registered. Returns ID of new mode

	static int RegisterUserMode (MFDMODESPECEX *mode);
	// Register a user-defined mode. Must be called after builtin modes
	// have been registered. Returns ID of new mode

	static bool UnregisterUserMode (int id);
	// Un-register a previously registered user mode
	// Returns false if mode was not found

	static int ModeIdFromKey (oapi::UInt32 key);
	// Returns the id of an instrument mode, given its activation key
	// If no mode matches the key, return value is MFD_NONE

	static int ModeFromNameOld (char *name, MFDMODESPEC **spec = NULL);
	// obsolete

	static int ModeFromName (char *name, MFDMODESPECEX **spec = NULL);
	// Returns the id of an instrument mode, given its name
	// If spec is defined, it points to the mode specs on return
	// If no mode matches the key, return value is MFD_NONE

	int VesselModeFromName (const char *name, MFDMODESPECEX **spec);
	// Returns the id of a vessel-specific mode, given its name
	// If spec is defined, it points to the mode specs on return
	// If no mode matches the key, return value is MFD_NONE

	inline const MFDMODE *GetMode (oapi::UInt32 i) const
	{ return (i < nGlobalModes ? GlobalMode+i :
	          i < nGlobalModes+nVesselModes ?
			  VesselMode+(i-nGlobalModes) : 0); }
	// Return a mode across global and vessel-specific modes

	static int GetUserMode (oapi::UInt32 i, MFDMODESPEC *spec);  // may not be necessary
	int GetMFDMode (char *name, const MFDMODESPECEX **spec) const; // may not be necessary
	int GetMFDModeOld (char *name, const MFDMODESPEC **spec) const; // obsolete

	static int nextmodeid;       // id for next user-defined mode
	static oapi::UInt32 nGlobalModes;   // total number of registered modes
	static MFDMODE *GlobalMode;  // list of pointers to registered modes

	oapi::UInt32 nVesselModes;          // number of registered vessel-specific modes
	const MFDMODE *VesselMode;   // list of vessel-specific modes

	static void DisableMode (int id);
	static void ClearDisabledModes ();
	static bool IsDisabledMode (int id);

	void Write (std::ostream &ofs) const;
	// read/write instrument status from/to stream

	void AllocSurface (oapi::UInt32 w, oapi::UInt32 h);

protected:
	Pane *pane;                 // pointer to pane
	oapi::CockpitClient *gc;   // graphics client, if available
	std::intptr_t id;                	// instrument id
	bool BufKey (char key, double repdelay = 0.5);
	void SetBuf (char key);
	int IW, IH;                 // instrument dimensions
	int cw, ch;                 // character width and height of standard font (hfnt1)
	int nbtl, nbtr;             // number of buttons on left and right side of display
	int nbt;                    // total number of buttons per page
	int bt_y0, bt_dy;           // offset of top button, and button y-distances (pixel)
	int btnpage;                // currently displayed button page
	oapi::UInt32 flag;                 // bit flags
	Vessel *vessel;             // spacecraft to which the instrument refers
	double instrDT;             // instrument update interval
	double updT, updSysT;       // simulation/system time of next update
	double dT, pT;              // last update interval, last update time
	bool blink;                 // flag for blinking objects: alternates true/false
	SURFHANDLE surf;            // MFD drawing surface
	SURFHANDLE tex;             // texture version of MFD display

	// MFD colours
	static oapi::UInt32 col_green1;   // light green
	static oapi::UInt32 col_green2;   // dark green
	static oapi::UInt32 col_yellow1;  // light yellow
	static oapi::UInt32 col_yellow2;  // dark yellow
	static oapi::UInt32 col_grey1;    // light grey
	static oapi::UInt32 col_grey2;    // dark grey
	static oapi::UInt32 col_red1;     // light red

	oapi::Font *GetDefaultFont (oapi::UInt32 fontidx);
	// Returns a predefined font resource

	oapi::SdkFont SelectDefaultFont (oapi::SdkDrawContext hDC, oapi::UInt32 i);
	// obsolete

	oapi::Pen *GetDefaultPen (oapi::UInt32 colidx, oapi::UInt32 intens=0, oapi::UInt32 style=1);
	// Returns a predefined pen resource

#ifdef _WIN32
	HPEN SelectDefaultPen (oapi::SdkDrawContext hDC, oapi::UInt32 i);
#endif
	// obsolete

	oapi::UInt32 GetDefaultColour (oapi::UInt32 colidx, oapi::UInt32 intens) const;
	// Return one of the default MFD colours.

	bool FindScnHeader (std::ifstream &ifs) const;

	virtual bool ReadParams (std::ifstream &ifs) = 0;
	virtual void WriteParams (std::ostream &ofs) const = 0;

	void OpenSelect_CelBody (const char *title, Select::Callbk enter_cbk, oapi::UInt32 flag = 0);
	static bool ClbkSelect_CelBody (Select *menu, int item, char *str, void *data);
	// Open a selection box for a celestial object.
	// The callback function is called if a selection is made.
	// The following bit flags are supported:
	//   1: do not include Star objects

	void OpenSelect_Tgt (const char *title, Select::Callbk enter_cbk, const CelestialBody *ref = 0, oapi::UInt32 flag = 0);
	// Open a selection box for a target object
	// Supported bitflags:
	//   1: don't display 'By name' option
	//   2: don't display other targets than those orbiting 'ref'

	// Drawing resources
	oapi::Font *mfdfont[4];     // MFD font resources
	bool use_skp_interface;     // true if drawing through Sketchpad, false for oapi::SdkDrawContext

public:
	static struct DrawResource { // MFD drawing resources
		oapi::UInt32 col;
		oapi::Pen *solidpen;
		oapi::Pen *dashpen;
	} draw[MAXDEFCOL][2];  // first index: colour scheme, second index: intensity (0=bright, 1=dim)

#ifdef _WIN32
	static HPEN hdefpen[MAXPEN];       // deprecated pen resources
#endif

	static void GlobalInit (oapi::CockpitClient *gc);
	static void GlobalExit (oapi::CockpitClient *gc);

private:
	void ReleaseSurface ();
	void ClearSurface ();
	// allocate/deallocate/wipe instrument surface buffer 'surf'

	void DrawMenu ();

	static bool ClbkSelect_Tgt (Select *menu, int item, char *str, void *data);
	static bool ClbkEnter_Tgt (Select *menu, int item, char *str, void *data);
	static bool ClbkName_Tgt (InputBox*, char *str, void *data);
	// internal callback functions for generic selection dialogs

	static oapi::UInt32 SelCelBodyFlag;
	static struct SelTgtPrm {
		Select::Callbk clbk;
		char title[256];
		const CelestialBody *ref;
		oapi::UInt32 flag;
	} seltgtprm;

	int modepage;               // currently displayed modepage (-1=none)

	char lastkey;               // last key consumed in buffered mode
	double lastkeytime;         // time of last buffered key
	bool showmenu;              // show button menu instead of regular MFD display
	bool pageonmenu;            // combine menu and page buttons

	static oapi::UInt32 nDisabledModes;  // number of disabled MFD modes
	static int *DisabledModes;    // list of disabled MFD modes
};


#endif // !__MFD_H