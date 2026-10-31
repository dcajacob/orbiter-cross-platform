// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "Session.h"
#include "TimeData.h"

namespace orbiter::production {

void Session::UpdateWorld(SessionServices& services, const TimeData& time,
    const bool& running, const bool& playback, bool& stateUpdate,
    const bool& forceUpdate)
{
    services.Observe("world.update.before", running);
    if (running) services.ModulePreStep();

    stateUpdate = true;
    if (running && time.SimDT) {
        if (playback) services.PlaybackStep();
        services.UpdateBodies(forceUpdate);
    }
    services.UpdateDialogs();
    if (running) services.ModulePostStep();
    stateUpdate = false;
    if (!services.DeletePendingVessels()) services.NoVessels();
    services.Observe("world.update.after", running);
}

void Session::EndTimeStep(SessionServices& services, TimeData& time,
    bool running, const bool& applicationRunning, bool& forceUpdate)
{
    if (running) {
        services.Observe("world.finalise.before", true);
        services.FinaliseBodies();
        services.Observe("world.finalise.after", true);
    }

    services.Observe("time.end.before", running);
    services.AdvanceTime(running);
    services.Observe("time.end.after", running);
    if (running) services.WriteTrace();

    services.UpdateCamera();
    services.UpdatePanels(time.SimT1, time.SysT1);
    services.UpdateVisuals(applicationRunning);
    forceUpdate = false;
    services.Observe("app.frame.end", running);
    services.CheckSessionLimit();
}

}
