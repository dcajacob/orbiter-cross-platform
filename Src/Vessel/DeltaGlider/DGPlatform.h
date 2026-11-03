// Licensed under the MIT License
#pragma once
#ifdef _WIN32
#include <cstdlib>
#include <cstring>
namespace dg {
inline int CompareText(const char *a, const char *b) { return _stricmp(a, b); }
inline int ComparePrefix(const char *a, const char *b, std::size_t n) { return _strnicmp(a, b, n); }
inline double RandomLampPhase() { return (double)std::rand()/(double)RAND_MAX; }
}
#else
#include "Production/FlightKeys.h"
#include "Production/Random.h"
#include "Production/Text.h"
namespace dg {
using orbiter::production::CompareText;
using orbiter::production::ComparePrefix;
inline double RandomLampPhase()
{
    return (double)orbiter::production::RandomInteger()/(double)orbiter::production::RandomMaximum;
}
}
#endif
