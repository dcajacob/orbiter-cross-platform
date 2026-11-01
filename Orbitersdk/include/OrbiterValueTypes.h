// Licensed under the MIT License
#ifndef ORBITER_VALUE_TYPES_H
#define ORBITER_VALUE_TYPES_H
#include <cstdint>
namespace oapi {
#ifdef _WIN32
using UInt32=unsigned long; // Preserve the original Windows SDK scalar identity.
#else
using UInt32=std::uint32_t;
#endif
using UInt=unsigned int;
using UInt16=std::uint16_t;
static_assert(sizeof(UInt32)==4 && sizeof(UInt)==4 && sizeof(UInt16)==2,"SDK scalar width changed");
}
#endif
