// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_SIMULATION_DATA_H
#define ORBITER_SIMULATION_DATA_H
#include "OrbiterValueTypes.h"
#include "OrbiterGeometry.h"
#include "OrbiterMeshData.h"

typedef struct {
	oapi::UInt32 flags;   ///< flags (see \ref grpedit)
	oapi::UInt32 UsrFlag; ///< Replacement for group UsrFlag entry
	NTVERTEX *Vtx; ///< Replacement for group vertices
	oapi::UInt32 nVtx;    ///< Number of vertices to be replaced
	oapi::UInt16 *vIdx;    ///< Index list for vertices to be replaced
} GROUPEDITSPEC;
typedef struct {
	NTVERTEX *Vtx;  ///< Vertex buffer
	oapi::UInt32 nVtx;     ///< Number of vertices to return
	oapi::UInt16 *VtxPerm;  ///< Vertex permutation index list
	oapi::UInt16 *Idx;      ///< Triangle index buffer
	oapi::UInt32 nIdx;     ///< Number of indices to return
	oapi::UInt16 *IdxPerm;  ///< Triangle permutation index list
	oapi::UInt32 MtrlIdx;  ///< Material index
	oapi::UInt32 TexIdx;   ///< Texture index
} GROUPREQUESTSPEC;
typedef struct {
	double a;          ///< semi-major axis [m]
	double e;          ///< eccentricity
	double i;          ///< inclination [rad]
	double theta;      ///< longitude of ascending node [rad]
	double omegab;     ///< longitude of periapsis [rad]
	double L;          ///< mean longitude at epoch
} ELEMENTS;
typedef struct {
	double SMi;        ///< semi-minor axis [m]
	double PeD;        ///< periapsis distance [m]
	double ApD;        ///< apoapsis distance [m]
	double MnA;        ///< mean anomaly [rad]
	double TrA;        ///< true anomaly [rad]
	double MnL;        ///< mean longitude [rad]
	double TrL;        ///< true longitude [rad]
	double EcA;        ///< eccentric anomaly [rad]
	double Lec;        ///< linear eccentricity [m]
	double T;          ///< orbit period [s]
	double PeT;        ///< time to next periapsis passage [s]
	double ApT;        ///< time to next apoapsis passage [s]
} ORBITPARAM;
typedef struct {
	double main;       ///<     -1 (full retro) .. +1 (full main)
	double hover;      ///<     0 .. +1 (full hover)
	int attmode;       ///<     0=rotation, 1=translation
} ENGINESTATUS;
#define EXHAUST_CONSTANTLEVEL 0x0001 ///< exhaust level is constant
#define EXHAUST_CONSTANTPOS   0x0002 ///< exhaust position is constant
#define EXHAUST_CONSTANTDIR   0x0004 ///< exhaust direction is constant
#define EVENT_VESSEL_INSMESH      0 ///< Insert a mesh (context: mesh index)
#define EVENT_VESSEL_DELMESH      1 ///< Delete a mesh (context: mesh index, or -1 for all)
#define EVENT_VESSEL_MESHVISMODE  2 ///< Set mesh visibility mode (context: mesh index)
#define EVENT_VESSEL_RESETANIM    3 ///< Reset animations
#define EVENT_VESSEL_CLEARANIM    4 ///< Clear all animations (context: oapi::UInt (1=reset animations, 0=leave animations at current state)
#define EVENT_VESSEL_DELANIM      5 ///< Delete an animation (context: animation index)
#define EVENT_VESSEL_NEWANIM      6 ///< Create a new animation (context: animation index)
#define EVENT_VESSEL_MESHOFS      7 ///< Shift a mesh (context: mesh index)
#define EVENT_VESSEL_MODMESHGROUP 8 ///< A mesh group has been modified
#define NAVBIT_KILLROT    0x01
#define NAVBIT_HLEVEL     0x02
#define NAVBIT_PROGRADE   0x04
#define NAVBIT_RETROGRADE 0x08
#define NAVBIT_NORMAL     0x10
#define NAVBIT_ANTINORMAL 0x20
#define NAVBIT_HOLDALT    0x40
#define PROP_ORBITAL             0x0F
#define PROP_ORBITAL_ELEMENTS    0x00
#define PROP_ORBITAL_FIXEDSTATE  0x01
#define PROP_ORBITAL_FIXEDSURF   0x02
#define PROP_SORBITAL            0xF0
#define PROP_SORBITAL_ELEMENTS   (0x0 << 4)
#define PROP_SORBITAL_FIXEDSTATE (0x1 << 4)
#define PROP_SORBITAL_FIXEDSURF  (0x2 << 4)
#define PROP_SORBITAL_DESTROY    (0x3 << 4)
#define PANEL_REDRAW_NEVER      0x0000 ///< Don't generate redraw events
#define PANEL_REDRAW_ALWAYS     0x0001 ///< Generate event at each frame
#define PANEL_REDRAW_MOUSE      0x0002 ///< Generate event on mouse event
#define PANEL_REDRAW_INIT       0x0003 ///< Initialisation event
#define PANEL_REDRAW_USER       0x0004 ///< User-generated event
#define PANEL_REDRAW_GDI        0x1000 ///< Allow GDI access during redraw events
#define PANEL_REDRAW_SKETCHPAD  0x2000 ///< Allow Sketchpad access during redraw events
#define MESHVIS_NEVER          0x00  ///< Mesh is never visible
#define MESHVIS_EXTERNAL       0x01  ///< Mesh is visible in external views
#define MESHVIS_COCKPIT        0x02  ///< Mesh is visible in all internal (cockpit) views
#define MESHVIS_ALWAYS         (MESHVIS_EXTERNAL|MESHVIS_COCKPIT) ///< Mesh is always visible
#define MESHVIS_VC             0x04  ///< Mesh is only visible in virtual cockpit internal views
#define MESHVIS_EXTPASS        0x10  ///< Visibility modifier: render mesh during external pass, even for internal views
const oapi::UInt ALLDOCKS = (oapi::UInt)-1;
#define OPTCAT_CELSPHERE                     0x0001
#define OPTCAT_PLANETARIUM                   0x0002
#define OPTCAT_INSTRUMENT                    0x0003
#define OPTCAT_VESSEL                        0x0004
#define OPTCAT_JOYSTICK                      0x0005
#define OPTITEM_CELSPHERE_ACTIVATESTARDOTS   0x0001
#define OPTITEM_CELSPHERE_STARDISPLAYPARAM   0x0002
#define OPTITEM_CELSPHERE_ACTIVATESTARIMAGE  0x0003
#define OPTITEM_CELSPHERE_STARIMAGECHANGED   0x0004
#define OPTITEM_CELSPHERE_ACTIVATEBGIMAGE    0x0005
#define OPTITEM_CELSPHERE_BGIMAGECHANGED     0x0006
#define OPTITEM_CELSPHERE_BGIMAGEBRIGHTNESS  0x0007
#define OPTITEM_PLANETARIUM_DISPFLAG         0x0001
#define OPTITEM_INSTRUMENT_MFDUPDATEINTERVAL 0x0001
#define OPTITEM_INSTRUMENT_MFDGENERICSIZE    0x0002
#define OPTITEM_INSTRUMENT_MFDGENERICTRANSP  0x0003
#define OPTITEM_INSTRUMENT_MFDVCSIZE         0x0004
#define OPTITEM_INSTRUMENT_PANELSCROLLSPEED  0x0005
#define OPTITEM_INSTRUMENT_PANELSCALE        0x0006
#define OPTITEM_VESSEL_LIMITEDFUEL           0x0001
#define OPTITEM_VESSEL_PADREFUEL             0x0002
#define OPTITEM_JOYSTICK_DEVICE              0x0001
#define OPTITEM_JOYSTICK_PARAM               0x0002
#endif
