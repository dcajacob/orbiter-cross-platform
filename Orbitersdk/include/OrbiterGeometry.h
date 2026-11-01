// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_GEOMETRY_H
#define ORBITER_GEOMETRY_H
#include "OrbiterVector.h"

/**
 * \brief 4-element vector
 */
typedef union {
	double data[4];                ///< array data interface
	struct { double x, y, z, w; }; ///< named data interface
} VECTOR4;

/**
 * \brief 3x3-element matrix
 */
typedef union {
	double data[9];               ///< array data interface (row-sorted)
	struct { double m11, m12, m13, m21, m22, m23, m31, m32, m33; }; ///< named data interface
} MATRIX3;

typedef union {      // 4x4 matrix
	double data[16];
	struct { double m11, m12, m13, m14, m21, m22, m23, m24, m31, m32, m33, m34, m41, m42, m43, m44; };
} MATRIX4;

#endif
