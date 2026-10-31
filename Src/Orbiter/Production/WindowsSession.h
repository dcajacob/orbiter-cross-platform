// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_WINDOWS_SESSION_H
#define ORBITER_WINDOWS_SESSION_H
#include "Session.h"
class Orbiter;

namespace orbiter::production {
class WindowsSessionServices final : public SessionServices {
public:
    explicit WindowsSessionServices(Orbiter& application) : app(application) {}
    void Observe(const char* event, bool running) override;
    void ModulePreStep() override;
    void PlaybackStep() override;
    void UpdateBodies(bool force) override;
    void UpdateDialogs() override;
    void ModulePostStep() override;
    bool DeletePendingVessels() override;
    void NoVessels() override;
    void FinaliseBodies() override;
    void AdvanceTime(bool running) override;
    void WriteTrace() override;
    void UpdateCamera() override;
    void UpdatePanels(double simulationTime, double systemTime) override;
    void UpdateVisuals(bool running) override;
    void CheckSessionLimit() override;
private:
    Orbiter& app;
};
}
#endif
