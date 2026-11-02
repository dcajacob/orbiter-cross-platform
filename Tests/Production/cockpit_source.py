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
       'MfdMap_old.h','MfdOrbit.h','MfdSurface.h','MfdSync.h','MfdTransfer.h','Astro.h',
       'MfdOrbit.cpp','MfdAlign.cpp','MfdComms.cpp','MfdDocking.cpp','MfdHsi.cpp','MfdLanding.cpp',
       'MfdMap.cpp','MfdSync.cpp','MfdTransfer.cpp')

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
    services=windows(raw('Src/Orbiter/Production/CockpitServices.h'))
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
#include "CockpitGraphics.h"
#include "BodyServices.h"
#include "RigidBodyServices.h"
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
namespace orbiter::production {
inline oapi::UInt32 CockpitColor(std::uint8_t r,std::uint8_t g,std::uint8_t b) {return RGB(r,g,b);}
inline Config* CockpitConfiguration() {return &GetCameraServices().Configuration();}
inline oapi::CockpitClient* CockpitGraphicsClient() {return g_pOrbiter->GetGraphicsClient();}
inline std::filesystem::path CockpitConfigPath(const char* name) {return g_pOrbiter->ConfigPath(name);}
inline bool CockpitReleaseSurface(SURFHANDLE surface) {return g_pOrbiter->ReleaseSurface(surface);}
inline oapi::UInt32 CockpitDeviceColour(std::uint8_t r,std::uint8_t g,std::uint8_t b) {return g_pOrbiter->GetDeviceColour(r,g,b);}
inline bool CockpitFillSurface(SURFHANDLE surface,oapi::UInt32 color) {return g_pOrbiter->FillSurface(surface,color);}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,oapi::UInt32 flags=0) {return g_pOrbiter->Blt(target,x,y,source,flags);}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,oapi::UInt32 sx,oapi::UInt32 sy,oapi::UInt32 width,oapi::UInt32 height,oapi::UInt32 flags=0) {return g_pOrbiter->Blt(target,x,y,source,sx,sy,width,height,flags);}
}
#endif''',services,'Windows cockpit service adapter identities')
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#define ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#include "RigidBodyServices.h"
#include "CockpitServices.h"
#include "OrbiterScalar.h"
#include "OrbiterGeometry.h"
#include "FlightKeys.h"
#include "ConfigFile.h"
#include "Config.h"
#include "Text.h"
#include <algorithm>
inline double normangle(double angle) {double a=fmod(angle,PI2);return a>=PI?a-PI2:a< -PI?a+PI2:a;}
inline double posangle(double angle) {return orbiter::math::PositiveAngle(angle,PI2);}
#define TRACENEW orbiter::production::GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
#endif''',raw('Src/Orbiter/Production/CockpitNativeSupport.h'),'Native instrument math, text and allocation bindings')
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
        for service,application in [('CockpitColor','RGB'),('CockpitGraphicsClient','g_pOrbiter->GetGraphicsClient'),('CockpitReleaseSurface','g_pOrbiter->ReleaseSurface'),('CockpitDeviceColour','g_pOrbiter->GetDeviceColour'),('CockpitFillSurface','g_pOrbiter->FillSurface'),('CockpitBlt','g_pOrbiter->Blt'),('CockpitConfigPath','g_pOrbiter->ConfigPath'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp')]:
            current=current.replace('orbiter::production::'+service,application)
        for a,b in [('oapi::UInt32','DWORD'),('std::intptr_t','INT_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkFont','HFONT'),('oapi::SdkPoint','POINT'),('oapi::UInt','UINT'),('oapi::SdkRectangle','RECT')]:current=current.replace(a,b)
        if name in ('Mfd.h','hud.h'):current=current.replace('#include "Production/CockpitGraphics.h"','#include "GraphicsAPI.h"')
        else:current=current.replace('#include "Production/CockpitGraphics.h"','')
        if name=='Mfd.h':current=current.replace('class Pane;','class Pane;\nclass oapi::GraphicsClient;',1)
        if name=='MfdHsi.cpp':current=current.replace('static const int arrowseg','static const INT arrowseg').replace('static const int narrowseg','static const INT narrowseg')
        if name=='MfdAlign.cpp':current=current.replace('saveprm = {0,0,0,false,0.0,0.0}','saveprm = {0,0,0,0.0,0.0,false}')
        current=restore_geometry(name,current,original)
        equal(original.replace('COLORREF','DWORD'),current.replace('COLORREF','DWORD'),'Original cockpit calculations, declarations and call order: '+name)
    print('Original Pane, HUD, MFD and panel algorithms conserved; Windows graphics pointer types unchanged')
if __name__=='__main__':verify()
