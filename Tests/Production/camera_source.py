#!/usr/bin/env python3
"""Conserve original camera calculations and exact Windows SDK declarations."""
from pathlib import Path
import re,subprocess
from vessel_runtime_source import equal,span
ROOT=Path(__file__).resolve().parents[2]
PRIOR='cbcafe04'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def raw(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
def windows(text):
    output=[];stack=[];active=True
    for line in text.splitlines(True):
        stripped=line.strip()
        if re.match(r'#\s*(ifdef|ifndef|if)\b',stripped):
            controlled=stripped in ('#ifdef _WIN32','#ifndef _WIN32')
            stack.append((active,controlled,stripped=='#ifdef _WIN32'))
            if controlled:active=active and stack[-1][2]
            elif active:output.append(line)
        elif stripped.startswith('#else') and stack:
            parent,controlled,positive=stack[-1]
            if controlled:active=parent and not positive
            elif active:output.append(line)
        elif stripped.startswith('#endif') and stack:
            parent,controlled,positive=stack.pop()
            if not controlled and active:output.append(line)
            active=parent
        elif active:output.append(line)
    return ''.join(output)
def sdk_blocks(source):
    a=source.index('class OAPIFUNC CameraMode {');b=source.index('// ======================================================================',source.index('class OAPIFUNC CameraMode_Ground',a))
    c=source.index('#define COCKPIT_GENERIC');d=source.index('// time propagation modes',c)
    return a,b,c,d
def restore_api(actual):
    if (b'OrbiterCockpitData.h' in actual if isinstance(actual,bytes) else 'OrbiterCockpitData.h' in actual):
        from cockpit_values_source import restore_api as restore_cockpit
        actual=restore_cockpit(actual)
    source=old('Orbitersdk/include/OrbiterAPI.h');a,b,c,d=sdk_blocks(source)
    header=raw('Orbitersdk/include/OrbiterCameraData.h')
    body=header[header.index('#define COCKPIT_GENERIC'):header.rindex('#endif')]
    equal(source[c:d]+source[a:b],body,'Original camera SDK modes and constants')
    expected=source[:a]+'#include "OrbiterCameraData.h"\n\n'+source[b:]
    expected=expected.replace(source[c:d],'',1)
    text=(actual.decode('cp1252') if isinstance(actual,bytes) else actual).replace('\r\n','\n')
    if expected!=text:raise ValueError('Camera SDK extraction changed other Windows API bytes')
    return source.encode('cp1252') if isinstance(actual,bytes) else source

def verify():
    gui=('Camera::ProcessMouse','Camera::UpdateMouse','Camera::Direction2Viewport','Camera::D3D_ProjViewMatrix','Camera::UpdateProjectionMatrix')
    original=old('Src/Orbiter/Camera.cpp');core=original[original.index('static Vector nullvec;'):];moved=[]
    for name in gui:
        a,b=span(core,name);moved.append(core[a:b]);core=core[:a]+core[b:]
    adapter=raw('Src/Orbiter/CameraApplication.cpp');a,b=span(adapter,gui[0]);equal('\n'.join(moved),adapter[a:],'Original Windows camera mouse and Direct3D adapter')
    for a,b in [('g_pOrbiter->Cfg()->','GetCameraServices().Configuration().'),('g_psys','GetRigidBodyServices().World()'),('g_focusobj','GetCameraServices().Focus()'),('td.','GetRigidBodyServices().Time().'),('g_pOrbiter->SetFocusObject','GetCameraServices().SetFocus'),('g_pOrbiter->SetFOV','GetCameraServices().SetFOV'),('g_pOrbiter->ScnPath','GetCameraServices().ScenarioPath'),('g_pane->','GetCameraServices().'),('TRACENEW','GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);'),('_strnicmp','ComparePrefix'),('_stricmp','CompareText'),('strnicmp','ComparePrefix'),('normangle (','NormalizeCameraAngle ('),('DWORD','oapi::UInt32')]:core=core.replace(a,b)
    core=core.replace('\tVObject **vobj, *vo;\n\tconst Body *bd;\n\tint i, nobj;','\tint i;\n\tVObject **vobj, *vo;\n\tconst Body *bd;\n\tint nobj;')
    actual=windows(raw('Src/Orbiter/Camera.cpp'));actual=actual[actual.index('static Vector nullvec;'):]
    # ASan/UBSan found the original constructor reading external_view before
    # assignment. Initial setters must also receive an initialized old matrix.
    actual=actual.replace('\t// Setters below read this mode before the first scenario/camera attachment.\n\texternal_view = true;\n\trrot0.Set (1,0,0, 0,1,0, 0,0,1);\n','',1)
    actual=actual.replace('\tnpreset = 0;\n','\tnpreset = 0;\n\texternal_view = true;//false;\n',1)
    equal(core,actual,'All production camera/ground observer/preset calculations and ordering')
    api=old('Orbitersdk/include/OrbiterAPI.h');a,b=span(api,'normangle');helper=raw('Src/Orbiter/Camera.cpp');c,d=span(helper,'NormalizeCameraAngle')
    equal(api[a:b].replace('inline double normangle','static double NormalizeCameraAngle'),helper[c:d],'Original signed angle normalization')
    for path in ('Src/Orbiter/Camera.h','Orbitersdk/include/CamAPI.h'):
        current=windows(raw(path)).replace('oapi::UInt32','DWORD')
        equal(old(path),current,'Exact Windows camera field types and API declarations: '+path)
    path='Src/Orbiter/CamAPI.cpp';source=old(path);a=source.index('ExternalCameraControl::ExternalCameraControl');b=source.index('// ======================================================================\n// External control registration',a)
    equal(source[:a]+source[b:],raw(path),'Windows external camera registration')
    moved=raw('Src/Orbiter/CameraControl.cpp');moved=moved[moved.index('ExternalCameraControl::ExternalCameraControl'):].replace('oapi::UInt32','DWORD')
    equal(source[a:b],moved,'Original external camera control state')
    content=(ROOT/'Orbitersdk/include/OrbiterAPI.h').read_bytes().replace(b'\r\n',b'\n')
    assert restore_api(content)==restore_api(content.replace(b'\n',b'\r\n')), 'Windows checkout line endings changed the SDK audit'
    print('Original production camera calculations, Windows input/projection adapters and SDK modes conserved')
if __name__=='__main__':verify()
