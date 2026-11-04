// Licensed under the MIT License
#pragma once
#include <cstdint>
#include <vector>

namespace orbiter::production {
// Private renderer ownership for original compatibility-OpenGL instruments.
// No platform window/context handle enters a vessel's physical state or SDK.
class NativeGraphicsContext {
public:
    virtual ~NativeGraphicsContext()=default;
};

class NativeInstrumentTarget {
public:
    virtual ~NativeInstrumentTarget()=default;
    virtual void Activate()=0;
    // Original GL readback ordering: RGBA rows start at the lower edge.
    virtual void Readback(std::vector<std::uint8_t>&)=0;
};
}
