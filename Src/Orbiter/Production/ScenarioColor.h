// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SCENARIO_COLOR_H
#define ORBITER_PRODUCTION_SCENARIO_COLOR_H
#include "CoreTypes.h"
// Original scenario CSS colour parser; 0xbbggrr integer, never a device object.
orbiter::production::UInt32 GetCSSColor(const char* color);
#endif
