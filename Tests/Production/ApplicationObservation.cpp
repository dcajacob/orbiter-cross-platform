// Copyright (c) Orbiter contributors. Licensed under the MIT License.
#include "ApplicationObservation.h"
#include <cmath>
#include <limits>

namespace {
OrbiterTestObserver observer = nullptr;
double defaultMjd = std::numeric_limits<double>::quiet_NaN();
}

// GetProcAddress is used by the test plugin so the public SDK/import interface
// is unchanged. All callbacks execute synchronously on the application thread.
extern "C" __declspec(dllexport) int OrbiterTestSetObserver(
    unsigned version, OrbiterTestObserver callback, double epoch) {
    if (version != 1) return 0;
    observer = callback;
    defaultMjd = epoch;
    return 1;
}
extern "C" void OrbiterTestObserve(const char *phase, const char *object,
                                  double simt, double mjd, int running) {
    if (observer) observer(phase, object ? object : "", simt, mjd, running);
}
extern "C" double OrbiterTestDefaultMjd(double original) {
    return std::isfinite(defaultMjd) ? defaultMjd : original;
}
