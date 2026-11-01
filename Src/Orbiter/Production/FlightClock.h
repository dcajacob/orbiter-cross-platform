// Licensed under the MIT License
#pragma once
#include <cmath>
#include <stdexcept>
namespace orbiter::production {
// Rendering only feeds elapsed wall time. Every returned tick has the same
// duration. Backlog is retained; a slow renderer never discards simulation time.
class FlightClock {
    long double pending=0,quantum;
public:
    explicit FlightClock(double step):quantum(step) {if(!std::isfinite(step)||step<=0)throw std::invalid_argument("Invalid flight clock quantum");}
    void Add(double elapsed) {if(!std::isfinite(elapsed)||elapsed<0)throw std::invalid_argument("Invalid elapsed time");pending+=elapsed;}
    bool Tick() {if(pending+quantum*1e-12L<quantum)return false;pending-=quantum;return true;}
};
}
