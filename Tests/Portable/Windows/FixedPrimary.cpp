// Licensed under the MIT License.
// Test fixture adapter only: supply a stationary primary to the original app.
// No force model or vessel propagation is implemented here.
#define ORBITER_MODULE
#include "Orbitersdk.h"

class FixedPrimary : public CELBODY {
public:
    // Both callbacks report the same stationary state at every epoch.
    bool bEphemeris() const override { return true; }

    int clbkEphemeris(double, int, double *state) override { return Position(state); }
    int clbkFastEphemeris(double, int, double *state) override { return Position(state); }

private:
    static int Position(double *state) {
        for (int i = 0; i < 12; ++i) state[i] = 0.0;
        // CelestialBody::InterpolatePosition normalizes its global root position.
        // Keep it away from zero without modifying that pre-refactor algorithm.
        // The scenario and traces use primary-relative position/velocity.
        state[0] = state[6] = 100000000.0;
        return EPHEM_TRUEPOS | EPHEM_TRUEVEL | EPHEM_BARYPOS | EPHEM_BARYVEL | EPHEM_BARYISTRUE;
    }
};

DLLCLBK CELBODY *InitInstance(OBJHANDLE) { return new FixedPrimary; }
DLLCLBK void ExitInstance(CELBODY *body) { delete static_cast<FixedPrimary *>(body); }
