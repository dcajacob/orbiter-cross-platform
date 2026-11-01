// Licensed under the MIT License
// Compile the actual SDK vessel declarations without a native Windows header.
#include "NativeVesselAPI.h"
#include "NativeVesselAPI.h"
#include <type_traits>

static_assert(std::is_base_of<VESSEL,VESSEL2>::value, "Stock vessel interface inheritance");
static_assert(std::is_base_of<VESSEL2,VESSEL3>::value, "Stock vessel interface inheritance");
static_assert(std::is_base_of<VESSEL3,VESSEL4>::value, "Stock vessel interface inheritance");
static_assert(sizeof(oapi::Rectangle)==16, "Stock rectangle dimensions");
#ifdef _WIN32
static_assert(std::is_same<oapi::UInt32,DWORD>::value, "Preserve Windows SDK DWORD identity");
static_assert(std::is_same<oapi::UInt16,WORD>::value, "Preserve Windows SDK WORD identity");
static_assert(std::is_same<oapi::UInt,UINT>::value, "Preserve Windows SDK UINT identity");
static_assert(std::is_same<oapi::Rectangle,RECT>::value, "Preserve Windows SDK RECT identity");
static_assert(std::is_same<oapi::DrawContext,HDC>::value, "Preserve Windows SDK HDC identity");
#else
#ifdef _WINDOWS_
#error Native vessel declarations unexpectedly pulled in Windows headers
#endif
#endif
int main() {return 0;}
