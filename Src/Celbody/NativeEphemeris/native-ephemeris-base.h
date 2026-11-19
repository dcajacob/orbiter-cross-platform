// Licensed under the MIT License
#pragma once
#include "Production/NativeAbi.h"
#include "Production/NativeCelestialApi.h"
#include "ConfigFile.h"
#include <cmath>
#include <cctype>
#include <cstring>
#include <stdexcept>
#include <limits>

struct Sample {
    double t;
    double rad;
    double param[6];
};


class NativeEphemerisBase : public orbiter::native::CelestialModule {
public:
    using CelestialModule::CelestialModule;

    bool clbkAtmParam(double altitude, orbiter::native::AtmosphereOutput* result) override
    {
        if (!GetAtmosphere())
            return false;
        orbiter::native::AtmosphereInput input{};
        input.alt = altitude;
        input.flag = orbiter::native::Atmosphere::PRM_ALT;
        return GetAtmosphere()->clbkParams(&input, result);
    }
};
