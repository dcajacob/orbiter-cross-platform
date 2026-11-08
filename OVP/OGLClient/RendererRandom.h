// Licensed under the MIT License
// The host declares whether visual draws share the simulation's CRT stream.
// Keep that relationship explicit without intercepting foreign libc.
#pragma once
#include <cstdlib>
#ifndef _WIN32
#include "Production/Random.h"
#endif
namespace renderer_random {
#ifdef _WIN32
inline int Next() noexcept { return std::rand(); }
inline constexpr int Maximum = RAND_MAX;
#else
inline int Next() noexcept { return orbiter::production::RendererRandomNext(); }
inline constexpr int Maximum = orbiter::production::RandomMaximum;
#endif
}
