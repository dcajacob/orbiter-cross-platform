// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Native source SDK graphics records, with the original field order/values.
#ifndef ORBITER_NATIVE_GRAPHICS_DATA_H
#define ORBITER_NATIVE_GRAPHICS_DATA_H
#include "NativeVesselAPI.h"
#include "OrbiterVisualData.h"
#include "OrbiterPlanetData.h"
#include "OrbiterSdkDrawingTypes.h"
enum FontStyle {
	FONT_NORMAL = 0x0,
	FONT_BOLD = 0x1,
	FONT_ITALIC = 0x2,
	FONT_UNDERLINE = 0x4,
	FONT_STRIKEOUT = 0x8,
	FONT_CRISP = 0x10,			///< Override app-default, No Antialiasing
	FONT_ANTIALIAS = 0x20		///< Override app-default, Use Antialiashing
};
namespace oapi {
	enum ImageFileFormat {
		IMAGE_BMP = 0,
		IMAGE_PNG = 1,
		IMAGE_JPG = 2,
		IMAGE_TIF = 3,
		IMAGE_DDS = 4	///< D3D9+ only
	};
}
#define OAPISURFACE_TEXTURE      0x0001 ///< Surface can be used as a texture (e.g. by associating it with a mesh)
#define OAPISURFACE_RENDERTARGET 0x0002 ///< Surface can be rendered to by the graphics device
#define OAPISURFACE_GDI          0x0004 ///< A HDC context can be requested from the surface for GDI drawing
#define OAPISURFACE_SKETCHPAD    0x0008 ///< A Sketchpad context can be requested from the surface for Sketchpad drawing
#define OAPISURFACE_MIPMAPS      0x0010 ///< Create a full chain of mipmaps for the surface. If loaded from file, add any missing mipmap levels
#define OAPISURFACE_NOMIPMAPS    0x0020 ///< Don't create mipmaps. If loaded from file, ignore any mipmap levels present
#define OAPISURFACE_ALPHA        0x0040 ///< Create an alpha channel for the surface. If loaded from file, add an alpha channel if required
#define OAPISURFACE_NOALPHA      0x0080 ///< Don't create an alpha channel. If loaded from file, strip any existing alpha channel
#define OAPISURFACE_UNCOMPRESS   0x0100 ///< Create an uncompressed surface. If loaded from file, uncompress if required.
#define OAPISURFACE_SYSMEM       0x0200 ///< Create the surface in system (host) memory
#define OAPISURFACE_RENDER3D     0x0400 ///< Create a surface that can act as a target for rendering a 3D scene
#define OAPISURFACE_ANTIALIAS    0x0800 ///< Create a surface with anti-aliasing the level will depend on launchpad settings.
#define OAPISURFACE_SHARED		 0x1000 ///< Create a shared resource
typedef struct {
	NTVERTEX *Vtx;     ///< vertex list
	oapi::UInt16 *Idx;         ///< index list
	oapi::UInt32 nVtx;        ///< vertex count
	oapi::UInt32 nIdx;        ///< index count
	oapi::UInt32 MtrlIdx;     ///< material index (>= 1, 0=none)
	oapi::UInt32 TexIdx;      ///< texture index (>= 1, 0=none)
	oapi::UInt32 UsrFlag;     ///< user-defined flag
	oapi::UInt16 zBias;        ///< z bias
	oapi::UInt16 Flags;        ///< internal flags
} MESHGROUP;

const oapi::UInt32 MAXTEX = 1;  // max. extra textures per mesh group

/**
 * \ingroup structures
 * \brief extended mesh group definition
 */
typedef struct {
	NTVERTEX *Vtx;     ///< vertex list
	oapi::UInt16 *Idx;         ///< index list
	oapi::UInt32 nVtx;        ///< vertex count
	oapi::UInt32 nIdx;        ///< index count
	oapi::UInt32 MtrlIdx;     ///< material index (>= 1, 0=none)
	oapi::UInt32 TexIdx;      ///< texture index (>= 1, 0=none)
	oapi::UInt32 UsrFlag;     ///< user-defined flag
	oapi::UInt16 zBias;        ///< z bias
	oapi::UInt16 Flags;        ///< internal flags
	oapi::UInt32 TexIdxEx[MAXTEX]; ///< additional texture indices
	float TexMixEx[MAXTEX]; ///< texture mix values
} MESHGROUPEX;
const oapi::UInt TEXIDX_MFD0=oapi::UInt(-1)-MAXMFD;
#define SURF_NO_CK 0xFFFFFFFF
#define MESHPROPERTY_MODULATEMATALPHA 1

