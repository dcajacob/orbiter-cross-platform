// Licensed under the MIT License
#pragma once
#include "NativeVesselAPI.h"
#include <cstddef>

namespace orbiter::production {
// Borrowed from the checked LuaMFD module until every user MFD is destroyed.
struct NativeLuaMfdApi {
    std::size_t size;
    void (*postStep)(double, double, double);
    void (*deleteVessel)(OBJHANDLE);
    void (*end)();
};
}
