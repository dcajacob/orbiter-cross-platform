// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include <cmath>
#include <stdexcept>
namespace orbiter::production {
// Original Orbiter::BeginTimeStep startup policy and elapsed-time cap. The
// production TimeData still computes simulation time from the fixed step/warp.
class CockpitSystemClock {
    unsigned launchTicks=3;
public:
    double Step(double elapsed) {
        if(!std::isfinite(elapsed) || elapsed<=0)throw std::invalid_argument("Application elapsed time must be positive and finite");
        double deltat;
        if(launchTicks){deltat=1.e-2;--launchTicks;}
        else deltat=elapsed;
        if(deltat>0.1)deltat=0.1;
        return deltat;
    }
};
}
