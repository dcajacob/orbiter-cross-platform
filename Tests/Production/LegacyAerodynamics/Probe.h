// Licensed under the MIT License
#pragma once

#include "OrbiterVesselData.h"
#include "Vecmat.h"
#include <cmath>

// Fields read or written by the production legacy force method.
struct LegacyForceProbe {
    bool bCWexplicit = true;
    struct {
        double airspd = 0;
        double atmrho = 1;
        double dynp = 0;
        Vector airvel_ship{0, 0, 0};
    } sp;
    double size = 1, mass = 1000, trim_scale = 0;
    double pitch_moment_scale = 0, bank_moment_scale = 0;
    struct { double curr = 0; } ctrlsurf_level[AIRCTRL_ELEVATORTRIM + 1];
    Vector cs{4, 4, 8}, rdrag{0, 0, 0};
    struct AngularState { Vector omega{0, 0, 0}; } state;
    AngularState *s0 = &state;
    double vd_side = 1.5, vd_vert = 2, vd_forw = 0.4, vd_back = 3;
    double wingfactor = 1, Lift = 0, Drag = 0;
    double (*LiftCoeff)(double) = nullptr;
    Vector Flin_add{0, 0, 0}, Amom_add{0, 0, 0};

    void UpdateAerodynamicForces_OLD();

    void evaluate(const Vector &flow) {
        sp.airvel_ship = flow;
        sp.airspd = flow.length();
        sp.dynp = 0.5 * sp.atmrho * sp.airspd * sp.airspd;
        Flin_add.Set(0, 0, 0);
        Amom_add.Set(0, 0, 0);
        UpdateAerodynamicForces_OLD();
    }
};
