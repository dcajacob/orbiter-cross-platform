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
class Pane;class Select;class InputBox;
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
extern Pane* g_pane;extern Select* g_select;extern InputBox* g_input;extern HELPCONTEXT DefHelpContext;
extern TimeData td;extern PlanetarySystem* g_psys;extern Vessel* g_focusobj;
namespace orbiter::production {
inline int CockpitScreenHeight() {return GetSystemMetrics(SM_CYSCREEN);}
inline TimeData& CockpitTime() {return td;}
inline PlanetarySystem* CockpitWorld() {return g_psys;}
inline Vessel* CockpitFocus() {return g_focusobj;}
inline Pane* CockpitPane() {return g_pane;}
inline Select* CockpitSelect() {return g_select;}
inline InputBox* CockpitInput() {return g_input;}
inline HELPCONTEXT& CockpitHelpContext() {return DefHelpContext;}
inline std::uint16_t CockpitHighWord(oapi::UInt32 value) {return HIWORD(value);}
inline std::uint16_t CockpitLowWord(oapi::UInt32 value) {return LOWORD(value);}
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
        # Only the original known Elements call sites receive explicit time.
        current=current.replace('new Elements(orbiter::production::CockpitTime().MJD_ref)','new Elements()')
        import re
        pattern=re.compile(r'\b(?:shpel2?|tgtel|el2)->(?:Setup|Set|Reset|Update)\s*\(')
        for match in reversed(list(pattern.finditer(current))):
            start=match.end()-1;depth=1;end=start+1
            while depth:
                if current[end]=='(':depth+=1
                elif current[end]==')':depth-=1
                end+=1
            argument='orbiter::production::CockpitTime().SimT1' if '->Update' in match.group(0) else 'orbiter::production::CockpitTime().MJD_ref'
            suffix=', '+argument
            if not current[:end-1].endswith(suffix):raise ValueError('Instrument Elements lacks its explicit original time input: '+name)
            current=current[:end-1-len(suffix)]+current[end-1:]
        for service,application in [('CockpitTime()','td'),('CockpitWorld()','g_psys'),('CockpitFocus()','g_focusobj'),('CockpitPane()','g_pane'),('CockpitSelect()','g_select'),('CockpitInput()','g_input'),('CockpitHelpContext()','DefHelpContext')]:
            current=current.replace('orbiter::production::'+service,application)
        current=current.replace('orbiter::production::CockpitConfiguration()','g_pOrbiter->Cfg()')
        current=current.replace('#include "Production/CockpitServices.h"','')
        for service,application in [('CockpitColor','RGB'),('CockpitGraphicsClient','g_pOrbiter->GetGraphicsClient'),('CockpitReleaseSurface','g_pOrbiter->ReleaseSurface'),('CockpitDeviceColour','g_pOrbiter->GetDeviceColour'),('CockpitFillSurface','g_pOrbiter->FillSurface'),('CockpitBlt','g_pOrbiter->Blt'),('CockpitConfigPath','g_pOrbiter->ConfigPath'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),('CockpitHighWord','HIWORD'),('CockpitLowWord','LOWORD')]:
            current=current.replace('orbiter::production::'+service,application)
        for a,b in [('oapi::UInt32','DWORD'),('std::intptr_t','INT_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkFont','HFONT'),('oapi::SdkPoint','POINT'),('oapi::UInt','UINT'),('oapi::SdkRectangle','RECT')]:current=current.replace(a,b)
        if name in ('Mfd.h','hud.h'):current=current.replace('#include "Production/CockpitGraphics.h"','#include "GraphicsAPI.h"')
        else:current=current.replace('#include "Production/CockpitGraphics.h"','')
        if name=='Mfd.h':current=current.replace('class Pane;','class Pane;\nclass oapi::GraphicsClient;',1)
        if name=='VectorMap.h':current=current.replace('explicit DRAWDATA(double reference_mjd):focusel(reference_mjd),tgtvel(reference_mjd) {}','',1)
        if name=='VectorMap.cpp':
            current=current.replace(':drawdata(td.MJD_ref)','')
            current=current.replace('drawdata.focusel.Set (*g_focusobj->Els(), td.MJD_ref)','drawdata.focusel.Set (*g_focusobj->Els())')
            current=current.replace('orbiter::production::CockpitScreenHeight()','GetSystemMetrics(SM_CYSCREEN)')
        if name=='MfdHsi.cpp':current=current.replace('static const int arrowseg','static const INT arrowseg').replace('static const int narrowseg','static const INT narrowseg')
        if name=='MfdAlign.cpp':current=current.replace('saveprm = {0,0,0,false,0.0,0.0}','saveprm = {0,0,0,0.0,0.0,false}')
        if name=='Mfd.cpp':current=current.replace('(long long)id + 1','(int64_t)id + 1')
        current=restore_geometry(name,current,original)
        equal(original.replace('COLORREF','DWORD'),current.replace('COLORREF','DWORD'),'Original cockpit calculations, declarations and call order: '+name)
    print('Original Pane, HUD, MFD and panel algorithms conserved; Windows graphics pointer types unchanged')
if __name__=='__main__':verify()
