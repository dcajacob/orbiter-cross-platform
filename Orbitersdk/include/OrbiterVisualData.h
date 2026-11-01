// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_VISUAL_DATA_H
#define ORBITER_VISUAL_DATA_H

// Unchanged SDK values and star settings; no window or renderer ownership.
/// \defgroup cfgprm Configuration parameter identifiers
/// Used by GraphicsClient::GetConfigParam()
/// @{

/// Max. level of detail for rendering planetary surfaces
/// \par Parameter type:
///   DWORD
#define CFGPRM_SURFACEMAXLEVEL 0x0001

/// Flag for rendering planet surfaces with specular reflections
/// (e.g. for oceans)
/// \par Parameter type:
///   bool
#define CFGPRM_SURFACEREFLECT  0x0002

/// Flag for rendering specular reflections with microtexture
/// ("ripples")
/// \par Parameter type:
///   bool
#define CFGPRM_SURFACERIPPLE   0x0003

/// Flag for rendering emissive textures ("city lights") on the
/// unlit side of planetary surfaces.
/// \par Parameter type:
///   bool
#define CFGPRM_SURFACELIGHTS   0x0004

/// Brightness factor for emissive city light textures (0-1)
/// \par Parameter type:
///   double
#define CFGPRM_SURFACELIGHTBRT 0x0006

/// Flag for rendering "atmospheric haze" over planets with
/// atmospheres
/// \par Parameter type:
///   bool
#define CFGPRM_ATMHAZE         0x0007

/// Flag for rendering distance fog within planetary atmospheres
/// \par Parameter type:
///   bool
#define CFGPRM_ATMFOG          0x0008

/// Flag for rendering planetary cloud layers
/// \par Parameter type:
///   bool
#define CFGPRM_CLOUDS          0x0009

/// Flag for rendering cloud shadows on the planet surface
/// \par Parameter type:
///   bool
#define CFGPRM_CLOUDSHADOWS    0x000A

/// Bit flag for "planetarium mode" elements.
/// For a description of the available bit flags, see \ref plnflag
/// \par Parameter type:
///   DWORD
#define CFGPRM_PLANETARIUMFLAG 0x000B

/**
 * Parameters for rendering stars on the celestial sphere.
 * \par Parameter type:
 *   struct StarRenderPrm
 */
#define CFGPRM_STARRENDERPRM 0x000C

/**
 * Ambient light level (brightness of unlit nonemissive surfaces)
 * in the range 0-255.
 * \par Parameter type:
 *   DWORD
 */
#define CFGPRM_AMBIENTLEVEL    0x000E

/**
 * Flag for rendering vessel shadows on the planet surface
 * \par Parameter type:
 *   bool
 */
#define CFGPRM_VESSELSHADOWS   0x000F

/**
 * Flag for rendering object shadows on the planet surface
 * \par Parameter type:
 *   bool
 */
#define CFGPRM_OBJECTSHADOWS   0x0010

/**
 * Flag for enabling specular reflections from objects
 * \par Parameter type:
 *   bool
 */
#define CFGPRM_OBJECTSPECULAR  0x0011

/**
 * \Flag for rendering background images from a texture set
 * \par Parameter type:
 *    bool
 */
#define CFGPRM_CSPHEREUSEBGIMAGE 0x0012

/**
 * File path for celestial sphere background textures
 * \par Parameter type:
 *   *char
 */
#define CFGPRM_CSPHERETEXTURE 0x0013

/**
 * Flag for rendering intensity of celestial sphere background textures
 * \par Parameter type:
 *   double
 */
#define CFGPRM_CSPHEREINTENS 0x0014

/**
 * Flag for enabling local light sources
 * \par Parameter type:
 *   bool
 */
#define CFGPRM_LOCALLIGHT 0x0015

/**
 * Max number of light sources
 * \par Parameter type:
 *   int
 */
#define CFGPRM_MAXLIGHT 0x0016

/**
 * Planet tile resolution bias
 * \par Parameter type:
 *   double
 */
#define CFGPRM_RESOLUTIONBIAS 0x0017

/**
 * Render meshes as wireframe models?
 * \par Parameter type:
 *   bool
 */
#define CFGPRM_WIREFRAME 0x0018

/**
 * Mesh interpolation method for planetary surfaces
 * (0=none, 1=linear, 2=cubic)
 * \par Parameter type:
 *   int
 */
#define CFGPRM_ELEVATIONMODE 0x0019

/**
 * Size of texture surface used for rendering panel MFDs and VC HUD
 * (multiple of 2, usually 256 or 512)
 * \par Parameter type:
 *   int
 */
#define CFGPRM_PANELMFDHUDSIZE 0x001A

/**
 * Scaling power n of planet surface patch mesh resolution 2 << n
 * Valid range: [4,5,6]
 * \par Parameter type:
 *   int
 */
#define CFGPRM_TILEPATCHRES 0x001B

/**
 * Bitflags for planetary tile file load behaviour
 * - bit 1: load from individual tiles in directory tree
 * - bit 2: load from compressed archive file
 * \par Parameter type:
 *   DWORD
 */
#define CFGPRM_TILELOADFLAGS 0x001C

/**
 * Path to background star texture
 * \par Parameter type:
 *   *char
 */
#define CFGPRM_CSPHERESTARTEXTURE 0x001D

/**
 * \Flag for rendering background stars from a texture set
 * \par Parameter type:
 *    bool
 */
