// Licensed under the MIT License.
#include "OrbiterVector.h"
#include "OrbiterVector.h" // Header must be safe to include more than once.
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
int main() { return 0; }
