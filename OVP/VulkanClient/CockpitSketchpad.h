// Licensed under the MIT License
#pragma once
#include "OrbiterScene.h"

namespace orbiter::vulkan {

// The stock HUD and MFDs draw through Orbiter's Sketchpad ABI on both hosts.
struct CockpitFont final : oapi::Font {
    int height;
    std::unique_ptr<SDL_Surface,decltype(&SDL_DestroySurface)> atlas{nullptr,SDL_DestroySurface};
    CockpitFont(int h, bool prop, const char* face, FontStyle style, int angle)
        : Font(h, prop, face, style, angle), height(std::max(1, std::abs(h))) {}
};
struct CockpitPen final : oapi::Pen {
    int style, width;
    oapi::UInt32 color;
    CockpitPen(int s, int w, oapi::UInt32 c) : Pen(s,w,c), style(s), width(std::max(1,w)), color(c) {}
};
struct CockpitBrush final : oapi::Brush {
    oapi::UInt32 color;
    explicit CockpitBrush(oapi::UInt32 c) : Brush(c), color(c) {}
};

oapi::Sketchpad* OpenCockpitSketchpad(OrbiterScene&, SURFHANDLE);
} // namespace orbiter::vulkan
