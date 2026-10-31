// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SESSION_H
#define ORBITER_PRODUCTION_SESSION_H
#include "Export.h"

class TimeData;

namespace orbiter::production {

// Internal application services. There are no window handles, graphics types,
// SDK exports or optional success stubs in this contract. A host implements every
// operation, including an explicit policy for a session with no graphics client.
class SessionServices {
public:
    virtual ~SessionServices() = default;
    virtual void Observe(const char* event, bool running) = 0;
    virtual void ModulePreStep() = 0;
    virtual void PlaybackStep() = 0;
    virtual void UpdateBodies(bool force) = 0;
    virtual void UpdateDialogs() = 0;
    virtual void ModulePostStep() = 0;
    virtual bool DeletePendingVessels() = 0;
    virtual void NoVessels() = 0;
    virtual void FinaliseBodies() = 0;
    virtual void AdvanceTime(bool running) = 0;
    virtual void WriteTrace() = 0;
    virtual void UpdateCamera() = 0;
    virtual void UpdatePanels(double simulationTime, double systemTime) = 0;
    virtual void UpdateVisuals(bool running) = 0;
    virtual void CheckSessionLimit() = 0;
};

// The production application's original two update phases. Time advancement
// begins in the host (which supplies wall-clock/fixed-step policy). Input and
// rendering stay outside these functions, at their original positions.
// References to the live flags are intentional: callbacks can change them.
class ORBITER_PRODUCTION_API Session {
public:
    static void UpdateWorld(SessionServices& services, const TimeData& time,
        const bool& running, const bool& playback, bool& stateUpdate,
        const bool& forceUpdate);
    static void EndTimeStep(SessionServices& services, TimeData& time,
        bool running, const bool& applicationRunning, bool& forceUpdate);
};

}
#endif
