// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_CORE_TYPES_H
#define ORBITER_PRODUCTION_CORE_TYPES_H
#include <cstdint>
namespace orbiter::production {
#ifdef _WIN32
using UInt32 = unsigned long; // preserve the existing Windows SDK scalar type
#else
using UInt32 = std::uint32_t;
#endif
using UInt16 = std::uint16_t;
using UInt64 = std::uint64_t;
static_assert(sizeof(UInt32)==4 && sizeof(UInt16)==2 && sizeof(UInt64)==8);
}
#endif
