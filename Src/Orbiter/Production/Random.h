// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_RANDOM_H
#define ORBITER_PRODUCTION_RANDOM_H
#include "Export.h"
#include <cstdlib>
namespace orbiter::production {
#if defined(_WIN32) || !defined(ORBITER_PRODUCTION_SHARED)
static constexpr int RandomMaximum=RAND_MAX;
static inline int RandomInteger() noexcept {return std::rand();}
static inline void SeedRandom(unsigned seed) noexcept {std::srand(seed);}
#else
// Match the original runtime's algorithm/range. State belongs to the numerical
// engine, so foreign libraries cannot consume its random sequence.
static constexpr int RandomMaximum=32767;
ORBITER_PRODUCTION_API int SimulationRandomNext() noexcept;
ORBITER_PRODUCTION_API void SeedSimulationRandom(unsigned seed) noexcept;
// The complete cockpit reproduces the original client's shared CRT stream.
// The external-view host keeps visual draws out of its simulation stream.
ORBITER_PRODUCTION_API void ConfigureRendererRandom(bool shared,unsigned seed) noexcept;
ORBITER_PRODUCTION_API int RendererRandomNext() noexcept;
ORBITER_PRODUCTION_API const char* RendererRandomProfile() noexcept;
static inline int RandomInteger() noexcept {return SimulationRandomNext();}
static inline void SeedRandom(unsigned seed) noexcept {SeedSimulationRandom(seed);}
#endif
ORBITER_PRODUCTION_API const char* SimulationMathProfile() noexcept;
}
ORBITER_PRODUCTION_API double rand1();
#endif
