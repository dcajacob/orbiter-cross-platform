// Licensed under the MIT License
#pragma once
#include "OrbiterHandles.h"
#include <cstddef>

namespace orbiter::production {
class ResourceResolver;
struct NativeSoundContext {
    const ResourceResolver& assets;
};
struct NativeSoundApi {
    std::size_t size;
    void (*step)(double, double, double);
    void (*pause)(bool);
    void (*deleteVessel)(OBJHANDLE);
};
}
