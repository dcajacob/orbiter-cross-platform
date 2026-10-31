// Copyright (c) Orbiter contributors
// Licensed under the MIT License
#ifndef ORBITER_PHYSICS_TRACE_H
#define ORBITER_PHYSICS_TRACE_H

#include <array>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <string>

namespace orbiter {

// Observation only: vectors use the global ecliptic axes, relative to the
// selected primary. Quaternion order is vector x,y,z then scalar, mapping
// vessel-local vectors to global axes. Angular velocity uses vessel-local axes.
struct PhysicsTraceSample {
    std::size_t step;
    double seconds, mjd;
    std::array<double, 3> position, velocity;
    std::array<double, 4> orientation;
    std::array<double, 3> angularVelocity;
};

class PhysicsTrace {
public:
    void Open(const std::string &path) {
        if (stream.is_open()) throw std::runtime_error("physics trace already open");
        stream.clear();
        stream.imbue(std::locale::classic());
        stream.open(path, std::ios::out | std::ios::trunc | std::ios::binary);
        if (!stream) throw std::runtime_error("cannot open physics trace: " + path);
        stream << "step,sim_seconds,mjd,rx,ry,rz,vx,vy,vz,qx,qy,qz,qw,wx,wy,wz\n";
        stream << std::setprecision(17);
        Check();
    }

    bool IsOpen() const { return stream.is_open(); }

    void Write(const PhysicsTraceSample &sample) {
        if (!IsOpen()) throw std::runtime_error("physics trace is not open");
        CheckFinite(sample.seconds);
        CheckFinite(sample.mjd);
        for (double v : sample.position) CheckFinite(v);
        for (double v : sample.velocity) CheckFinite(v);
        for (double v : sample.orientation) CheckFinite(v);
        for (double v : sample.angularVelocity) CheckFinite(v);
        stream << sample.step << ',' << sample.seconds << ',' << sample.mjd;
        for (double v : sample.position) stream << ',' << v;
        for (double v : sample.velocity) stream << ',' << v;
        for (double v : sample.orientation) stream << ',' << v;
        for (double v : sample.angularVelocity) stream << ',' << v;
        stream << '\n';
        // Orbiter's existing fast-exit path calls exit(), bypassing destructors.
        stream.flush();
        Check();
    }

    void Close() {
        if (!IsOpen()) return;
        stream.close();
        Check();
    }

private:
    static void CheckFinite(double value) {
        if (!std::isfinite(value)) throw std::runtime_error("nonfinite physics trace state");
    }
    void Check() const {
        if (!stream) throw std::runtime_error("cannot write physics trace");
    }
    std::ofstream stream;
};

} // namespace orbiter
#endif
