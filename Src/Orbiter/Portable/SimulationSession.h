// Licensed under the MIT License.
#ifndef ORBITER_PORTABLE_SIMULATION_SESSION_H
#define ORBITER_PORTABLE_SIMULATION_SESSION_H
#include "PhysicsTrace.h"
#include "TimeData.h"
#include "Vecmat.h"
#include <filesystem>
#include <vector>

namespace orbiter { namespace portable {

// Internal fixed-primary, single unpowered-vessel session. Owns its time and
// state; file streams close during Load and no platform services are required.
class SimulationSession {
public:
    static SimulationSession Load(const std::filesystem::path &scenario, double fixedStep);
    void Step();
    PhysicsTraceSample ReadState() const;
    bool IsInputFile(const std::filesystem::path &path) const;

private:
    TimeData time;
    StateVectors state;
    Vector primaryPosition, inertia;
    Vector positionBase, velocityBase, positionDelta, velocityDelta;
    Vector acceleration, angularAcceleration;
    double primaryMass = 0, primaryRadius = 0, step = 0;
    int flushCounter = 0;
    std::vector<std::filesystem::path> inputs;
    void ValidateState() const;
};

}}
#endif
