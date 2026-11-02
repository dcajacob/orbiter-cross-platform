// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_COCKPIT_DATA_H
#define ORBITER_COCKPIT_DATA_H
#include "OrbiterValueTypes.h"
#include "OrbiterSdkDrawingTypes.h"
#include "OrbiterGeometry.h"
#include "OrbiterHandles.h"
namespace oapi {
#ifdef _WIN32
#ifdef _WIN64
using CockpitMessageResult=LRESULT;
#else
using CockpitMessageResult=int;
#endif
using CockpitUnsignedParam=WPARAM;
using CockpitSignedParam=LPARAM;
#else
using CockpitMessageResult=std::intptr_t;
using CockpitUnsignedParam=std::uintptr_t;
using CockpitSignedParam=std::intptr_t;
#endif
}
typedef struct {
	oapi::SdkRectangle pos;
	int nbt_left, nbt_right;
	int bt_yofs, bt_ydist;
} MFDSPEC;

typedef struct {
	oapi::UInt32 nmesh, ngroup;
} VCMFDSPEC;

#define MFD_SHOWMODELABELS       0x0001
#define MFD_TRANSPARENT_WHEN_OFF 0x0002

typedef struct {
	oapi::SdkRectangle pos;
	oapi::UInt32 nmesh, ngroup;
	oapi::UInt32 flag;
	int nbt1, nbt2;
	int bt_yofs, bt_ydist;
} EXTMFDSPEC;

typedef struct {
	oapi::UInt32 nmesh, ngroup;
	VECTOR3 hudcnt;
	double size;
} VCHUDSPEC;

typedef struct {
	int W, H;
	int CX, CY;
	double Scale;
	int Markersize;
} HUDPAINTSPEC;

typedef struct {
	char *name;
	oapi::UInt32 key;
	oapi::CockpitMessageResult (*msgproc)(oapi::UInt,oapi::UInt,oapi::CockpitUnsignedParam,oapi::CockpitSignedParam);
} MFDMODESPEC;

typedef struct {
	char *name;
	oapi::UInt32 key;
	void *context;
	oapi::CockpitMessageResult (*msgproc)(oapi::UInt,oapi::UInt,oapi::CockpitUnsignedParam,oapi::CockpitSignedParam);
} MFDMODESPECEX;

typedef struct {
	int w, h;
	MFDMODESPECEX *spec;
} MFDMODEOPENSPEC;

#pragma pack(push,1)
typedef struct {
	const char *line1, *line2;
	char selchar;
} MFDBUTTONMENU;
#pragma pack(pop)

// ===========================================================================
/// \ingroup defines
/// \defgroup hudmode HUD mode identifiers
///  These constants are used to refer to the built-in HUD (head-up display) modes.
// ===========================================================================
//@{
#define HUD_NONE                 0 ///< No mode (turn HUD off)
#define HUD_ORBIT                1 ///< Orbit HUD mode
#define HUD_SURFACE              2 ///< Surface HUD mode
#define HUD_DOCKING              3 ///< Docking HUD mode
//@}

/**
 * \brief Mode-specific parameters for HUD mode settings
 * \sa oapiSetHUDMode(int,const HUDPARAM*)
 */
typedef union {
	struct {
		OBJHANDLE hRef;   ///< orbit HUD reference object (NULL for auto)
	} HUDorbit;
	struct {
		oapi::UInt32 NavIdx;       ///< docking HUD nav receiver index (>= 0)
	} HUDdocking;
} HUDPARAM;

// ===========================================================================
/// \ingroup defines
/// \defgroup mfdmode MFD mode identifiers
/// These constants are used to refer to the built-in MFD (multifunctional display) modes.
// ===========================================================================
//@{
#define MFD_REFRESHBUTTONS      -1 ///< Refresh MFD buttons
#define MFD_NONE                 0 ///< No mode (turn MFD off)
#define MFD_ORBIT                1 ///< Orbit MFD mode
#define MFD_SURFACE              2 ///< Surface MFD mode
#define MFD_MAP                  3 ///< Map MFD mode
#define MFD_HSI                  4 ///< HSI (horizontal situation indicator) MFD mode
#define MFD_LANDING              5 ///< VTOL support MFD mode
#define MFD_DOCKING              6 ///< Docking support MFD mode
#define MFD_OPLANEALIGN          7 ///< Orbital plane alignment MFD mode
#define MFD_OSYNC                8 ///< Orbit synchronisation MFD mode
#define MFD_TRANSFER             9 ///< Transfer orbit MFD mode
#define MFD_COMMS               10 ///< Communications MFD mode
#define MFD_USERTYPE            64 ///< User-defined MFD mode
#define BUILTIN_MFD_MODES       10 ///< Number of built-in MFD modes
//@}

// ===========================================================================
/// \ingroup defines
/// \defgroup mfdidentifier MFD identifiers
// ===========================================================================
//@{
#define MAXMFD                  12  ///< Max. number of MFD displays per panel
#define MFD_LEFT                 0  ///< Left default MFD display
#define MFD_RIGHT                1  ///< Right default MFD display
#define MFD_USER1                2  ///< User-defined MFD display 1
#define MFD_USER2                3  ///< User-defined MFD display 2
#define MFD_USER3                4  ///< User-defined MFD display 3
#define MFD_USER4                5  ///< User-defined MFD display 4
#define MFD_USER5                6  ///< User-defined MFD display 5
#define MFD_USER6                7  ///< User-defined MFD display 6
#define MFD_USER7                8  ///< User-defined MFD display 7
#define MFD_USER8                9  ///< User-defined MFD display 8
#define MFD_USER9               10  ///< User-defined MFD display 9
#define MFD_USER10              11  ///< User-defined MFD display 10
//@}
#define PANEL_MOUSE_IGNORE      0x00 ///< Don't generate mouse events
#define PANEL_MOUSE_LBDOWN      0x01 ///< Left button down event
#define PANEL_MOUSE_RBDOWN      0x02 ///< Right button down event
#define PANEL_MOUSE_LBUP        0x04 ///< Left button release event
#define PANEL_MOUSE_RBUP        0x08 ///< Right button release event
#define PANEL_MOUSE_LBPRESSED   0x10 ///< Left button down (continuous)
#define PANEL_MOUSE_RBPRESSED   0x20 ///< Right button down (continuous)
#define PANEL_MOUSE_DOWN        0x03 ///< Composite down event
#define PANEL_MOUSE_UP          0x0C ///< Composite release event
#define PANEL_MOUSE_PRESSED     0x30 ///< Composite down (continous)
#define PANEL_MOUSE_ONREPLAY    0x40 ///< Create mouse events during replay
#endif
