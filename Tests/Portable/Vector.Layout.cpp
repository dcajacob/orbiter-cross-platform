// Licensed under the MIT License.
#include "OrbiterVector.h"
#include "OrbiterVector.h" // Header must be safe to include more than once.
#include "OrbiterVectorMath.h"
#include "OrbiterAnimationData.h"
#include "OrbiterVesselData.h"
#include "OrbiterVesselRecords.h"
#include <cstddef>
#include <type_traits>

static_assert(std::is_standard_layout<VECTOR3>::value, "VECTOR3 layout");
static_assert(std::is_trivially_copyable<VECTOR3>::value, "VECTOR3 copying");
static_assert(sizeof(VECTOR3) == 3*sizeof(double), "VECTOR3 size");
static_assert(alignof(VECTOR3) == alignof(double), "VECTOR3 alignment");
static_assert(offsetof(VECTOR3, data) == 0, "array offset");
static_assert(offsetof(VECTOR3, x) == 0, "x offset");
static_assert(offsetof(VECTOR3, y) == sizeof(double), "y offset");
static_assert(offsetof(VECTOR3, z) == 2*sizeof(double), "z offset");
static_assert(sizeof(VECTOR4)==4*sizeof(double) && alignof(VECTOR4)==alignof(double), "VECTOR4 layout");
static_assert(sizeof(MATRIX3)==9*sizeof(double) && alignof(MATRIX3)==alignof(double), "MATRIX3 layout");
static_assert(sizeof(MATRIX4)==16*sizeof(double) && alignof(MATRIX4)==alignof(double), "MATRIX4 layout");
static_assert(offsetof(MATRIX3,m31)==6*sizeof(double) && offsetof(MATRIX4,m41)==12*sizeof(double), "Matrix row layout");
static_assert(std::is_same<oapi::AnimationIndex,unsigned int>::value, "Windows UINT animation identity");
static_assert(sizeof(MESHGROUP_TRANSFORM)==64 && alignof(MESHGROUP_TRANSFORM)==1, "Legacy packed animation layout");
static_assert(sizeof(ANIMATIONCOMP)==48 && offsetof(ANIMATIONCOMP,nchildren)==40, "Animation component layout");
static_assert(sizeof(ANIMATION)==32 && offsetof(ANIMATION,comp)==24, "Animation root layout");
static_assert(THGROUP_ATT_BANKRIGHT==8 && THGROUP_USER_LAST==255 && AIRCTRL_AXIS_XPOS==3 && NAVMODE_HOLDALT==7, "Stock flight identifiers");
static_assert(sizeof(VESSELSTATUS)==504 && sizeof(VESSELSTATUS2)==208, "Original x64 vessel status sizes");
static_assert(offsetof(VESSELSTATUS,flag)==464 && offsetof(VESSELSTATUS2,xpdr)==200, "Original vessel status field offsets");
static_assert(sizeof(EXHAUSTSPEC)==80 && sizeof(PARTICLESTREAMSPEC)==120 && sizeof(BEACONLIGHTSPEC)==72, "Original x64 visual record layouts");
int main() {
    // Use SDK geometry directly without a Windows/graphics umbrella header.
    const auto v=_V(2.,3.,5.);
    const auto r=rotm(unit(_V(1.,2.,3.)),0.7);
    const auto roundTrip=tmul(r,mul(r,v));
    const auto identityProduct=mul(identity4(),_V(2.,3.,5.,1.));
    unsigned int groups[]={2,3};
    MGROUP_ROTATE animation(0,groups,2,_V(1,2,3),_V(0,1,0),0.25f);
    const MGROUP_TRANSFORM& transform=animation;
    return length(roundTrip-v)>1e-12 || identityProduct.x!=2 || identityProduct.y!=3 || identityProduct.z!=5 || identityProduct.w!=1
        || transform.Type()!=MGROUP_TRANSFORM::ROTATE || transform.grp!=groups || transform.ngrp!=2 || animation.angle!=0.25f;
}
