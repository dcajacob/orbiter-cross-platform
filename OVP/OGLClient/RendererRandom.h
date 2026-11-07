// Licensed under the MIT License
// The original client shares the application's CRT random stream. Keep that
// explicit relationship in the native port without intercepting foreign libc.
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
inline int Next() noexcept { return orbiter::production::RandomInteger(); }
inline constexpr int Maximum = orbiter::production::RandomMaximum;
#endif
}
