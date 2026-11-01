// Licensed under the MIT License
#include "OrbiterMeshData.h"
#include <cstddef>
#include <type_traits>

// Existing Windows SDK records: four-byte float fields and the frozen field
// order. Compile this same contract without Windows, graphics or Lua headers.
static_assert(sizeof(float) == 4);
static_assert(std::is_standard_layout<COLOUR4>::value && std::is_trivially_copyable<COLOUR4>::value);
static_assert(sizeof(COLOUR4) == 16 && alignof(COLOUR4) == alignof(float));
static_assert(offsetof(COLOUR4,r) == 0 && offsetof(COLOUR4,g) == 4 && offsetof(COLOUR4,b) == 8 && offsetof(COLOUR4,a) == 12);
static_assert(std::is_standard_layout<NTVERTEX>::value && std::is_trivially_copyable<NTVERTEX>::value);
static_assert(sizeof(NTVERTEX) == 32 && alignof(NTVERTEX) == alignof(float));
static_assert(offsetof(NTVERTEX,x) == 0 && offsetof(NTVERTEX,y) == 4 && offsetof(NTVERTEX,z) == 8);
static_assert(offsetof(NTVERTEX,nx) == 12 && offsetof(NTVERTEX,ny) == 16 && offsetof(NTVERTEX,nz) == 20);
static_assert(offsetof(NTVERTEX,tu) == 24 && offsetof(NTVERTEX,tv) == 28);
static_assert(std::is_standard_layout<MATERIAL>::value && std::is_trivially_copyable<MATERIAL>::value);
static_assert(sizeof(MATERIAL) == 68 && alignof(MATERIAL) == alignof(float));
static_assert(offsetof(MATERIAL,diffuse) == 0 && offsetof(MATERIAL,ambient) == 16);
static_assert(offsetof(MATERIAL,specular) == 32 && offsetof(MATERIAL,emissive) == 48 && offsetof(MATERIAL,power) == 64);
int main() { return 0; }
