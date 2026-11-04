#!/usr/bin/env python3
"""Conserve every original HST, solar-sail and quadcopter calculation and Lua method."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
FAMILIES=('HST','Solarsail','Quadcopter')


def adapted(name,source):
    for old,new in (('DWORD','oapi::UInt32'),('UINT','oapi::UInt'),('WORD','oapi::UInt16')):
        source=re.sub(r'\b'+old+r'\b',new,source)
    source=source.replace('#include "orbitersdk.h"','#include "../StockVesselPlatform.h"')
    source=source.replace('#include "..\\Common\\Instrument.h"','#include "../Common/Instrument.h"')
    source=source.replace('_strnicmp','stock_vessel::ComparePrefix')
    filename=Path(name).name
    if filename=='HST.cpp':source+='\n#ifndef _WIN32\n#include "NativeHstFactory.inc"\n#endif\n'
    if filename=='HST_Lua.cpp':
        for function in ('hstAntenna','hstHatch','hstArray'):
            old='int '+function+' (lua_State *L);'
            if source.count(old)!=1:raise ValueError('HST Lua declaration changed')
            source=source.replace(old,'static '+old)
    if filename=='SailLua.cpp':
        source=source.replace('int sailSetPaddle (lua_State *L);','static int sailSetPaddle (lua_State *L);')
    if filename=='Solarsail.cpp':
        source=source.replace('DLLCLBK void InitModule (HINSTANCE hModule)','static void InitSailResources ()')
        source=source.replace('DLLCLBK void ExitModule (HINSTANCE hModule)','static void ReleaseSailResources ()')
        marker='// Vessel initialisation\n// --------------------------------------------------------------'
        if source.count(marker)!=1:raise ValueError('Solar-sail module entry marker changed')
        source=source.replace(marker,
            '#ifdef _WIN32\nDLLCLBK void InitModule (HINSTANCE hModule)\n{\n\tInitSailResources();\n}\n\n'
            'DLLCLBK void ExitModule (HINSTANCE hModule)\n{\n\tReleaseSailResources();\n}\n#endif\n\n'+marker)
        source+='\n#ifndef _WIN32\n#include "NativeSolarSailFactory.inc"\n#endif\n'
    if filename=='Quadcopter.cpp':source+='\n#ifndef _WIN32\n#include "NativeQuadcopterFactory.inc"\n#endif\n'
    return source


def original_files():
    return subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--',
        *('Src/Vessel/'+name for name in FAMILIES)],text=True).splitlines()


def verify():
    checked=[];resources=[]
    for name in original_files():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name])
        actual=(ROOT/name).read_bytes()
        if Path(name).suffix in ('.cpp','.h'):
            expected=adapted(name,body.decode('cp1252').replace('\r\n','\n'))
            if expected!=actual.decode('cp1252').replace('\r\n','\n'):
                raise ValueError('Original remaining-vessel source changed beyond explicit platform bindings: '+name)
            checked.append(name)
        else:
            text=Path(name).suffix in ('.cfg','.msh','.txt')
            if (actual.replace(b'\r\n',b'\n')!=body.replace(b'\r\n',b'\n') if text else actual!=body):
                raise ValueError('Original module resource or installation rule changed: '+name)
            resources.append(name)
    if len(checked)!=14:raise ValueError('Original HST/solar-sail/quadcopter source closure incomplete')
    print('Conserved all 14 original HST/solar-sail/quadcopter source/header/Lua files and '+str(len(resources))+
          ' unchanged resources/install rules; all original physical, animation, deformation and Lua operations retained')


if __name__=='__main__':verify()
