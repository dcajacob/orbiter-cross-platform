// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_SDK_MESH_DATA_H
#define ORBITER_SDK_MESH_DATA_H

// Shared SDK value records. Declarations, field order and scalar types are
// identical to the original Windows SDK; this header needs no platform APIs.

/** 
 * \ingroup structures
 * \brief colour definition
 */
typedef struct {
	float r;    ///< read colour component [0..1]
	float g;    ///< green colour component [0..1]
	float b;    ///< blue colour component [0..1]
	float a;    ///< alpha (opacity) component (0..1)
} COLOUR4;

/**
 * \ingroup structures
 * \brief vertex definition including normals and texture coordinates 
 */
typedef struct {
	float x;     ///< vertex x position
	float y;     ///< vertex y position
	float z;     ///< vertex z position
	float nx;    ///< vertex x normal
	float ny;    ///< vertex y normal
	float nz;    ///< vertex z normal
	float tu;    ///< vertex u texture coordinate
	float tv;    ///< vertex v texture coordinate
} NTVERTEX;

/**
 * \ingroup structures
 * \brief material definition 
 */
typedef struct {
	COLOUR4 diffuse;   ///< diffuse component
	COLOUR4 ambient;   ///< ambient component
	COLOUR4 specular;  ///< specular component
	COLOUR4 emissive;  ///< emissive component
	float power;       ///< specular power
} MATERIAL;

#endif
