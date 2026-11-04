// Licensed under the MIT License
#pragma once
#ifdef _WIN32
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Production/FlightKeys.h"
#include "Production/Text.h"
#include "MFDAPI.h"
#include <memory>
#include <vector>
class AscentAP;
class PayloadBayOp;
#define DLLCLBK static
#endif

namespace atlantis {
inline int CompareText(const char* left,const char* right) {
#ifdef _WIN32
    return _stricmp(left,right);
#else
    return orbiter::production::CompareText(left,right);
#endif
}
inline int ComparePrefix(const char* left,const char* right,std::size_t count) {
#ifdef _WIN32
    return _strnicmp(left,right,count);
#else
    return orbiter::production::ComparePrefix(left,right,count);
#endif
}
inline oapi::UInt16 LowWord(oapi::CockpitUnsignedParam value) {
#ifdef _WIN32
    return LOWORD(value);
#else
    return static_cast<oapi::UInt16>(value&0xffff);
#endif
}
inline oapi::UInt16 HighWord(oapi::CockpitUnsignedParam value) {
#ifdef _WIN32
    return HIWORD(value);
#else
    return static_cast<oapi::UInt16>((value>>16)&0xffff);
#endif
}
}
