// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_ANIMATION_DATA_H
#define ORBITER_ANIMATION_DATA_H
#include "OrbiterGeometry.h"
namespace oapi { using AnimationIndex=unsigned int; }
static_assert(sizeof(oapi::AnimationIndex)==4,"Animation index width changed");

#pragma pack(push,1)
/**
 * \brief This structure defines an affine mesh group transform
 *   (translation, rotation or scaling).
 * \sa VESSEL::MeshgroupTransform
 */
typedef struct {
	union {
		struct {
			VECTOR3 ref;   ///< rotation reference point
			VECTOR3 axis;  ///< rotation axis direction
			float angle;   ///< rotation angle [rad]
		} rotparam;
		struct {
			VECTOR3 shift; ///< translation vector
		} transparam;
		struct {
			VECTOR3 scale; ///< scaling factor
		} scaleparam;
	} P;
	int nmesh;             ///< mesh index (>= 0)
	int ngrp;              ///< group index (>= 0, or < 0 to indicate entire mesh)
	enum { TRANSLATE, ROTATE, SCALE } transform; ///< transformation flag
} MESHGROUP_TRANSFORM;
#pragma pack(pop)

// Animation component (obsolete)
typedef struct {
	oapi::AnimationIndex *grp;
	oapi::AnimationIndex ngrp;
	double state0;
	double state1;
	MESHGROUP_TRANSFORM trans;
} ANIMCOMP;

// Transformation types for animations

// Transformation base class
class MGROUP_TRANSFORM {
public:
	MGROUP_TRANSFORM () : mesh(0), grp(0), ngrp(0) {}
	MGROUP_TRANSFORM (oapi::AnimationIndex _mesh, oapi::AnimationIndex *_grp, oapi::AnimationIndex _ngrp)
		: mesh(_mesh), grp(_grp), ngrp(_ngrp) {}
	enum TYPE { NULLTRANSFORM, ROTATE, TRANSLATE, SCALE };
	virtual TYPE Type() const { return NULLTRANSFORM; }

	oapi::AnimationIndex mesh;
	oapi::AnimationIndex *grp;
	oapi::AnimationIndex ngrp;
};

// Rotation
class MGROUP_ROTATE: public MGROUP_TRANSFORM {
public:
	MGROUP_ROTATE (oapi::AnimationIndex _mesh, oapi::AnimationIndex *_grp, oapi::AnimationIndex _ngrp, const VECTOR3 &_ref, const VECTOR3 &_axis, float _angle)
		: MGROUP_TRANSFORM (_mesh, _grp, _ngrp), ref(_ref), axis(_axis), angle(_angle) {}
	TYPE Type() const { return ROTATE; }

	VECTOR3 ref;
	VECTOR3 axis;
	float angle;
};

// Translation
class MGROUP_TRANSLATE: public MGROUP_TRANSFORM {
public:
	MGROUP_TRANSLATE (oapi::AnimationIndex _mesh, oapi::AnimationIndex *_grp, oapi::AnimationIndex _ngrp, const VECTOR3 &_shift)
		: MGROUP_TRANSFORM (_mesh, _grp, _ngrp), shift(_shift) {}
	TYPE Type() const { return TRANSLATE; }

	VECTOR3 shift;
};

// Scaling
class MGROUP_SCALE: public MGROUP_TRANSFORM {
public:
	MGROUP_SCALE (oapi::AnimationIndex _mesh, oapi::AnimationIndex *_grp, oapi::AnimationIndex _ngrp, const VECTOR3 &_ref, const VECTOR3 &_scale)
		: MGROUP_TRANSFORM (_mesh, _grp, _ngrp), ref(_ref), scale(_scale) {}
	TYPE Type() const { return SCALE; }

	VECTOR3 ref;
	VECTOR3 scale;
};

/**
 * \brief Animation component definition
 *
 * Defines one component of an animation, including the mesh transformation,
 * the relative start and end points within the entire animation, and any
 * parent and child relationships with other animations.
 * \sa VESSEL::AddAnimationComponent
 */
struct ANIMATIONCOMP {
	double state0;			  ///< first end state
	double state1;			  ///< second end state
	MGROUP_TRANSFORM *trans;  ///< transformation
	ANIMATIONCOMP *parent;    ///< parent transformation
	ANIMATIONCOMP **children; ///< list of children
	oapi::AnimationIndex nchildren;           ///< number of children
};

/**
 * \brief Animation definition
 *
 * Defines a complete animation, including a list of components, the current
 * animation state, and the default state (as represented by the original mesh).
 */
struct ANIMATION {
	double defstate;          ///< default animation state in the mesh
	double state;             ///< current state
	oapi::AnimationIndex ncomp;               ///< number of components
	ANIMATIONCOMP **comp;     ///< list of components
};


/**
 * \ingroup defines
 * \defgroup animationflags Animation flags
 * \sa VESSEL::AddAnimationComponent
 */
//@{
#define LOCALVERTEXLIST ((oapi::AnimationIndex)(-1)) ///< flags animation component as explicit vertex list
#define MAKEGROUPARRAY(x) ((oapi::AnimationIndex*)x) ///< casts a vertex array into a group
//@}

#endif
