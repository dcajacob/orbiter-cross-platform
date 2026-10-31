// Licensed under the MIT License.
#pragma once
#include "SimulationSession.h"
#include <chrono>
#include <functional>

namespace orbiter {
namespace client {
using Snapshot = portable::SimulationSnapshot;
// Re-anchor wall time after pause/resume/reset. A slow event callback or OS
// suspension must not become simulation catch-up in the new session.
class FrameClock {
  public:
    void Restart() {
        fresh = true;
    }
    std::chrono::nanoseconds Elapsed(std::chrono::steady_clock::time_point now) {
        const auto elapsed = fresh ? std::chrono::nanoseconds(0)
                                   : std::chrono::duration_cast<std::chrono::nanoseconds>(now - previous);
        previous = now;
        fresh = false;
        return elapsed;
    }

  private:
    bool fresh = true;
    std::chrono::steady_clock::time_point previous{};
};

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