#define CFGPRM_CSPHEREUSESTARIMAGE 0x001E

/**
 * \Flag for rendering background stars as pixels
 * \par Parameter type:
 *    bool
 */
#define CFGPRM_CSPHEREUSESTARDOTS 0x001F

/**
 * Bit flags for force vector display options.
 * For a description of the available bit flags, see \ref bfvflag
 * \par Parameter type:
 *   DWORD
 */
#define CFGPRM_FORCEVECTORFLAG 0x0020

/**
 * Force vector display scaling factor
 * \par Parameter type:
 *   float
 */
#define CFGPRM_FORCEVECTORSCALE 0x0021

/**
 * Force vector display opacity value
 * \par Parameter type:
 *   float
 */
#define CFGPRM_FORCEVECTOROPACITY 0x0022

/**
 * Bit flags for frame axis display options.
 * For a description of the available bit flags, see \ref favflag
 * \par Parameter type:
 *   DWORD
 */
#define CFGPRM_FRAMEAXISFLAG 0x0023

/**
 * Frame axis display scaling factor
 * \par Parameter type:
 *   float
 */
#define CFGPRM_FRAMEAXISSCALE 0x0024

/**
 * Frame axis display opacity value
 * \par Parameter type:
 *   float
 */
#define CFGPRM_FRAMEAXISOPACITY 0x0025

 /**
  * Bit flags for surface and object marker display options.
  * For a description of the available bit flags, see \ref mkrflag
  * \par Parameter type:
  *   DWORD
  */
#define CFGPRM_SURFMARKERFLAG 0x0026
/// @}

/**
 * \defgroup renderprm Render parameter identifiers
 * \sa GraphicsClient::clbkGetRenderParam()
 */
/// @{
#define RP_COLOURDEPTH        1 ///< colour bit depth of the render target
#define RP_ZBUFFERDEPTH       2 ///< z-buffer depth of the render target
#define RP_STENCILDEPTH       3 ///< stencil buffer depth of the render target
#define RP_MAXLIGHTS          4 ///< maximum number of simultaneous light sources supported
#define RP_ISTLDEVICE         5 ///< render device supports Transform&Lighting
#define RP_REQUIRETEXPOW2     6 ///< texture size=pow2 required? (0=no, 1=yes, 2=conditional)
/// @}

/// \defgroup plnflag Bit flags for planetarium mode elements
/// @{
#define PLN_ENABLE    0x0001 ///< Enable planetarium mode (master flag)
#define PLN_CGRID     0x0002 ///< Enable celestial grid
#define PLN_EGRID     0x0004 ///< Enable ecliptic grid
#define PLN_GGRID     0x0008 ///< Enable galactic grid
#define PLN_HGRID     0x0010 ///< Enable local horizon grid
#define PLN_EQU       0x0020 ///< Enable target body equator
#define PLN_CONST     0x0040 ///< Enable constellation patterns
#define PLN_CNSTLABEL 0x0080 ///< Enable constellation labels
#define PLN_CNSTLONG  0x0100 ///< Enable long constellation names
#define PLN_CNSTBND   0x0200 ///< Enable constellation boundaries
#define PLN_CCMARK    0x0400 ///< Enable celestial sphere labels
/// @}

/// \defgroup mkrflag Bit flags for surface and object markers
/// @{
#define MKR_ENABLE    0x0001 ///< Enable surface and object markers
#define MKR_CMARK     0x0002 ///< Enable solar system body markers
#define MKR_VMARK     0x0004 ///< Enable vessel markers
#define MKR_BMARK     0x0008 ///< Enable surface base markers
#define MKR_RMARK     0x0010 ///< Enable VOR transmitter markers
#define MKR_LMARK     0x0020 ///< Enable planetary surface labels
#define MKR_SURFMARK (MKR_BMARK | MKR_RMARK | MKR_LMARK)
/// @}

/// \defgroup bfvflag Bit flags for vessel force vector render options
/// @{
#define BFV_ENABLE    0x0001 ///< Enable body force vectors
#define BFV_LOGSCALE  0x0002 ///< Use logarithmic scale (instead of linear scale)
#define BFV_WEIGHT    0x0004 ///< Show weight vector
#define BFV_THRUST    0x0008 ///< Show thrust vector
#define BFV_LIFT      0x0010 ///< Show lift vector
#define BFV_DRAG      0x0020 ///< Show drag vector
#define BFV_TOTAL     0x0040 ///< Show total force vector
#define BFV_TORQUE    0x0080 ///< Show torque vector
#define BFV_SIDEFORCE 0x0100 ///< Show side-force vector
/// @}

/// \defgroup favflag Bit flags for frame axis vector render options
/// @{
#define FAV_ENABLE    0x0001 ///< Enable frame axis vector display
#define FAV_NEGATIVE  0x0002 ///< Also show negative axes
#define FAV_VESSEL    0x0004 ///< Show vessel frame axes
#define FAV_CELBODY   0x0008 ///< Show celestial body frame axes
#define FAV_BASE      0x0010 ///< Show surface base frame axes
/// @}

/// \defgroup bltflag Bit flags for blitting operations
/// @{
#define BLT_SRCCOLORKEY 0x1 ///< Use source surface colour key for transparency
#define BLT_TGTCOLORKEY 0x2 ///< Use target surface colour key for transparency
/// @}

struct StarRenderPrm {
	double mag_hi;
	double mag_lo;
	double brt_min;
	bool   map_log;
};

#endif
