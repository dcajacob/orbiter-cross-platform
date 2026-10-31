// Licensed under the MIT License.
#include "Controller.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace orbiter {
namespace client {
Controller::Controller(std::filesystem::path path, double dt, std::size_t count)
    : scenario(std::move(path)), step(dt), limit(count),
      session(portable::SimulationSession::Load(scenario, step)) {
    const double ns = step * 1e9;
    if (!std::isfinite(ns) || ns < 1 || ns >= double(std::numeric_limits<long long>::max()))
        throw std::runtime_error("fixed step is outside the native clock range");
    period = std::chrono::nanoseconds(std::llround(ns));
    previous = current = session.ReadSnapshot();
}
void Controller::Observe(std::function<void(const PhysicsTraceSample &)> callback) {
    observer = std::move(callback);
    if (observer)
        observer(current.vessel);
}
bool Controller::Finished() const {
    return limit && current.vessel.step >= limit;
}
void Controller::Tick() {
    if (Finished())
        return;
    previous = current;
    session.Step();
    current = session.ReadSnapshot();
    if (observer)
        observer(current.vessel);
}
unsigned Controller::Advance(std::chrono::nanoseconds elapsed, unsigned budget) {
    if (elapsed.count() < 0)
        throw std::runtime_error("clock moved backwards");
    if (paused || Finished())
        return 0;
    if (elapsed > std::chrono::nanoseconds::max() - pending)
        throw std::runtime_error("native clock backlog overflow");
    pending += elapsed;
    unsigned advanced = 0;
    while (pending >= period && advanced < budget && !Finished()) {
        Tick();
        pending -= period;
        ++advanced;
    }
    return advanced;
}
void Controller::Pause(bool value) {
    if (paused != value) {
        paused = value;
        pending = std::chrono::nanoseconds(0);
        previous = current;
    }
}
void Controller::SingleStep() {
    if (!paused)
        return;
    Tick();
    previous = current;
}
void Controller::Reset() {
    auto replacement = portable::SimulationSession::Load(scenario, step);
    session = std::move(replacement);
    previous = current = session.ReadSnapshot();
    pending = std::chrono::nanoseconds(0);
    if (observer)
        observer(current.vessel);
}
Snapshot Controller::Display() const {
    if (paused || Finished())
        return current;
    const double alpha = std::clamp(double(pending.count()) / double(period.count()), 0.0, 1.0);
    Snapshot display = current;
    auto &out = display.vessel;
    for (int i = 0; i < 3; ++i) {
        out.position[i] = previous.vessel.position[i] * (1 - alpha) + current.vessel.position[i] * alpha;
        out.velocity[i] = previous.vessel.velocity[i] * (1 - alpha) + current.vessel.velocity[i] * alpha;
    }
    // Shortest-path normalized quaternion interpolation is for display only.
    const auto &a = previous.vessel.orientation;
    const auto &b = current.vessel.orientation;
    double dot = 0, length = 0;
    for (int i = 0; i < 4; ++i)
        dot += a[i] * b[i];
    for (int i = 0; i < 4; ++i) {
        out.orientation[i] = a[i] * (1 - alpha) + b[i] * alpha * (dot < 0 ? -1 : 1);
        length += out.orientation[i] * out.orientation[i];
    }
    for (double &x : out.orientation)
        x /= std::sqrt(length);
    return display;
}
} // namespace client
} // namespace orbiter
