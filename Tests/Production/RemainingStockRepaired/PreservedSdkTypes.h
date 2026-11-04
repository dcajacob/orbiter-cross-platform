// Licensed under the MIT License
// Private source spellings for compiling the current client against the exact
// retained Windows SDK. No SDK file, public type or class layout is changed.
#pragma once
#include <windows.h>
#include <cstdint>
#include <type_traits>
namespace oapi {
using UInt32=DWORD;
using UInt=UINT;
static_assert(sizeof(UInt32)==4 && sizeof(UInt)==4);
static_assert(std::is_same<UInt32,DWORD>::value && std::is_same<UInt,UINT>::value);
}
