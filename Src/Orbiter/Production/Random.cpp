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
namespace {
thread_local std::uint32_t randomState=1,rendererState=1;
thread_local bool rendererSharesSimulation=true;
int Next(std::uint32_t& state) noexcept {
    state=state*UINT32_C(214013)+UINT32_C(2531011);
    return static_cast<int>((state>>16)&UINT32_C(32767));
}
}
int SimulationRandomNext() noexcept {return Next(randomState);}
void SeedSimulationRandom(unsigned seed) noexcept {randomState=seed;}
void ConfigureRendererRandom(bool shared,unsigned seed) noexcept {
    rendererSharesSimulation=shared;rendererState=seed;
}
int RendererRandomNext() noexcept {
    return rendererSharesSimulation?SimulationRandomNext():Next(rendererState);
}
const char* RendererRandomProfile() noexcept {
    return rendererSharesSimulation?"shared-simulation":"isolated-msvc-lcg32";
}
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
