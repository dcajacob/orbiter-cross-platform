// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef ORBITER_VECTOR_H
#define ORBITER_VECTOR_H

// Shared vector storage, independent of platform and SDK services.
/**
 * \ingroup vec
 * \brief 3-element vector
 */
typedef union {
	double data[3];               ///< array data interface
	struct { double x, y, z; };   ///< named data interface
} VECTOR3;

#endif // ORBITER_VECTOR_H
