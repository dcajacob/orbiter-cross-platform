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
    if filename=='PropulsionSubsys.h':
        source=source.replace('\tPropulsionSubsystem(Quadcopter *qc);',
            '\tPropulsionSubsystem(Quadcopter *qc);\n\t~PropulsionSubsystem() override;')
    if filename=='PropulsionSubsys.cpp':
        source=source.replace('double PropulsionSubsystem::getAtmDensity() const',
            'PropulsionSubsystem::~PropulsionSubsystem()\n{\n\tfor (int i = 0; i < 4; i++) delete m_rotor[i];\n}\n\n'
            'double PropulsionSubsystem::getAtmDensity() const')
    if filename=='SolarSail.h':
        source=source.replace('\tstatic void GlobalSetup();','\tstatic void GlobalSetup();\n\tstatic void GlobalCleanup();')
        source=source.replace('\tstatic VECTOR3 *sail_vbuf;   // vertex temporary buffer',
            '\tstatic VECTOR3 *sail_vbuf;   // vertex temporary buffer\n'
            '\tstatic VECTOR3 *sail_nml;\n\tstatic oapi::UInt32 *sail_nsd;')
    if filename=='Solarsail.cpp':
        # Actual two-session LSan evidence loses the first 153-node graph
        # and vertex buffer. Give the original shared scratch caches the
        # same explicit module lifetime as the indices. Keep traversal exact.
        source=source.replace('\tstatic VECTOR3 *nml = 0;','\tVECTOR3 *&nml = sail_nml;')
        source=source.replace('\tstatic oapi::UInt32 *nsd = 0;','\toapi::UInt32 *&nsd = sail_nsd;')
        marker='void SolarSail::SetupElasticity (MESHHANDLE hMeshTemplate)'
        source=source.replace(marker,
            'void SolarSail::GlobalCleanup()\n{\n'
            '\tfor (int i = 0; i < 4; i++) {\n\t\tdelete []sail_idx[i];\n\t\tsail_idx[i] = NULL;\n\t}\n'
            '\tdelete []nbhr; nbhr = NULL;\n\tdelete []sail_vbuf; sail_vbuf = NULL;\n'
            '\tdelete []sail_nml; sail_nml = NULL;\n\tdelete []sail_nsd; sail_nsd = NULL;\n'
            '\tsail_nvtx = sail_ntri = 0;\n\thMeshTpl = NULL;\n}\n\n'+marker)
        source=source.replace('oapi::UInt32 SolarSail::sail_ntri = 0;',
            'oapi::UInt32 SolarSail::sail_ntri = 0;\n'
            'VECTOR3 *SolarSail::sail_nml = NULL;\noapi::UInt32 *SolarSail::sail_nsd = NULL;')
        original_cleanup='\tfor (int i = 0; i < 4; i++) {\n\t\tdelete []SolarSail::sail_idx[i];\n\t}'
        if source.count(original_cleanup)!=1:raise ValueError('Original solar-sail index cleanup changed')
        source=source.replace(original_cleanup,'\tSolarSail::GlobalCleanup();')
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
          ' unchanged resources/install rules; original physical/animation/deformation/Lua operations retained with declared rotor and shared scratch-cache cleanup')


if __name__=='__main__':verify()
