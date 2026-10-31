// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Private test ABI, compiled only into observation-enabled test applications.
// Not installed, not part of the Windows SDK, and never used by propagation.
#pragma once
using OrbiterTestObserver = void (*)(const char *, const char *, double, double, int);
extern "C" void OrbiterTestObserve(const char *phase, const char *object,
                                 double simt, double mjd, int running);
extern "C" double OrbiterTestDefaultMjd(double original);
