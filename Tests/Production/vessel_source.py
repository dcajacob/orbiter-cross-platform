#!/usr/bin/env python3
"""Conserve actual production vessel state/assembly code during host separation."""
from pathlib import Path
import re
import subprocess
from surface_source import equal
ROOT=Path(__file__).resolve().parents[2]
PRIOR='0e794eb0'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def now(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
def scalars(source):
    for a,b in [('oapi::UInt32','DWORD'),('oapi::UInt16','WORD'),('oapi::UInt','UINT'),('std::uintptr_t','DWORD_PTR'),('std::uint8_t','BYTE')]:source=source.replace(a,b)
    return source
def restore_header(source):
    source=source.replace('#include "Production/VesselServices.h"\n','')
    source=source.replace('#ifdef _WIN32\n#include "GraphicsAPI.h"\n#include "Log.h"\n#else\n#include "NativeVesselAPI.h"\n#include <stdexcept>\nnamespace oapi {class ParticleStream;}\nstruct ENGINESTATUS;\n#endif','#include "GraphicsAPI.h"\n#include "Log.h"')
    source=source.replace('namespace oapi {class Sketchpad;}','class oapi::Sketchpad;')
    source=source.replace('} orbital;','};').replace('} landed;','};')
    source=source.replace('orbiter::production::GetVesselServices().Check(tgs != nullptr, "Zero ThrustGroupSpec pointer not permitted.");','dCHECK(tgs, "Zero ThrustGroupSpec pointer not permitted.")')
    source=source.replace('#ifdef _WIN32\n\tHINSTANCE hMod;\n#else\n\tvoid* hMod;\n#endif\n\t// Module handle; native ownership is provided by the checked module loader.','\tHINSTANCE hMod;        // module handle')
    source=re.sub(r'#ifdef _WIN32\n\tfriend OAPIFUNC ([^\n]+)\n#else\n\tfriend \1\n#endif',r'\tfriend OAPIFUNC \1',source)
    return scalars(source)
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
    if a[:start]+'#include "Production/GeometryConversions.h"\n\n'+a[end:]!=now(name):raise ValueError('Utility header changed beyond verbatim conversions extraction')
    print('Actual vessel state parsing, persistence, composite dynamics and private storage conserved through platform services')
if __name__=='__main__':verify()
