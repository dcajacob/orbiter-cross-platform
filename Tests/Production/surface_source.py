#!/usr/bin/env python3
"""Conserve original production planet/base calculations across service extraction."""
import difflib
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='db1b9d43'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def now(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
def canonical(s):
    from random_source import canonical as random_bindings
    s=random_bindings(s)
    s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
    s=re.sub(r'if \(GetMeshServices\(\).allocation\) GetMeshServices\(\).allocation\(GetMeshServices\(\).context,__FILE__,__LINE__\);','',s)
    s=s.replace('GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','').replace('TRACENEW','').replace('TraceSurfaceAllocation(__FILE__,__LINE__);','')
    for a,b in [('SurfaceScalar','D3DVALUE'),('SurfaceVector','D3DVECTOR'),('SurfacePoint2','VECTOR2D'),('SurfacePoint','VERTEX_XYZ'),('SurfaceTextureVertex','POSTEXVERTEX'),('SurfaceMaterial','D3DMATERIAL7'),('SurfaceName','LONGLONG'),('UInt32','DWORD'),('UInt16','WORD'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),('NavigationText','_snprintf'),('SurfacePositiveAngle','posangle')]:
        s=re.sub(r'\b'+a+r'\b',b,s)
    s=s.replace('orbiter::production::','')
    s=s.replace('CelestialClock().','td.').replace('GetSurfaceServices().Configuration().','g_pOrbiter->Cfg()->').replace('GetSurfaceServices().CameraAperture()','g_camera->Aperture()').replace('GetSurfaceServices().CameraPosition()','g_camera->GPos()').replace('GetSurfaceServices().CameraDirection()','g_camera->Direction()')
    s=s.replace('GetSurfaceServices().DeallocationProgress()','g_pOrbiter->UpdateDeallocationProgress()')
    return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',s)
def method(s,name):
    # Extract whole methods, then compare tokens including literal values and
    # expression order. Braces here are code braces; comments are removed first.
    s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
    start=s.index(name+' (');start=s.index('{',start);end=start+1;depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[start:end]
def equal(a,b,label):
    x,y=canonical(a),canonical(b)
    if x!=y:
        delta='\n'.join('old: '+' '.join(x[max(0,i-5):j+5])+'\nnew: '+' '.join(y[max(0,k-5):l+5]) for op,i,j,k,l in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if op!='equal')
        raise ValueError(label+' changed beyond declared platform adapters:\n'+delta[:3000])
def verify():
    for name in ('Planet::GetParam','Planet::ElToEcliptic','Planet::GroundVelocity','Planet::WindVelocity','Planet::Update','Planet::BeginStateUpdate','Planet::EndStateUpdate'):
        equal(method(old('Src/Orbiter/Planet.cpp'),name),method(now('Src/Orbiter/Planet.cpp'),name),name)
    # All base-object geometry, transforms, dynamics and legacy Windows drawing
    # remain the original implementation. Only host/type/diagnostic calls leave.
    a=old('Src/Orbiter/Baseobj.cpp');b=now('Src/Orbiter/Baseobj.cpp')
    a=a[a.index('BaseObject::BaseObject'):];b=b[b.index('BaseObject::BaseObject'):]
    a=re.sub(r'^#[^\n]*','',a,flags=re.M)
    b=re.sub(r'^#[^\n]*','',b,flags=re.M)
    b=b.replace('SurfaceScalar(r - sqrt (r2+d2))','D3DVAL(r - sqrt (r2+d2))').replace('SurfaceScalar(std::hypot (dx, dz))','D3DVAL(std::hypot (dx, dz))').replace('SurfaceScalar(j)/SurfaceScalar(rwseg[i].subseg)','D3DVAL(j)/D3DVAL(rwseg[i].subseg)')
    a=a.replace('LOGOUT ("BaseObject: Parse error");','').replace('LOGOUT ("BaseObject: Parse error %d", err);','').replace('LOGOUT_ERR(errmsg);','')
    b=b.replace('GetSurfaceServices().Log("BaseObject: Parse error");','').replace('GetSurfaceServices().Log("BaseObject: Parse error "+std::to_string(err));','').replace('GetSurfaceServices().Log(errmsg);','')
    b=b.replace('fname = static_cast<char*>(std::malloc(std::strlen(value)+1));\n\t\tif (!fname) throw std::bad_alloc();\n\t\tstd::strcpy(fname,value);','fname = _strdup (value);')
    for line in ('\tD3DCOLOR shcol = D3DRGBA(0,0,0,0.3);\n','\t\tD3DCOLOR shcol = D3DRGBA(shadowCol.x, shadowCol.y, shadowCol.z, shadowCol.w);\n'):
        a=a.replace(line,'') # unused colors; their only consumers were commented out
    equal(a,b,'Complete production base-object geometry/dynamics')
    vessel=now('Src/Orbiter/Vesselbase.cpp')
    # A complete stock DG-S AAP launch exposed an indeterminate bool190 here.
    # Define only its initial unchecked state; retain every contact calculation,
    # propagator choice and state-update order from the original implementation.
    from random_source import restore_contact_speed_check_default
    vessel=restore_contact_speed_check_default(vessel)
    equal(old('Src/Orbiter/Vesselbase.cpp').split('// =======================================================================',1)[1],vessel.split('// =======================================================================',1)[1].replace('GetRigidBodyServices().World()->','g_psys->'),'Original vessel surface/contact implementation with defined initial collision-speed flag')
    for name in ('Base::Setup','Base::Attach','Base::Update','Base::Rel_EquPos','Base::Pad_EquPos','Base::CosSunAlt','Base::ExportBaseStructures','Base::ExportShadowGeometry','Base::ExportCollisionMeshes'):
        equal(method(old('Src/Orbiter/Base.cpp'),name),method(now('Src/Orbiter/Base.cpp'),name),name)
    a=old('Src/Orbiter/Astro.cpp');start=a.index('void Orthodome (');end=a.index('static char strbuf',start)
    if a[start:end].rstrip() not in now('Src/Orbiter/Production/SurfaceNavigation.cpp'):
        raise ValueError('Original orthodome implementation changed')
    a=old('Src/Orbiter/Util.cpp');start=a.index('LONGLONG NameToId');end=a.index('double rand1()',start)
    equal(a[start:end],now('Src/Orbiter/Production/SurfaceNames.cpp').split('#include <cctype>',1)[1],'Original texture name IDs')
    print('Original planet forces/wind/updates and complete base geometry/dynamics conserved')
if __name__=='__main__':verify()
