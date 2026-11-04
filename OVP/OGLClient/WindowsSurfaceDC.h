// Licensed under the MIT License
// Private Windows GDI lease ownership; the public GraphicsClient SDK is unchanged.
#pragma once
#include <memory>
#include <unordered_map>
struct WindowsSurfaceDC;
struct WindowsSurfaceDCDelete {
    void operator()(WindowsSurfaceDC*) const;
};
using WindowsSurfaceDCs = std::unordered_map<SURFHANDLE,
    std::unique_ptr<WindowsSurfaceDC, WindowsSurfaceDCDelete>>;
