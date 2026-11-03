// Licensed under the MIT License.
#ifndef ORBITER_SHUTTLE_A_PLATFORM_H
#define ORBITER_SHUTTLE_A_PLATFORM_H
#ifdef _WIN32
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Production/FlightKeys.h"
#include "Production/Text.h"
#include "OrbiterScalar.h"
// Same implementation used by the Windows SDK utility.
inline double posangle(double angle)
{
    return orbiter::math::PositiveAngle(angle, PI2);
}
#endif

namespace shuttlea {
inline int CompareText(const char *a, const char *b)
{
#ifdef _WIN32
    return _stricmp(a, b);
#else
    return orbiter::production::CompareText(a, b);
#endif
}
inline int ComparePrefix(const char *a, const char *b, std::size_t count)
{
#ifdef _WIN32
    return _strnicmp(a, b, count);
#else
    return orbiter::production::ComparePrefix(a, b, count);
#endif
}
}
#endif
