// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_CONFIGURATION_TYPES_H
#define ORBITER_PRODUCTION_CONFIGURATION_TYPES_H
#include "CoreTypes.h"
#ifdef _WIN32
#include <windows.h>
#endif
namespace orbiter::production {
#ifdef _WIN32
using ConfigurationRectangle = RECT;
using ConfigurationWriteResult = BOOL;
#else
// Persisted window coordinates, without exposing native window objects to Config.
struct ConfigurationRectangle { std::int32_t left, top, right, bottom; };
using ConfigurationWriteResult = int;
#endif
// Capacity of the existing serialized font-path fields, on both platforms.
constexpr unsigned ConfigurationFontPathCapacity = 260;
}
#endif
