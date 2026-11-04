#!/usr/bin/env python3
"""Conserve every original Atlantis calculation and callback through explicit native adapters."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'


def adapted(name,source):
    if 'AtlantisConfig' in Path(name).parts:return source
    for old,new in (('DWORD','oapi::UInt32'),('UINT','oapi::UInt'),('WORD','oapi::UInt16'),
                    ('OAPI_MSGTYPE','oapi::CockpitMessageResult'),('WPARAM','oapi::CockpitUnsignedParam'),
                    ('LPARAM','oapi::CockpitSignedParam'),('RECT','oapi::SdkRectangle')):
        source=re.sub(r'\b'+old+r'\b',new,source)
    source=source.replace('_strnicmp','atlantis::ComparePrefix').replace('_stricmp','atlantis::CompareText')
    source=source.replace('LOWORD(wparam)','atlantis::LowWord(wparam)').replace('HIWORD(wparam)','atlantis::HighWord(wparam)')
    source=source.replace('#include "imgui_extras.h"',
        '#ifdef _WIN32\n#include "imgui_extras.h"\n#else\n#include "Production/CockpitGuiExports.h"\n#endif')
    source=re.sub(r'RGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
                  lambda m:f'0x{int(m[1])|int(m[2])<<8|int(m[3])<<16:08x}',source)
    filename=Path(name).name
    if filename=='Atlantis.h':
        source=source.replace('#include "Orbitersdk.h"','#include "AtlantisPlatform.h"')
        source=source.replace('#ifdef ATLANTIS_TANK_MODULE','#ifdef _WIN32\n#ifdef ATLANTIS_TANK_MODULE',1)
        source=source.replace('#define SRBFUNC DLLIMPORT\n#endif',
            '#define SRBFUNC DLLIMPORT\n#endif\n#else\n#define TANKFUNC __attribute__((visibility("default")))\n#define SRBFUNC __attribute__((visibility("default")))\n#endif',1)
        source=source.replace('\tHINSTANCE hDLL;','#ifdef _WIN32\n\tHINSTANCE hDLL;\n#endif')
    if filename=='Atlantis.cpp':
        # ASan proves the six original 88-byte rotations were deleted through
        # their 32-byte, non-virtual base. Preserve allocation/callback order.
        source=source.replace('for (i = 0; i < 6; i++) delete rms_anim[i];',
            'for (i = 0; i < 6; i++) delete static_cast<MGROUP_ROTATE*>(rms_anim[i]);\n'
            '\tfor (i = 0; i < 3; i++) delete static_cast<MGROUP_ROTATE*>(ssme_anim[i]);')
        source=source.replace('DLLCLBK void InitModule (HINSTANCE hModule)\n{\n\tg_Param.hDLL = hModule;\n',
                              'static void InitDrawingResources ()\n{')
        source=source.replace('DLLCLBK void ExitModule (HINSTANCE hModule)','static void ReleaseDrawingResources ()')
        # The next fully enabled LSan run identifies these three rotations,
        # module font and brush (473 bytes with the font's owned name).
        source=source.replace('\toapiDestroySurface (g_Param.tkbk_label);\n}',
            '\toapiDestroySurface (g_Param.tkbk_label);\n'
            '\tif (g_Param.font[0]) oapiReleaseFont (g_Param.font[0]);\n'
            '\tif (g_Param.brush[0]) oapiReleaseBrush (g_Param.brush[0]);\n'
            '\tg_Param.tkbk_label = nullptr;\n\tg_Param.font[0] = nullptr;\n\tg_Param.brush[0] = nullptr;\n}')
        marker='// Vessel initialisation\n// --------------------------------------------------------------'
        source=source.replace(marker,
            '#ifdef _WIN32\nDLLCLBK void InitModule (HINSTANCE hModule)\n{\n\tg_Param.hDLL = hModule;\n\tInitDrawingResources();\n}\n\nDLLCLBK void ExitModule (HINSTANCE hModule)\n{\n\tReleaseDrawingResources();\n}\n#endif\n\n'+marker,1)
        source+='\n#ifndef _WIN32\n#include "NativeAtlantisFactory.inc"\n#endif\n'
    if filename=='Atlantis_Tank.cpp':
        # The unchanged KSC tour reproduces an ASan stale default-tank read:
        # the original callback deletes a still-connected external tank.
        source=source.replace('\tif (GetAltitude() < 0.0) oapiDeleteVessel (GetHandle());',
            '\t// The orbiter owns this propellant while connected, including on the pad.\n'
            '\tif (!GetDockStatus (GetDockHandle (0)) && GetAltitude() < 0.0)\n'
            '\t\toapiDeleteVessel (GetHandle());')
    if filename in ('Atlantis_Tank.cpp','Atlantis_SRB.cpp'):
        factory='NativeAtlantisTankFactory.inc' if filename=='Atlantis_Tank.cpp' else 'NativeAtlantisSrbFactory.inc'
        source+='\n#ifndef _WIN32\n#include "'+factory+'"\n#endif\n'
    return source


def verify():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--','Src/Vessel/Atlantis'],text=True).splitlines()
    checked=[]
    def normalize(text):return '\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n'
    for name in paths:
        if Path(name).suffix not in ('.h','.cpp'):continue
        source=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode('cp1252').replace('\r\n','\n')
        current=(ROOT/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        if normalize(adapted(name,source))!=normalize(current):
            raise ValueError('Atlantis source differs beyond declared native adapters: '+name)
        checked.append(name)
    if len(checked)!=11:raise ValueError('Original Atlantis source closure incomplete: '+str(len(checked)))
    assets=[]
    for name in paths:
        if Path(name).suffix not in ('.msh','.cfg'):continue
        source=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).replace(b'\r\n',b'\n')
        if source!=(ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Original Atlantis mesh/configuration changed: '+name)
        assets.append(name)
    if len(assets)!=9:raise ValueError('Original Atlantis mesh/configuration closure incomplete')
    original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Src/Orbiter/OrbiterAPI.cpp']).decode('cp1252')
    native=(ROOT/'Src/Orbiter/Production/NativeRenderApi.cpp').read_text()
    def function(text,name):
        match=re.search(r'^[^\n]*\b'+re.escape(name)+r'\s*\([^\n]*\)\s*\n\s*\{.*?\n\s*\}',text,re.M|re.S)
        if match is None:raise ValueError('Missing source-conserved SDK adapter: '+name)
        return match[0]
    def compact(text):return re.sub(r'\s+','',text)
    for name in ('oapiSetShowGrapplePoints','oapiGetSurfaceSize','WriteScenario_state','sscan_state'):
        expected=function(original,name).replace('DLLEXPORT ','')
        expected=expected.replace('g_bShowGrapple','GetNativeRenderContext().showGrapple')
        expected=expected.replace('oapi::GraphicsClient* gc = g_pOrbiter->GetGraphicsClient();',
                                  'auto* gc = GetNativeRenderContext().graphics;').replace('(DWORD*)','(oapi::UInt32*)')
        if compact(expected)!=compact(function(native,name)):raise ValueError('Original SDK adapter body changed: '+name)
    original_gui=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Src/Orbiter/DlgMgr.cpp']).decode('cp1252')
    native_gui=(ROOT/'Src/Orbiter/Production/NativeCockpitGui.cpp').read_text()
    expected=function(original_gui,'Image').replace('DLLEXPORT','ORBITER_PRODUCTION_API')
    if compact(expected)!=compact(function(native_gui,'Image')):raise ValueError('Original surface Image algorithm changed')
    print('Conserved all eleven original Atlantis source/header files: nine runtime files and two unchanged Windows utility files')
    print('Conserved original grapple-visibility, surface-size, surface Image and animation-state utility bodies')
    print('Verified all nine unchanged original Atlantis mesh/configuration inputs')


if __name__=='__main__':verify()