#define GRPEDIT_SETUSERFLAG 0x00001 ///< replace the group's UsrFlag entry with the value in the GROUPEDITSPEC structure.
#define GRPEDIT_ADDUSERFLAG 0x00002 ///< Add the UsrFlag value to the group's UsrFlag entry
#define GRPEDIT_DELUSERFLAG 0x00004 ///< Remove the UsrFlag value from the group's UsrFlag entry
#define GRPEDIT_VTXCRDX     0x00008 ///< Replace vertex x-coordinates
#define GRPEDIT_VTXCRDY     0x00010 ///< Replace vertex y-coordinates
#define GRPEDIT_VTXCRDZ     0x00020 ///< Replace vertex z-coordinates
#define GRPEDIT_VTXCRD      (GRPEDIT_VTXCRDX | GRPEDIT_VTXCRDY | GRPEDIT_VTXCRDZ) ///< Replace vertex coordinates
#define GRPEDIT_VTXNMLX     0x00040 ///< Replace vertex x-normals
#define GRPEDIT_VTXNMLY     0x00080 ///< Replace vertex y-normals
#define GRPEDIT_VTXNMLZ     0x00100 ///< Replace vertex z-normals
#define GRPEDIT_VTXNML      (GRPEDIT_VTXNMLX | GRPEDIT_VTXNMLY | GRPEDIT_VTXNMLZ) ///< Replace vertex normals
#define GRPEDIT_VTXTEXU     0x00200 ///< Replace vertex texture u-coordinates
#define GRPEDIT_VTXTEXV     0x00400 ///< Replace vertex texture v-coordinates
#define GRPEDIT_VTXTEX      (GRPEDIT_VTXTEXU | GRPEDIT_VTXTEXV) ///< Replace vertex texture coordinates
#define GRPEDIT_VTX         (GRPEDIT_VTXCRD | GRPEDIT_VTXNML | GRPEDIT_VTXTEX) ///< Replace vertices
#define GRPEDIT_VTXCRDADDX  0x00800 ///< Add to vertex x-coordinates
#define GRPEDIT_VTXCRDADDY  0x01000 ///< Add to vertex y-coordinates
#define GRPEDIT_VTXCRDADDZ  0x02000 ///< Add to vertex z-coordinates
#define GRPEDIT_VTXCRDADD   (GRPEDIT_VTXCRDADDX | GRPEDIT_VTXCRDADDY | GRPEDIT_VTXCRDADDZ) ///< Add to vertex coordinates
#define GRPEDIT_VTXNMLADDX  0x04000 ///< Add to vertex x-normals
#define GRPEDIT_VTXNMLADDY  0x08000 ///< Add to vertex y-normals
#define GRPEDIT_VTXNMLADDZ  0x10000 ///< Add to vertex z-normals
#define GRPEDIT_VTXNMLADD   (GRPEDIT_VTXNMLADDX | GRPEDIT_VTXNMLADDY | GRPEDIT_VTXNMLADDZ) ///< Add to vertex normals
#define GRPEDIT_VTXTEXADDU  0x20000 ///< Add to vertex texture u-coordinates
#define GRPEDIT_VTXTEXADDV  0x40000 ///< Add to vertex texture v-coordinates
#define GRPEDIT_VTXTEXADD   (GRPEDIT_VTXTEXADDU | GRPEDIT_VTXTEXADDV) ///< Add to vertex texture coordinates
#define GRPEDIT_VTXADD      (GRPEDIT_VTXCRDADD | GRPEDIT_VTXNMLADD | GRPEDIT_VTXTEXADD)
#define GRPEDIT_VTXMOD      (GRPEDIT_VTX | GRPEDIT_VTXADD)
#endif
