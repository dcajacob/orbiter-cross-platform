#!/usr/bin/env python3
"""Prove shared creation/focus/deletion control flow preserves original Windows code."""
from pathlib import Path
import subprocess
from vessel_runtime_source import equal,span
ROOT=Path(__file__).resolve().parents[2]
BEFORE='88eaa185'
CALLBACKS={'\tif (g_pane) g_pane->FocusChanged (g_focusobj);': '\tservices.PaneFocusChanged(g_focusobj);',
 '\tfor (auto it = m_Plugin.begin(); it != m_Plugin.end(); it++)\n\t\tit->pModule->clbkFocusChanged(g_focusobj, g_pfocusobj);': '\t'
                                                                                                                                'services.ModuleFocusChanged(g_focusobj,g_pfocusobj);',
 '\tif (pDlgMgr) pDlgMgr->BroadcastMessage (MSG_FOCUSVESSEL, vessel);': '\t'
                                                                        'services.DialogFocusChanged(vessel);',
 '\tfor (auto it = m_Plugin.begin(); it != m_Plugin.end(); it++)\n\t\tit->pModule->clbkNewVessel((OBJHANDLE)vessel);': '\t'
                                                                                                                       'services.ModuleNewVessel(vessel);',
 '\tif (gclient)\n\t\tgclient->clbkNewVessel((OBJHANDLE)vessel);': '\t'
                                                                   'services.GraphicsNewVessel(vessel);',
 '\tif (pDlgMgr) pDlgMgr->BroadcastMessage (MSG_CREATEVESSEL, vessel);': '\t'
                                                                         'services.DialogNewVessel(vessel);',
 '\t\t\tfor (auto it = m_Plugin.begin(); it != m_Plugin.end(); it++)\n\t\t\t\tit->pModule->clbkDeleteVessel((OBJHANDLE)vessel);': '\t\t\t'
                                                                                                                                  'services.ModuleDeleteVessel(vessel);',
 '\t\t\tif (gclient)\n\t\t\t\tgclient->clbkDeleteVessel((OBJHANDLE)vessel);': '\t\t\t'
                                                                              'services.GraphicsDeleteVessel(vessel);',
 '\t\t\tif (g_pane) g_pane->DelVessel (vessel);': '\t\t\tservices.PaneDeleteVessel(vessel);',
 '\t\t\tif (pDlgMgr) pDlgMgr->BroadcastMessage (MSG_KILLVESSEL, vessel);': '\t\t\t'
                                                                           'services.DialogDeleteVessel(vessel);',
 '\t\t\tif (m_pConsole) {\n\t\t\t\tchar cbuf[256];\n\t\t\t\tsprintf (cbuf, "Vessel %s deleted", vessel->Name());\n\t\t\t\tm_pConsole->Echo(cbuf);\n\t\t\t}': '\t\t\t'
                                                                                                                                                             'services.ConsoleDeleteVessel(vessel);'}

def verify():
    old=subprocess.check_output(['git','-C',str(ROOT),'show',BEFORE+':Src/Orbiter/Orbiter.cpp']).decode().replace('\r\n','\n')
    shared=(ROOT/'Src/Orbiter/Production/VesselLifetime.h').read_text()
    current=(ROOT/'Src/Orbiter/Orbiter.cpp').read_text()
    for name in ('SetFocusObject','InsertVessel','KillVessels'):
        a,b=span(old,'Orbiter::'+name);original=old[a:b];c,d=span(shared,name);actual=shared[c:d]
        body=actual[actual.index('{')+1:-1]
        for alias in ('auto*& g_focusobj=services.CurrentFocus();','auto*& g_pfocusobj=services.PreviousFocus();','auto*& g_psys=services.LifetimeWorld();','auto*& g_camera=services.LifetimeCamera();'):
            body=body.replace(alias,'')
        body=body.replace('SetFocusObject (services, ','SetFocusObject (').replace('services.SetView','SetView').replace('UInt32 j;','DWORD j;')
        for before,after in CALLBACKS.items():body=body.replace(after,before)
        equal(original[original.index('{')+1:-1],body,'Original '+name+' ordering/selection/ownership')
        c,d=span(current,'Orbiter::'+name);wrapper=current[c:d]
        expected=original[:original.index('{')+1]+'\norbiter::production::WindowsVesselLifetime services(*this);\n'+('return ' if name!='InsertVessel' else '')+'orbiter::production::'+name+'(services'+(', vessel, setview' if name=='SetFocusObject' else ', vessel' if name=='InsertVessel' else '')+');\n}'
        equal(expected,wrapper,'Windows '+name+' adapter')
    print('Original Windows focus, creation and deferred deletion algorithms shared with native host')
if __name__=='__main__':verify()
