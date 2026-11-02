// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "Random.h"
#include <cstdlib>
#include <cstdint>
#ifdef ORBITER_REFERENCE_MATH
#include "Math/Runtime.h"
#endif

namespace orbiter::production {
#if !defined(_WIN32) && defined(ORBITER_PRODUCTION_SHARED)
namespace {thread_local std::uint32_t randomState=1;}
int SimulationRandomNext() noexcept {
    randomState=randomState*UINT32_C(214013)+UINT32_C(2531011);
    return static_cast<int>((randomState>>16)&UINT32_C(32767));
}
void SeedSimulationRandom(unsigned seed) noexcept {randomState=seed;}
#endif
const char* SimulationMathProfile() noexcept {
#ifdef ORBITER_REFERENCE_MATH
    return ReferenceMathProfile();
#else
    return "system-crt";
#endif
}
}

double rand1()
{
	static double irmax = 1.0/(double)orbiter::production::RandomMaximum;
	return (double)orbiter::production::RandomInteger()*irmax;
}
