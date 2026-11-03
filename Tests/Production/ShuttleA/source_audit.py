#!/usr/bin/env python3
"""Conserve every original Shuttle-A and payload calculation and callback body.

Only explicit SDK spellings, source resource loading, module resource hooks,
Windows editor guards and C++ Lua linkage declarations are adapted. Existing
references, scenario files, equations and callback order are never regenerated.
"""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'


def adapted(name,original):
    s=original
    for a,b in [('DWORD','oapi::UInt32'),('UINT','oapi::UInt'),('WORD','oapi::UInt16')]:s=re.sub(r'\b'+a+r'\b',b,s)
    s=s.replace('..\\Common\\Instrument.h','../Common/Instrument.h')
    for h in ('orbitersdk.h','Orbitersdk.h'):
     s=s.replace('#include "'+h+'"','#include "'+('../' if Path(name).parent.name=='ShuttleA_PL' else '')+'ShuttleAPlatform.h"')
    s=s.replace('_strnicmp','shuttlea::ComparePrefix').replace('_stricmp','shuttlea::CompareText')
    if Path(name).name=='ShuttleA.h':s=s.replace('\tHINSTANCE hDLL;','\n#ifdef _WIN32\n\tHINSTANCE hDLL;\n#endif')
    if Path(name).name=='ShuttleA.cpp':
     s=s.replace('#include "ScnEditorAPI.h"\n#include "DlgCtrl.h"','#ifdef _WIN32\n#include "ScnEditorAPI.h"\n#include "DlgCtrl.h"\n#else\n#define DLLCLBK static\n#endif')
     s=s.replace('#include "resource.h"','#ifdef _WIN32\n#include "resource.h"\n#endif')
     s=s.replace('#define LOADBMP(id) (LoadBitmap (g_Param.hDLL, MAKEINTRESOURCE (id)))','#ifdef _WIN32\n#define LOADBMP(id) (LoadBitmap (g_Param.hDLL, MAKEINTRESOURCE (id)))\n#endif')
     s=s.replace('DLLCLBK void InitModule (HINSTANCE hModule)\n{\n\tg_Param.hDLL = hModule;\n\toapiRegisterCustomControls (hModule);\n','static void InitDrawingResources ()\n{')
     for color in ['120, 220, 120','220, 220, 120','0, 0, 0','0, 96, 0']:
      vals=[int(v) for v in color.split(',')];packed=vals[0]|vals[1]<<8|vals[2]<<16
      s=s.replace('RGB('+color+')',f'0x{packed:08x}')
     s=s.replace('DLLCLBK void ExitModule (HINSTANCE hModule)','static void ReleaseDrawingResources ()')
     s=s.replace('\toapiUnregisterCustomControls (g_Param.hDLL);\n}', '\n#ifndef _WIN32\n\tfor (auto &font : g_Param.pFont) font = nullptr;\n\tfor (auto &pen : g_Param.pPen) pen = nullptr;\n\tfor (auto &brush : g_Param.pBrush) brush = nullptr;\n\tShuttleA::panel2dtex = ShuttleA::paneleltex = ShuttleA::aditex = nullptr;\n#endif\n}\n\n#ifdef _WIN32\nDLLCLBK void InitModule (HINSTANCE hModule)\n{\n\tg_Param.hDLL = hModule;\n\toapiRegisterCustomControls (hModule);\n\tInitDrawingResources();\n}\n\nDLLCLBK void ExitModule (HINSTANCE hModule)\n{\n\tReleaseDrawingResources();\n\toapiUnregisterCustomControls (g_Param.hDLL);\n}\n#endif')
     s=s.replace('ShuttleA *GetV (HWND hDlg)','#ifdef _WIN32\nShuttleA *GetV (HWND hDlg)')
     s+='\n#else\n#include "NativeShuttleAFactory.inc"\n#endif\n'
    if Path(name).name=='ShuttleA_pl.cpp':
     s=s.replace('#include <stdio.h>','#include <stdio.h>\n#ifndef _WIN32\n#define DLLCLBK static\n#endif')
     s=s.replace('DLLCLBK void InitModule (HINSTANCE hModule)','#ifdef _WIN32\nDLLCLBK void InitModule (HINSTANCE hModule)')
     s=s.replace('// Vessel initialisation\n// --------------------------------------------------------------','// Vessel initialisation\n// --------------------------------------------------------------\n#endif')
     s+='\n#ifndef _WIN32\n#include "NativeShuttleAPayloadFactory.inc"\n#endif\n'
    if Path(name).name=='ShuttleA.cpp':
        s=s.replace('#define LOADBMP(id) (LoadBitmap (g_Param.hDLL, MAKEINTRESOURCE (id)))', '#define LOADBMP(id) (LoadBitmap (g_Param.hDLL, MAKEINTRESOURCE (id)))\n#define SHUTTLEA_BITMAP(id, name) oapiCreateSurface (LOADBMP (id))\n#else\n#define SHUTTLEA_BITMAP(id, name) oapiLoadSurfaceEx("ShuttleA/Bitmaps/" name, OAPISURFACE_NOMIPMAPS)')
        s=re.sub(r'oapiCreateSurface \(LOADBMP \((IDB_([A-Z0-9]+))\)\)',lambda m:'SHUTTLEA_BITMAP ('+m[1]+', "'+m[2].lower()+'.bmp")',s)
        s=re.sub(r'RGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',lambda m:f'0x{int(m[1])|int(m[2])<<8|int(m[3])<<16:08x}',s)
    if Path(name).name=='ShuttleALua.cpp':
        end=s.index('// ==========================================================================',s.index('// API function prototypes'))
        a,b=s[:end],s[end:]
        a=re.sub(r'^int (lua_gear|set_\w+) \(',r'static int \1 (',a,flags=re.M)
        s=a+b
    return s


def normalized(source):
    return '\n'.join(line.rstrip() for line in source.splitlines()).rstrip()+'\n'


def verify():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--','Src/Vessel/ShuttleA'],text=True).splitlines()
    checked=[]
    for name in paths:
        if Path(name).suffix not in ('.h','.cpp'):continue
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode('cp1252').replace('\r\n','\n')
        actual=(ROOT/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        if normalized(adapted(name,original))!=normalized(actual):
            raise ValueError('Shuttle-A source changed beyond declared platform adapters: '+name)
        checked.append(name)
    if len(checked)!=40:raise ValueError('Incomplete Shuttle-A source conservation scope: '+str(len(checked)))
    print('Conserved all',len(checked),'original Shuttle-A and payload source/header files')


if __name__=='__main__':verify()
