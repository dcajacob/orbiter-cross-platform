#!/usr/bin/env python3
"""Conserve actual production vessel state/assembly code during host separation."""
from pathlib import Path
import re
import subprocess
from surface_source import equal
ROOT=Path(__file__).resolve().parents[2]
PRIOR='0e794eb0'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def now(name):
    source=(ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
    if (ROOT/'Src/Orbiter/VesselSdkApplication.cpp').exists():
        from vessel_runtime_source import previous_files
        source=previous_files().get(name,source)
    return source
def scalars(source):
    for a,b in [('oapi::UInt32','DWORD'),('oapi::UInt16','WORD'),('oapi::UInt','UINT'),('std::uintptr_t','DWORD_PTR'),('std::uint8_t','BYTE')]:source=source.replace(a,b)
    return source
def restore_header(source):
    source=source.replace('#ifndef _WIN32\n\tstatic void ReleaseNativeInterface(VESSEL* interface);\n#endif\n','')
    source=source.replace('#include "Production/VesselServices.h"\n','')
    source=source.replace('#ifdef _WIN32\n#include "GraphicsAPI.h"\n#include "Log.h"\n#else\n#include "NativeVesselAPI.h"\n#include <stdexcept>\nnamespace oapi {class ParticleStream;}\n#endif','#include "GraphicsAPI.h"\n#include "Log.h"')
    source=source.replace('namespace oapi {class Sketchpad;}','class oapi::Sketchpad;')
    source=source.replace('} orbital;','};').replace('} landed;','};')
    source=source.replace('orbiter::production::GetVesselServices().Check(tgs != nullptr, "Zero ThrustGroupSpec pointer not permitted.");','dCHECK(tgs, "Zero ThrustGroupSpec pointer not permitted.")')
    source=source.replace('#ifdef _WIN32\n\tHINSTANCE hMod;\n#else\n\tvoid* hMod;\n#endif\n\t// Module handle; native ownership is provided by the checked module loader.','\tHINSTANCE hMod;        // module handle')
    source=re.sub(r'#ifdef _WIN32\n\tfriend OAPIFUNC ([^\n]+)\n#else\n\tfriend \1\n#endif',r'\tfriend OAPIFUNC \1',source)
    return scalars(source)

APPLICATION_METHODS=('ConsumeBufferedKey','DrawHUD','RenderHUD','RegisterMFDMode','UnregisterMFDMode','UnregisterMFDModes','LoadPanel2D','LeanCamera','LoadModule','RegisterModule','ClearModule','AddParticleStream','AddExhaustStream','DelExhaustStream','AddReentryStream','DelReentryStream','ClearReentryStreams','ClearExhaustStreamDefinitions','AddPointLight','AddSpotLight','DelLightEmitter','ClearLightEmitters','LightEmitterState','ShiftLightEmitters')
def function_span(source,name):
    match=re.search(r'^[^\n]*\bVessel::'+name+r'\s*\(',source,re.M)
    if match is None:raise ValueError('Missing original vessel method '+name)
    start=source.index('{',match.start());depth=0
    tokens=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for token in tokens.finditer(source,start):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if not depth:return match.start(),token.end()
    raise ValueError('Unclosed original vessel method '+name)
def verify_dynamics():
    a=old('Src/Orbiter/Vessel.cpp');b=now('Src/Orbiter/Vessel.cpp')
    if not (ROOT/'Src/Orbiter/VesselSdk.cpp').exists():return
    start=a.index('VESSEL::VESSEL (');sdk=a[start:];a=a[:start]
    actual=now('Src/Orbiter/VesselSdk.cpp');actual=actual[actual.index('VESSEL::VESSEL ('):]
    if '\n'.join(line.rstrip() for line in sdk.splitlines()).rstrip()!='\n'.join(line.rstrip() for line in actual.splitlines()).rstrip():raise ValueError('Original Windows SDK vessel implementations changed during split')
    application='\n'.join(line.rstrip() for line in now('Src/Orbiter/VesselApplication.cpp').splitlines())
    for name in APPLICATION_METHODS:
        start,end=function_span(a,name)
        if '\n'.join(line.rstrip() for line in a[start:end].splitlines()).rstrip() not in application:raise ValueError('Original Windows application vessel method changed: '+name)
        a=a[:start]+a[end:]
    start=a.index('struct UndockSpec {');end=a.index('void Vessel::RelDockingPos',start)
    if '\n'.join(line.rstrip() for line in a[start:end].splitlines()).rstrip() not in application:raise ValueError('Original undocking dialogs changed')
    a=a[:start]+a[end:]
    a=a[a.index('const double KEYDELAY'):];b=b[b.index('const double KEYDELAY'):]
    exhaust='static VECTOR3 DefExhaustDir[4] = {{0,0,-1}, {0,0,1}, {0,-1,0}, {0,0,-1}};\n'
    if exhaust not in now('Src/Orbiter/VesselSdk.cpp'):raise ValueError('Legacy exhaust directions changed')
    a=a.replace(exhaust,'')
    b=scalars(b).replace('GetRigidBodyServices().World()','g_psys').replace('GetRigidBodyServices().Time().','td.')
    substitutions=[
        ('GetVesselServices().ConfigFile (','g_pOrbiter->ConfigPath ('),('GetVesselServices().ConfigFile(','g_pOrbiter->ConfigPath('),
        ('GetVesselServices().Fatal("Vessel initialization failed")','g_pOrbiter->TerminateOnError()'),
        ('GetBodyServices().LoadStatus (','g_pOrbiter->OutputLoadStatus ('),
        ('GetVesselServices().Meshes().','g_pOrbiter->meshmanager.'),
        ('GetVesselServices().PlaybackDirectory()','g_pOrbiter->PState()->PlaybackDir()'),
        ('GetVesselServices().SetWarpFactor(','g_pOrbiter->SetWarpFactor('),
        ('GetVesselServices().TimejumpDelta()','g_pOrbiter->tjump.dt'),
        ('GetVesselServices().RedrawCockpitAreas (PANEL_REDRAW_INIT)','g_pane->RedrawCockpitAreas (PANEL_REDRAW_INIT)'),
        ('GetVesselServices().ManualControl (','g_pOrbiter->ManCtrlLevel ('),
        ('GetBodyServices().IsUpdating()','g_bStateUpdate'),
        ('GetVesselServices().Focus()','g_focusobj'),
        ('GetVesselServices().ParticleLevel(contrail[i])','contrail[i]->Level()'),
        ('((Mesh*)hMesh)->nGroup()','oapiMeshGroupCount(hMesh)'),
        ('GroupSpec *grp = ((Mesh*)hMesh)->GetGroup(g)','MESHGROUPEX *grp = oapiMeshGroupEx(hMesh, g)'),
        ('td.MJD_ref, td.MJD_ref);','td.MJD_ref);')]
    for before,after in substitutions:b=b.replace(before,after)
    b=re.sub(r'GetVesselServices\(\).Check\(bool\((.*?)\), ("[^"\n]*")\);',r'dCHECK(\1, \2)',b)
    a=re.sub(r'\bdCHECK\(([^\n]*)\);',r'dCHECK(\1)',a)
    b=re.sub(r'\bdCHECK\(([^\n]*)\);',r'dCHECK(\1)',b)
    # Diagnostic formatting is routed to the host; it does not enter dynamics.
    a=a.replace('LOGOUT_ERR_FILENOTFOUND_MSG(g_pOrbiter->ConfigPath(cbuf + 8), "No vessel class configuration file found for: %s", classname ? classname : name);','')
    b=b.replace('VesselLog("No vessel class configuration file found for: %s", classname ? classname : name.c_str());','')
    a=a.replace('oapiWriteLogV','VesselLog').replace('LOGOUT_ERR (','VesselLog (')
    equal(a,b,'Complete actual Vessel dynamics, capabilities, lifecycle and callback ordering')
def verify():
    name='Src/Orbiter/Vessel.h'
    if restore_header(now(name))!=old(name):raise ValueError('Private vessel declaration/layout changed beyond named packed-state members and exact platform aliases')
    name='Src/Orbiter/SuperVessel.h'
    if scalars(now(name))!=old(name):raise ValueError('Composite vessel layout changed')
    for name,start in [('Src/Orbiter/Vesselstatus.cpp','bool Vessel::ParseScenarioLine ('),('Src/Orbiter/SuperVessel.cpp','SuperVessel::SuperVessel (')]:
        a=old(name);b=now(name);a=a[a.index(start):];b=b[b.index(start):]
        b=scalars(b).replace('GetRigidBodyServices().World()','g_psys').replace('GetRigidBodyServices().Time().','td.')
        b=b.replace('td.MJD_ref, td.MJD_ref);','td.MJD_ref);')
        b=b.replace('GetVesselServices().Fatal(cerr);','LOGOUT_ERR(cerr);\n\t\t\t\tg_pOrbiter->TerminateOnError();')
        b=b.replace('GetVesselServices().ConfigFile(line,false)','g_pOrbiter->Cfg()->ConfigPathNoext (line)')
        b=b.replace('GetVesselServices().Check(!GetBodyServices().IsUpdating(),','dCHECK(!g_bStateUpdate,')
        b=b.replace('GetVesselServices().Check(hrot != nullptr,','dCHECK(hrot,')
        b=re.sub(r'(dCHECK\([^\n]+\));',r'\1',b)
        b=b.replace('sd->orbital.','sd->').replace('sd->landed.','sd->')
        equal(a,b,'Complete original '+name)
    name='Src/Orbiter/Util.h';a=old(name);start=a.index('// conversion between Vector and VECTOR3 structures');end=a.index('double rand1();',start)
    if a[start:end].rstrip() not in now('Src/Orbiter/Production/GeometryConversions.h'):raise ValueError('Geometry conversion formulas changed')
    expected=a[:start]+'#include "Production/GeometryConversions.h"\n\n'+a[end:]
    expected=expected.replace('double rand1();','#include "Production/Random.h"')
    if expected!=now(name):raise ValueError('Utility header changed beyond verbatim conversions/random extraction')
    a=old('Src/Orbiter/Util.cpp');start=a.index('double rand1()');end=a.index('bool MakePath',start)
    from random_source import canonical as random_bindings
    if a[start:end].rstrip() not in random_bindings(now('Src/Orbiter/Production/Random.cpp')) or a[:start]+a[end:]!=now('Src/Orbiter/Util.cpp'):
        raise ValueError('Original random-number calculation changed')
    verify_dynamics()
    print('Actual vessel state parsing, persistence, composite dynamics and private storage conserved through platform services')
if __name__=='__main__':verify()
