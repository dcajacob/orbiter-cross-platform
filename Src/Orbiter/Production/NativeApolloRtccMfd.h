// Licensed under the MIT License
#pragma once
#include "NativeVesselAPI.h"
#include <cstddef>

namespace orbiter::production {
struct NativeApolloRtccMfdApi {
    std::size_t size;
    void (*preStep)(double, double, double);
    void (*deleteVessel)(OBJHANDLE);
    void (*end)();
};
}
