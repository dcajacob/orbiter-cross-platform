// Licensed under the MIT License.
#pragma once
#include "Controller.h"
#include <array>
namespace orbiter {
namespace client {
struct Camera {
    bool overview = true;
    double yaw = .65, pitch = .4, zoom = 1;
    void Orbit(double dx, double dy);
    void Zoom(double amount);
};
struct View {
    Vector eye, right, up, forward;
    double nearPlane, farPlane, aspect;
    Vector EyePoint(const Vector &orbiterPoint) const;
    std::array<float, 16> Projection() const;
};
Vector Position(const Snapshot &snapshot);
Vector Rotate(const Snapshot &snapshot, const Vector &local);
View MakeView(const Camera &camera, const Snapshot &snapshot, int width, int height);
} // namespace client
} // namespace orbiter
