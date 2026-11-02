#!/usr/bin/env python3
"""Conserve the complete 311a4c31 vessel implementation across native SDK services.

This is a second conservation stage. Only after each current implementation is
verified may the first-stage audit inspect its immutable 311a4c31 predecessor.
No state reference, input profile or numerical budget is updated here.
"""
from pathlib import Path
import functools
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='311a4c31'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def raw(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
def tokens(s):
    s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
    return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',s)
def equal(a,b,label):
    if tokens(a)!=tokens(b):
        import difflib
        x,y=tokens(a),tokens(b)
        changes=['old: '+' '.join(x[max(0,i-4):j+4])+'\nnew: '+' '.join(y[max(0,k-4):l+4]) for op,i,j,k,l in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if op!='equal']
        raise ValueError(label+' changed beyond declared services:\n'+'\n'.join(changes)[:2400])
def aliases(s):
    for a,b in [('oapi::UInt32','DWORD'),('oapi::UInt16','WORD'),('oapi::UInt','UINT'),('std::uintptr_t','DWORD_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkRectangle','RECT')]:s=s.replace(a,b)
    return s
def clock_adapters(s):
    clock='GetRigidBodyServices().Time().'
    s=s.replace('new Elements('+clock+'MJD_ref);','new Elements;')
    s=s.replace('Elements els('+clock+'MJD_ref);','Elements els;')
    for prefix in ['el->Set (a, e, i*RAD, theta*RAD, omegab*RAD, L*RAD, elmjd',
                   'els.Set (el.a, el.e, el.i, el.theta, el.omegab, el.L, mjd_ref',
                   'els.Setup (0, ref->Mass(), mjd_ref',
                   'el->Setup (mass, cbody->Mass(), el->MJDepoch()']:
        s=s.replace(prefix+', '+clock+'MJD_ref);',prefix+');')
    for prefix in ['el->Update (rpos, rvel','els.Update (p, v']:
        s=s.replace(prefix+', '+clock+'SimT1);',prefix+');')
    s=s.replace('mjd_ref ? mjd_ref : '+clock+'MJD0, '+clock+'MJD_ref);','mjd_ref ? mjd_ref : '+clock+'MJD0);')
    return s

def span(s,qualified):
    m=re.search(r'^[^\n]*\b'+re.escape(qualified)+r'\s*\(',s,re.M)
    if m is None:return None
    first=s.index('{',m.start());depth=0
    lexer=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for token in lexer.finditer(s,first):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if not depth:return m.start(),token.end()
    raise ValueError('Unclosed method '+qualified)
GUI=('VESSEL::SetCameraDefaultDirection','VESSEL::SetCameraCatchAngle','VESSEL::TriggerPanelRedrawArea',
     'VESSEL::TriggerRedrawArea','VESSEL::GetDevMesh','VESSEL2::clbkDrawHUD','VESSEL3::SetPanelBackground',
     'VESSEL3::SetPanelScaling','VESSEL3::RegisterPanelMFDGeometry','VESSEL3::RegisterPanelArea',
     'VESSEL3::clbkDrawHUD','VESSEL3::clbkRenderHUD','VESSEL4::RegisterPanelArea')
LIGHTS=('AddPointLight','AddSpotLight','DelLightEmitter','ClearLightEmitters','LightEmitterState','ShiftLightEmitters')

@functools.lru_cache(maxsize=1)
def previous_files():
    from random_source import canonical as random_bindings
    result={}
    for name in ['Vessel.cpp','Vesselstatus.cpp','SuperVessel.cpp']:
        path='Src/Orbiter/'+name
        current=clock_adapters(random_bindings(raw(path)).replace('#include "Production/Random.h"\n',''))
        if name=='Vessel.cpp':
            # Sanitizer-confirmed upstream array-delete mismatch; no numerical change.
            assert current.count('delete []A->comp;')==2
            current=current.replace('\t\tdelete []A->comp;','\t\tdelete A->comp;',1)
            # Bulk exhaust cleanup must free owned constant fields like DelExhaust.
            current=current.replace('\t\tfor (i = 0; i < nexhaust; i++) {\n\t\t\tif (exhaust[i]->level && (exhaust[i]->flags & EXHAUST_CONSTANTLEVEL))\n\t\t\t\tdelete exhaust[i]->level;\n\t\t\tif (exhaust[i]->lpos && (exhaust[i]->flags & EXHAUST_CONSTANTPOS))\n\t\t\t\tdelete exhaust[i]->lpos;\n\t\t\tif (exhaust[i]->ldir && (exhaust[i]->flags & EXHAUST_CONSTANTDIR))\n\t\t\t\tdelete exhaust[i]->ldir;\n\t\t\tdelete exhaust[i];\n\t\t}', '\t\tfor (i = 0; i < nexhaust; i++)\n\t\t\tdelete exhaust[i];')
        equal(old(path),current,path);result[path]=old(path)
    path='Src/Orbiter/Vessel.h'
    s=raw(path).replace('#ifndef _WIN32\n\tstatic void ReleaseNativeInterface(VESSEL* interface);\n#endif\n','')
    equal(old(path),s,path);result[path]=old(path)
    # Retain every SDK wrapper. Platform-specific cockpit methods move intact;
    # the numerical and vessel-delegation methods remain one shared source.
    path='Src/Orbiter/VesselSdk.cpp';s=old(path);start=s.index('VESSEL::VESSEL (');original=s[start:];common=original;gui=[]
    for name in GUI:
        while (part:=span(common,name)) is not None:
            a,b=part;gui.append(common[a:b]);common=common[:a]+common[b:]
    current=raw(path);current=current[current.index('VESSEL::VESSEL ('):]
    current=clock_adapters(aliases(current))
    for a,b in [('GetRigidBodyServices().World()','g_psys'),('GetRigidBodyServices().Time().','td.'),
                ('GetSurfaceServices().Configuration().','g_pOrbiter->Cfg()->'),
                ('GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','TRACENEW'),
                ('GetVesselServices().InsertVessel (vessel)','g_pOrbiter->InsertVessel (vessel)'),
                ('GetVesselServices().ManualControl (thgt, device)','g_pOrbiter->ManCtrlLevel (thgt, device)'),
                ('GetVesselServices().NotifyJump (*vessel, gdr)','g_pOrbiter->NotifyObjectJump (vessel, gdr)'),
                ('GetVesselServices().ShiftCockpit (*vessel, vs);','if ((g_pane) && (g_focusobj == vessel)) g_pane->ShiftVC (vs);')]:current=current.replace(a,b)
    current=re.sub(r'GetVesselServices\(\).Check\(bool\((.*?)\), ("[^"\n]*")\);',r'dCHECK(\1, \2)',current)
    equal(common,current,'Complete production SDK vessel calculations/delegates')
    application=raw('Src/Orbiter/VesselSdkApplication.cpp')
    first=span(application,GUI[0]);equal('\n\n'.join(gui),application[first[0]:],'Original Windows cockpit SDK methods')
    result[path]=old(path)
    # Logical light objects and their vessel ownership remain CPU-side original
    # implementations. The graphics client owns only its GPU counterparts.
    path='Src/Orbiter/VesselApplication.cpp';s=old(path);lights=[]
    for name in LIGHTS:
        a,b=span(s,'Vessel::'+name);lights.append(s[a:b]);s=s[:a]+s[b:]
    equal(s,raw(path),path);result[path]=old(path)
    light=raw('Src/Orbiter/VesselLights.cpp');a,b=span(light,'Vessel::'+LIGHTS[0])
    equal('\n\n'.join(lights),aliases(light[a:]),'Original vessel light ownership/events')
    path='Src/Orbiter/LightEmitter.cpp';s=raw(path).replace('#ifdef _WIN32\n#define OAPI_IMPLEMENTATION\n#include "OrbiterAPI.h"\n#else\n#include "NativeVesselAPI.h"\n#endif','#define OAPI_IMPLEMENTATION\n#include "OrbiterAPI.h"')
    equal(old(path),s,path);result[path]=old(path)
    path='Src/Orbiter/OrbiterAPI.cpp';s=old(path);a=s.index('DLLEXPORT double oapiGetInducedDrag');b=s.index('// ===========================================================================',a)
    math=raw('Src/Orbiter/VesselFlightMath.cpp');math=math[math.index('ORBITER_FLIGHT_EXPORT double oapiGetInducedDrag'):].replace('ORBITER_FLIGHT_EXPORT double','DLLEXPORT double')
    equal(s[a:b],math,'Original aerodynamic helper formulas');equal(s[:a]+s[b:],raw(path),path);result[path]=old(path)
    # Preserve stock module capabilities, force-coefficient tables and animation
    # associations. Only exact Windows scalar aliases and its native entry differ.
    path='Src/Vessel/ShuttlePB/ShuttlePB.cpp';s=aliases(raw(path))
    s=s.replace('#ifdef ORBITER_NATIVE_MODULE\n#include "NativeVesselAPI.h"\n#define DLLCLBK static\n#else\n#include "orbitersdk.h"\n#endif','#include "orbitersdk.h"')
    s=s.replace('\n#ifdef ORBITER_NATIVE_MODULE\n#include "NativeShuttlePBFactory.inc"\n#endif','')
    equal(old(path),s,path);result[path]=old(path)
    verify_recorder(result)
    print('Complete stock vessel SDK, lights, recorder and ShuttlePB formulas conserved through native services')
    return result

def verify_recorder(result):
    path='Src/Orbiter/FlightRecorder.cpp';s=old(path)
    a=s.index('const double max_step');b=s.index('// ================================================================\n// System event recording/playback',a)
    helper=s.index('// convert Euler angles from given reference frame to quaternion')
    expected=s[:a]+'#include "Production/VesselRecorderState.h"\n\n'+s[b:helper]
    equal(expected,raw(path),'Original Windows system recorder');result[path]=old(path)
    original=s[a:b];actual=raw('Src/Orbiter/VesselRecorder.cpp');actual=actual[actual.index('const double max_step'):]
    helper_body=s[s.index('void Euler2Quaternion (double *a, Quaternion &q, int frm)\n{'):]
    original+='\n'+helper_body
    actual=aliases(actual).replace('double Tofs =','static double Tofs =',1).replace('double MJDofs =','static double MJDofs =',1)
    for before,after in [('GetSurfaceServices().Configuration().','g_pOrbiter->Cfg()->'),('GetRigidBodyServices().Time().','td.'),
        ('GetRigidBodyServices().World()','g_psys'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),
        ('GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','TRACENEW'),
        ('GetVesselServices().PlaybackWarp (RecordingSpeed, WarpDelay)','g_pOrbiter->SetWarpFactor (RecordingSpeed, true, WarpDelay)'),
        ('GetVesselServices().RecallCameraPreset (i)','g_camera->RecallPreset (i)'),
        ('GetVesselServices().EndPlayback()','g_pOrbiter->EndPlayback()'),
        ('GetVesselServices().Check(s1 != nullptr, "Update state not available.");','dCHECK(s1, "Update state not available.")')]:actual=actual.replace(before,after)
    for name in ['FRfname','cbuf','fname']:
        for writing in ['true','false']:
            actual=actual.replace('GetVesselServices().RecorderFile('+name+','+writing+')',name)
    begin=original.index('\t\t\t\toapi::ScreenAnnotation *sa = ');end=original.index('\n\t\t\t} else if (modIntf.v->Version()',begin)
    note=original[begin:end]
    actual=actual.replace('\t\t\t\tGetVesselServices().PlaybackNote(s);',note)
    equal(original,actual,'Complete original vessel recording/playback/interpolation')
    # The only removed drawing operations are preserved in the Windows adapter.
    adapter=raw('Src/Orbiter/Production/WindowsVesselServices.cpp')
    if note.strip() not in adapter:raise ValueError('Original playback note operations are missing from Windows adapter')

if __name__=='__main__':previous_files()
