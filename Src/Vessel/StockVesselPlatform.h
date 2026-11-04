// Licensed under the MIT License
#pragma once
#include <cstddef>
#ifdef _WIN32
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Production/NativeInterpreterSdk.h"
#include "Production/FlightKeys.h"
#include "Production/Text.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#define DLLCLBK static
#endif

namespace stock_vessel {
inline int ComparePrefix(const char* left,const char* right,std::size_t length) {
#ifdef _WIN32
    return _strnicmp(left,right,length);
#else
    return orbiter::production::ComparePrefix(left,right,length);
#endif
}
}
