// Licensed under the MIT License.
#include "OrbiterVector.h"
#include "OrbiterVector.h" // Header must be safe to include more than once.
#include "OrbiterVectorMath.h"
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
int main() {
    // Use SDK geometry directly without a Windows/graphics umbrella header.
    const auto v=_V(2.,3.,5.);
    const auto r=rotm(unit(_V(1.,2.,3.)),0.7);
    const auto roundTrip=tmul(r,mul(r,v));
    const auto identityProduct=mul(identity4(),_V(2.,3.,5.,1.));
    return length(roundTrip-v)>1e-12 || identityProduct.x!=2 || identityProduct.y!=3 || identityProduct.z!=5 || identityProduct.w!=1;
}
