#!/usr/bin/env python3
"""Conserve the original callbacks in the shared Windows/native cockpit path."""
from pathlib import Path
import subprocess
from vessel_runtime_source import equal,span
ROOT=Path(__file__).resolve().parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
def original(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode('cp1252').replace('\r\n','\n')
def raw(name):return (ROOT/name).read_text()
def canonical(text):
    for a,b in [('oapi::CockpitClient','oapi::GraphicsClient'),('oapi::UInt32','DWORD'),('oapi::SdkRectangle','RECT'),
        ('orbiter::production::CockpitGraphicsClient()','g_pOrbiter->GetGraphicsClient()'),
        ('orbiter::production::CockpitCamera()','g_camera'),('orbiter::production::CockpitFocus()','g_focusobj'),
        ('orbiter::production::CockpitPane()','g_pane')]:text=text.replace(a,b)
    return text
def callbacks():
    vessel=original('Src/Orbiter/VesselApplication.cpp');sdk=original('Src/Orbiter/VesselSdkApplication.cpp')
    expected={
        'CockpitVesselMethods.inc':vessel[vessel.index('void Vessel::DrawHUD'):vessel.index('bool Vessel::LoadModule')],
        'CockpitCameraMethods.inc':sdk[sdk.index('void VESSEL::SetCameraDefaultDirection'):sdk.index('DEVMESHHANDLE VESSEL::GetDevMesh')],
        'CockpitPanelMethods.inc':sdk[sdk.index('int VESSEL3::SetPanelBackground'):]}
    bodies={}
    for name,old in expected.items():
        bodies[name]=canonical(raw('Src/Orbiter/Production/'+name))
        equal(old,bodies[name],'Shared original stock cockpit callbacks: '+name)
    return bodies
def restore(path,text):
    if 'Production/CockpitVesselMethods.inc' not in text and 'Production/CockpitCameraMethods.inc' not in text:return text
    bodies=callbacks()
    for name,body in bodies.items():text=text.replace('#include "Production/'+name+'"',body)
    return text.replace('#include "Production/CockpitServices.h"','')
def verify():
    callbacks()
    wrapper=raw('Src/Orbiter/Production/NativeCockpitVessel.cpp')
    equal('''#include "CockpitVesselMethods.inc"
#include "CockpitCameraMethods.inc"
#include "CockpitPanelMethods.inc"''',wrapper[wrapper.index('#include "CockpitVesselMethods.inc"'):],
        'Native cockpit callback adapter uses only the shared implementations')
    for path in ('Src/Orbiter/VesselApplication.cpp','Src/Orbiter/VesselSdkApplication.cpp'):
        equal(original(path),restore(path,raw(path)),'Original Windows application adapter: '+path)
    dialogs=original('Src/Orbiter/DlgMgr.cpp');native=raw('Src/Orbiter/Production/NativeCockpitGui.cpp')
    for name in ('ImGuiDialog::Display','ImGuiDialog::Activate','BeginAnimatedPopup','EndAnimatedPopup'):
        a,b=span(dialogs,name);c,d=span(native,name)
        equal(dialogs[a:b].replace('DLLEXPORT','ORBITER_PRODUCTION_API'),native[c:d],'Original native dialog/widget algorithm: '+name)
    source=original('Src/Orbiter/Orbiter.cpp')
    for value in ('launch_tick = 3;','deltat = 1e-2;','launch_tick--;','if(deltat>0.1) deltat=0.1;'):
        if value not in source:raise ValueError('Original Windows startup clock policy changed: '+value)
    print('Original stock cockpit callbacks shared by Windows/native; dialog and startup clock algorithms conserved')
if __name__=='__main__':verify()
