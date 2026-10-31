// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_SCALAR_H
#define ORBITER_SCALAR_H
#include <math.h>

namespace orbiter { namespace math {
// Shared implementation of the SDK's existing positive-angle normalization.
inline double PositiveAngle(double angle, double full_turn)
{
    double a = fmod(angle, full_turn);
    return (a >= 0.0 ? a : a+full_turn);
}
}}
#endif
