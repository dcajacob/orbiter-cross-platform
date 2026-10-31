// Licensed under the MIT License.
#include "Controller.h"
#include "View.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace orbiter;
using namespace orbiter::client;
namespace {
void require(bool value, const char *message) {
    if (!value)
        throw std::runtime_error(message);
}
bool equal(const PhysicsTraceSample &a, const PhysicsTraceSample &b) {
    return a.step == b.step && a.seconds == b.seconds && a.mjd == b.mjd && a.position == b.position &&
           a.velocity == b.velocity && a.orientation == b.orientation &&
           a.angularVelocity == b.angularVelocity;
}
} // namespace
int main(int argc, char **argv) {
    try {
        require(argc == 2, "scenario argument required");
        const std::filesystem::path path = argv[1];
        auto core = portable::SimulationSession::Load(path, 1);
        std::vector<PhysicsTraceSample> expected{core.ReadState()};
        for (int i = 0; i < 6000; ++i) {
            core.Step();
            expected.push_back(core.ReadState());
        }
        for (int hz : {30, 60, 144, 0}) {
            Controller c(path, 1, 6000);
            std::size_t observed = 0;
            c.Observe([&](const auto &state) {
                require(equal(state, expected.at(observed++)), "render scheduling changed numerical state");
            });
            long long remaining = 6000LL * 1000000000;
            int frame = 0;
            while (remaining > 0) {
                long long ns = hz ? 1000000000 / hz : ((++frame % 7) ? 17700000 : 1900000000);
                ns = std::min(ns, remaining);
                remaining -= ns;
                c.Advance(std::chrono::nanoseconds(ns));
                const auto before = c.Current();
                auto shown = c.Display();
                shown.vessel.position[0] = 0;
                require(equal(before.vessel, c.Current().vessel), "display mutated physics");
            }
            while (!c.Finished())
                require(c.Advance(std::chrono::nanoseconds(0)) > 0, "lost catch-up steps");
            require(observed == 6001, "incomplete state observation");
        }
        Controller c(path, 1);
        require(c.Advance(std::chrono::seconds(20)) == 8, "unbounded work per frame");
        require(c.Advance(std::chrono::seconds(0)) == 8, "backlog was discarded");
        c.Pause(true);
        auto state = c.Current();
        c.Advance(std::chrono::hours(1));
        require(equal(state.vessel, c.Current().vessel), "pause advanced time");
        c.SingleStep();
        require(c.Current().vessel.step == 17, "single-step did not advance exactly once");
        c.Reset();
        require(c.Current().vessel.step == 0 && c.Paused(), "reset state or pause changed");
        c.Pause(false);
        c.Advance(std::chrono::milliseconds(500));
        require(c.Current().vessel.step == 0, "pause accumulated wall time");
        c.Advance(std::chrono::milliseconds(500));
        require(c.Current().vessel.step == 1, "resume lost time");
        bool backwards = false;
        try {
            c.Advance(std::chrono::nanoseconds(-1));
        } catch (const std::runtime_error &) {
            backwards = true;
        }
        require(backwards, "negative time accepted");

        auto snapshot = c.Current();
        snapshot.vessel.orientation = {0, 0, 0, 1};
        Camera camera;
        camera.overview = false;
        camera.yaw = camera.pitch = 0;
        auto view = MakeView(camera, snapshot, 800, 600);
        auto position = Position(snapshot);
        auto origin = view.EyePoint(position), x = view.EyePoint(position + Vector(.001, 0, 0));
        auto y = view.EyePoint(position + Vector(0, 1, 0)), z = view.EyePoint(position + Vector(0, 0, 1));
        require(std::abs(origin.x) < 1e-8 && std::abs(origin.y) < 1e-8 && origin.z < 0,
                "camera target projection");
        require(std::abs((x.x - origin.x) - .001) < 1e-8,
                "planetary translation lost local precision or x handedness");
        require(y.y > origin.y && z.z < origin.z, "view coordinate conventions");
        require((Rotate(snapshot, Vector(1, 2, 3)) - Vector(1, 2, 3)).length() < 1e-12, "identity attitude");
        snapshot.vessel.orientation = {0, 0, std::sqrt(.5), std::sqrt(.5)};
        require((Rotate(snapshot, Vector(1, 0, 0)) - Vector(0, -1, 0)).length() < 1e-12, "quaternion axes");
        camera.Orbit(100, 100);
        camera.Zoom(10000);
        require(std::isfinite(camera.yaw) && camera.pitch <= 1.45 && camera.zoom >= .3, "camera limits");
        std::cout << "PASS: 6000 steps at 30/60/144 Hz and irregular timing; pause/reset/backlog, immutable "
                     "display and camera axes\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
