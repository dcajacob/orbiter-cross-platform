// Licensed under the MIT License
#include "WindowsVesselLifetime.h"
#include "Orbiter.h"
#include "Pane.h"
#include "DlgMgr.h"
#include "console_ng.h"
extern PlanetarySystem* g_psys;
extern Camera* g_camera;
extern Pane* g_pane;
extern Vessel* g_focusobj;
extern Vessel* g_pfocusobj;
namespace orbiter::production {
PlanetarySystem*& WindowsVesselLifetime::LifetimeWorld() {return g_psys;}
Camera*& WindowsVesselLifetime::LifetimeCamera() {return g_camera;}
Vessel*& WindowsVesselLifetime::CurrentFocus() {return g_focusobj;}
Vessel*& WindowsVesselLifetime::PreviousFocus() {return g_pfocusobj;}
void WindowsVesselLifetime::SetView(Body* body,int mode) {app.SetView(body,mode);}
void WindowsVesselLifetime::PaneFocusChanged(Vessel* vessel) {if(g_pane)g_pane->FocusChanged(vessel);}
void WindowsVesselLifetime::ModuleFocusChanged(Vessel* now,Vessel* previous) {
    if(app.RecorderStatus()==1 && app.Cfg()->CfgRecPlayPrm.bRecordFocus)
        app.FRecorder_SaveEvent("FOCUS",now->Name());
    for(auto it=app.m_Plugin.begin();it!=app.m_Plugin.end();++it)it->pModule->clbkFocusChanged(now,previous);
}
void WindowsVesselLifetime::DialogFocusChanged(Vessel* vessel) {if(app.pDlgMgr)app.pDlgMgr->BroadcastMessage(MSG_FOCUSVESSEL,vessel);}
void WindowsVesselLifetime::ModuleNewVessel(Vessel* vessel) {
    for(auto it=app.m_Plugin.begin();it!=app.m_Plugin.end();++it)it->pModule->clbkNewVessel(vessel);
}
void WindowsVesselLifetime::GraphicsNewVessel(Vessel* vessel) {if(app.gclient)app.gclient->clbkNewVessel(vessel);}
void WindowsVesselLifetime::DialogNewVessel(Vessel* vessel) {if(app.pDlgMgr)app.pDlgMgr->BroadcastMessage(MSG_CREATEVESSEL,vessel);}
void WindowsVesselLifetime::ModuleDeleteVessel(Vessel* vessel) {
    for(auto it=app.m_Plugin.begin();it!=app.m_Plugin.end();++it)it->pModule->clbkDeleteVessel(vessel);
}
void WindowsVesselLifetime::GraphicsDeleteVessel(Vessel* vessel) {if(app.gclient)app.gclient->clbkDeleteVessel(vessel);}
void WindowsVesselLifetime::PaneDeleteVessel(Vessel* vessel) {if(g_pane)g_pane->DelVessel(vessel);}
void WindowsVesselLifetime::DialogDeleteVessel(Vessel* vessel) {if(app.pDlgMgr)app.pDlgMgr->BroadcastMessage(MSG_KILLVESSEL,vessel);}
void WindowsVesselLifetime::ConsoleDeleteVessel(Vessel* vessel) {
    if(app.m_pConsole) {char text[256];sprintf(text,"Vessel %s deleted",vessel->Name());app.m_pConsole->Echo(text);}
}
}
