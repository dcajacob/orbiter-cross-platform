// Licensed under the MIT License.
#pragma once
#include "SimulationSession.h"
#include <chrono>
#include <functional>

namespace orbiter {
namespace client {
using Snapshot = portable::SimulationSnapshot;
// Window-independent application state. All simulation changes pass through
// this controller; renderers receive snapshots by value.
class Controller {
  public:
    Controller(std::filesystem::path scenario, double step, std::size_t limit = 0);
    void Observe(std::function<void(const PhysicsTraceSample &)> observer);
    unsigned Advance(std::chrono::nanoseconds elapsed, unsigned budget = 8);
    void Pause(bool paused);
    bool Paused() const {
        return paused;
    }
    bool Finished() const;
    void SingleStep();
    void Reset();
    Snapshot Current() const {
        return current;
    }
    Snapshot Display() const;
    bool IsInputFile(const std::filesystem::path &path) const {
        return session.IsInputFile(path);
    }

  private:
    std::filesystem::path scenario;
    double step;
    std::size_t limit;
    portable::SimulationSession session;
    Snapshot previous, current;
    std::chrono::nanoseconds period, pending{0};
    bool paused = false;
    std::function<void(const PhysicsTraceSample &)> observer;
    void Tick();
};
} // namespace client
} // namespace orbiter
