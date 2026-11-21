// Licensed under the MIT License
#include "Probe.h"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void near(double actual, double expected, const char *label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-8 * std::max(1.0, std::abs(expected))) {
        throw std::runtime_error(std::string(label) + ": " + std::to_string(actual) + " != " + std::to_string(expected));
    }
}

double constantLift(double) { return 0.2; }

void checkDragAndLift() {
    LegacyForceProbe vessel;
    vessel.evaluate(Vector(0, 0, 100));
    near(vessel.Flin_add.z, -2000, "Forward drag");
    vessel.vd_back = 30;
    vessel.evaluate(Vector(0, 0, 100));
    near(vessel.Drag, 2000, "Backward coefficient changed forward flight");

    vessel.vd_back = 3;
    vessel.evaluate(Vector(0, 0, -100));
    near(vessel.Flin_add.z, 15000, "Backward drag did not use backward coefficient");

    for (double backward : {3.0, 30.0}) {
        vessel.vd_back = backward;
        vessel.evaluate(Vector(100, 0, 0));
        near(vessel.Flin_add.x, -7500, "Lateral drag");
        vessel.evaluate(Vector(0, -100, 0));
        near(vessel.Flin_add.y, 10000, "Vertical drag");
    }

    vessel.LiftCoeff = constantLift;
    for (double backward : {3.0, 6.0}) {
        vessel.vd_back = backward;
        vessel.evaluate(Vector(0, 0, -100));
        near(vessel.Lift, 4000, "Lift magnitude with backward flow");
        near(vessel.Flin_add.y, -4000, "Transverse lift force with backward flow");
    }
}

void checkDragDissipation() {
    LegacyForceProbe vessel;
    for (int x = -2; x <= 2; ++x) {
        for (int y = -2; y <= 2; ++y) {
            for (int z = -2; z <= 2; ++z) {
                const Vector flow(10 * x, 10 * y, 10 * z);
                vessel.evaluate(flow);
                const double power = dotp(vessel.Flin_add, flow);
                if (!std::isfinite(power) || power > 0) {
                    throw std::runtime_error("Legacy drag supplied kinetic energy");
                }
            }
        }
    }
    vessel.evaluate(Vector(0, 0, 0));
    near(vessel.Flin_add.length(), 0, "Zero-flow force");
    vessel.bCWexplicit = false;
    vessel.evaluate(Vector(0, 0, -100));
    near(vessel.Flin_add.length(), 0, "Implicit CW acquired legacy drag");
}
} // namespace

int main() {
    try {
        checkDragAndLift();
        checkDragDissipation();
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
