// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PLANET_DATA_H
#define ORBITER_PLANET_DATA_H
// ===========================================================================
/// \ingroup defines
/// \defgroup objprm Object parameter flags
/// Used by oapiGetObjectParam()
// ===========================================================================
//@{
/**
 * \brief Max. resolution level for planet surface rendering.
 *   (Parameter type: DWORD)
 */
#define OBJPRM_PLANET_SURFACEMAXLEVEL    0x0001

/**
 * \brief Flag for ripple effect on reflective surfaces
 *   (Parameter type: bool)
 */
#define OBJPRM_PLANET_SURFACERIPPLE      0x0002

/**
 * \brief Bleed-in factor of atmospheric haze into planet disc.
 *   (Parameter type: double; range: 0-0.9)
 */
#define OBJPRM_PLANET_HAZEEXTENT         0x0003

/**
 * \brief Density at which the horizon haze is rendered (basic
 *   density is calculated from atmospheric density) Default: 1.0.
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_HAZEDENSITY        0x0004

#define OBJPRM_PLANET_HAZESHIFT          0x0005
#define OBJPRM_PLANET_HAZECOLOUR         0x0006
#define OBJPRM_PLANET_FOGPARAM           0x0007
#define OBJPRM_PLANET_SHADOWCOLOUR       0x0008
#define OBJPRM_PLANET_HASCLOUDS          0x0009
#define OBJPRM_PLANET_CLOUDALT           0x000A
#define OBJPRM_PLANET_CLOUDROTATION      0x000B

/**
 * \brief Depth of cloud shadows
 *   (parameter type: float)
 */
#define OBJPRM_PLANET_CLOUDSHADOWCOL     0x000C

#define OBJPRM_PLANET_CLOUDMICROTEX      0x000D
#define OBJPRM_PLANET_CLOUDMICROALTMIN   0x000E
#define OBJPRM_PLANET_CLOUDMICROALTMAX   0x000F
#define OBJPRM_PLANET_HASRINGS           0x0010
#define OBJPRM_PLANET_RINGMINRAD         0x0011
#define OBJPRM_PLANET_RINGMAXRAD         0x0012

/**
 * \brief Altitude [m] up to which an atmosphere attenuates
 *   light cast from the sun on a spacecraft.
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_ATTENUATIONALT     0x0013

/**
 * \brief Planet tile engine version (1 or 2)
 *   (Parameter type: int)
 */
#define OBJPRM_PLANET_TILEENGINE         0x0014

/**
 * \brief Planet cloud tile engine version (1 or 2)
 *   (Parameter type: int)
 */
#define OBJPRM_PLANET_CLOUDTILEENGINE    0x0015

/**
 * \brief Atmospheric tint colour. This colour is mixed into
 *   the surface textures when seen through an atmospheric layer.
 *   (Parameter type: VECTOR3)
 */
#define OBJPRM_PLANET_ATMTINTCOLOUR      0x0016

/**
 * \brief Max. resolution level for cloud layer rendering
 *   (Parameter type: int)
 */
#define OBJPRM_PLANET_CLOUDMAXLEVEL      0x0017

/**
 * \brief Enhance cloud brightness?
 *   (Parameter type: bool)
 */
#define OBJPRM_PLANET_CLOUDOVERSATURATE  0x0018

/**
 * \brief Extend horizon visibility radius (avoid disappearing
 *    mountaintop artefacts)
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_HORIZONEXCESS      0x0019

/**
 * \brief Extend tile bounding box (avoid disappearing tiles
 *   for irregular shaped bodies)
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_TILEBBEXCESS       0x001A

/**
 * \brief Minimum planet elevation [m] relative to mean radius.
 *   Used to adjust lower horizon edge for rendering
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_MINELEVATION		 0x001B

/**
 * \brief Target resolution for elevation data [m]
 *   Elevation data loaded from file are rescaled to this resolution
 *   (Parameter type: double)
 */
#define OBJPRM_PLANET_ELEVRESOLUTION     0x001D

/**
 * \brief Planet surface label engine version (1 or 2)
 *   (Parameter type: int)
 */
#define OBJPRM_PLANET_LABELENGINE        0x001E

 /**
  * \brief Maximum planet elevation [m] relative to mean radius.
  *   (Parameter type: double)
  */
#define OBJPRM_PLANET_MAXELEVATION		 0x001F

//@}
#endif
