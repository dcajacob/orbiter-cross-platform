#!/usr/bin/env python3
"""Conserve original cockpit algorithms while introducing real platform services."""
import subprocess
from pathlib import Path
from camera_source import windows
from vessel_runtime_source import equal,raw
ROOT=Path(__file__).resolve().parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
FILES=('Pane.h','Pane.cpp','Mfd.h','Mfd.cpp','hud.h','hud.cpp','Panel.h',
       'Defpanel.h','Defpanel.cpp','Panel2D.h','VCockpit.h','VCockpit.cpp',
       'VectorMap.h','VectorMap.cpp','MfdSurface.cpp','Select.h',
       'MfdAlign.h','MfdComms.h','MfdDocking.h','MfdHsi.h','MfdLanding.h','MfdMap.h',
       'MfdMap_old.h','MfdOrbit.h','MfdSurface.h','MfdSync.h','MfdTransfer.h')

def restore_geometry(name,current,original):
    """Prove the shared production conic implementation is an exact code move."""
    if name=='Mfd.cpp':
        body=original[original.index('// =======================================================================\n// local utility functions'):]
        expected='// Copyright (c) Martin Schweiger\n// Licensed under the MIT License\n\n#include "MfdOrbitGeometry.h"\n\nusing namespace std;\n\n'+body
        equal(expected,raw('Src/Orbiter/MfdOrbitGeometry.cpp'),'Original shared MFD conic implementation')
        current=current.rstrip()+'\n\n\n'+body
    elif name=='Mfd.h':
        constants=original[original.index('#define ELN '):original.index('const int MAXPEN')]
        start=original.index('// =======================================================================\n// local prototypes')
        declarations=original[start:original.index('#endif // !__MFD_H',start)]
        expected='// Copyright (c) Martin Schweiger\n// Licensed under the MIT License\n\n#ifndef ORBITER_MFD_ORBIT_GEOMETRY_H\n#define ORBITER_MFD_ORBIT_GEOMETRY_H\n#include "Element.h"\n#include "DrawAPI.h"\n\n'+constants+declarations+'#endif\n'
        equal(expected,raw('Src/Orbiter/MfdOrbitGeometry.h'),'Original shared MFD conic declarations and screen mapping')
        current=current.replace('#include "MfdOrbitGeometry.h"\n\n',constants,1)
        current=current.replace('#endif // !__MFD_H',declarations+'#endif // !__MFD_H',1)
    return current

def verify():
    if (ROOT/'Src/Orbiter/Production/CockpitServices.h').exists():
        equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
namespace orbiter::production {
inline Config* CockpitConfiguration() {return &GetCameraServices().Configuration();}
}
#endif''',raw('Src/Orbiter/Production/CockpitServices.h'),'Shared cockpit configuration binding')
    header=windows(raw('Src/Orbiter/Production/CockpitGraphics.h'))
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#define ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#include "GraphicsAPI.h"
namespace oapi {using CockpitClient=GraphicsClient;}
#endif''',header,'Windows cockpit graphics type identity')
    for name in FILES:
        path='Src/Orbiter/'+name
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]).decode('cp1252').replace('\r\n','\n')
        current=windows(raw(path)).replace('oapi::CockpitClient','oapi::GraphicsClient')
        current=current.replace('orbiter::production::CockpitConfiguration()','g_pOrbiter->Cfg()')
        current=current.replace('#include "Production/CockpitServices.h"','')
        for a,b in [('oapi::UInt32','DWORD'),('std::intptr_t','INT_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkFont','HFONT'),('oapi::SdkPoint','POINT')]:current=current.replace(a,b)
        if name in ('Mfd.h','hud.h'):current=current.replace('#include "Production/CockpitGraphics.h"','#include "GraphicsAPI.h"')
        else:current=current.replace('#include "Production/CockpitGraphics.h"','')
        if name=='Mfd.h':current=current.replace('class Pane;','class Pane;\nclass oapi::GraphicsClient;',1)
        current=restore_geometry(name,current,original)
        equal(original.replace('COLORREF','DWORD'),current.replace('COLORREF','DWORD'),'Original cockpit calculations, declarations and call order: '+name)
    print('Original Pane, HUD, MFD and panel algorithms conserved; Windows graphics pointer types unchanged')
if __name__=='__main__':verify()
