// Licensed under the MIT License.
#include "View.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace orbiter {
namespace client {
namespace {
Vector GraphicsAxes(const Vector &v) {
    return Vector(v.x, v.y, -v.z);
}
} // namespace
Vector Position(const Snapshot &s) {
    const auto &p = s.vessel.position;
    return Vector(p[0], p[1], p[2]);
}
Vector Rotate(const Snapshot &s, const Vector &v) {
    const auto &q = s.vessel.orientation;
    Quaternion rotation;
    rotation.qvx = q[0];
    rotation.qvy = q[1];
    rotation.qvz = q[2];
    rotation.qs = q[3];
    Matrix m;
    m.Set(rotation);
    return mul(m, v);
}
void Camera::Orbit(double dx, double dy) {
    yaw = std::remainder(yaw + dx, Pi2);
    pitch = std::clamp(pitch + dy, -1.45, 1.45);
}
void Camera::Zoom(double amount) {
    zoom = std::clamp(zoom * std::exp(-amount * .12), .3, 5.0);
}
Vector View::EyePoint(const Vector &point) const {
    // Convert Orbiter's left-handed axes at this boundary, after subtracting
    // the camera origin in double precision. No simulation coordinates change.
    const auto delta = GraphicsAxes(point - eye);
    return Vector(dotp(delta, right), dotp(delta, up), -dotp(delta, forward));
}
std::array<float, 16> View::Projection() const {
    const double f = 1 / std::tan(25 * _RAD_);
    const double n = nearPlane, z = farPlane;
    return {float(f / aspect),          0, 0, 0, 0, float(f), 0, 0, 0, 0, float((z + n) / (n - z)), -1, 0, 0,
            float(2 * z * n / (n - z)), 0};
}
View MakeView(const Camera &c, const Snapshot &s, int width, int height) {
    if (width <= 0 || height <= 0)
        throw std::runtime_error("invalid framebuffer dimensions");
    const Vector target = c.overview ? Vector(0, 0, 0) : Position(s);
    const double distance = (c.overview ? s.primaryRadius * 3.4 : 18) * c.zoom;
    View v;
    v.eye = target + Vector(std::sin(c.yaw) * std::cos(c.pitch), std::sin(c.pitch),
                            -std::cos(c.yaw) * std::cos(c.pitch)) *
                         distance;
    v.forward = GraphicsAxes(target - v.eye).unit();
    v.right = crossp(v.forward, Vector(0, 1, 0)).unit();
    v.up = crossp(v.right, v.forward);
    v.nearPlane = c.overview ? s.primaryRadius * .01 : .05;
    v.farPlane = s.primaryRadius * 30;
    v.aspect = double(width) / height;
    return v;
}
} // namespace client
} // namespace orbiter
