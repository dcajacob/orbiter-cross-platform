// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "WindowsSession.h"
#include "Orbiter.h"
#include "Psys.h"
#include "Camera.h"
#include "Pane.h"
#include "DlgMgr.h"
#ifdef ORBITER_PRODUCTION_OBSERVATION
#include "ApplicationObservation.h"
#endif

extern TimeData td;
extern PlanetarySystem* g_psys;
extern Camera* g_camera;
extern Pane* g_pane;

namespace orbiter::production {
void WindowsSessionServices::Observe(const char* event, bool running)
{
#ifdef ORBITER_PRODUCTION_OBSERVATION
    OrbiterTestObserve(event, "", td.SimT0, td.MJD0, running ? 1 : 0);
#endif
}
void WindowsSessionServices::ModulePreStep() { app.ModulePreStep(); }
void WindowsSessionServices::PlaybackStep() { app.FRecorder_Play(); }
void WindowsSessionServices::UpdateBodies(bool force) { g_psys->Update(force); }
void WindowsSessionServices::UpdateDialogs()
{
    if (app.pDlgMgr) app.pDlgMgr->UpdateDialogs();
}
void WindowsSessionServices::ModulePostStep() { app.ModulePostStep(); }
bool WindowsSessionServices::DeletePendingVessels() { return app.KillVessels(); }
void WindowsSessionServices::NoVessels()
{
    if (app.hRenderWnd) DestroyWindow(app.hRenderWnd);
}
void WindowsSessionServices::FinaliseBodies()
{
    if (g_psys) g_psys->FinaliseUpdate();
}
void WindowsSessionServices::AdvanceTime(bool running) { td.EndStep(running); }
void WindowsSessionServices::WriteTrace()
{
    if (app.physicsTrace.IsOpen()) app.WritePhysicsTrace(false);
}
void WindowsSessionServices::UpdateCamera() { if (g_camera) g_camera->Update(); }
void WindowsSessionServices::UpdatePanels(double simulationTime, double systemTime)
{
    if (g_pane) g_pane->Update(simulationTime, systemTime);
}
void WindowsSessionServices::UpdateVisuals(bool running)
{
    if (app.gclient) app.gclient->clbkUpdate(running);
}
void WindowsSessionServices::CheckSessionLimit()
{
    if (app.SessionLimitReached())
        if (app.hRenderWnd) PostMessage(app.hRenderWnd, WM_CLOSE, 0, 0);
        else app.CloseSession();
}
}
