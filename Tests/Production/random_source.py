#!/usr/bin/env python3
"""Prove RNG extraction changes names/bindings, never numerical formulas/order."""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BEFORE='9aefc8d6'
FILES=('Vecmat.cpp','Rigidbody.cpp','Vesselbase.cpp','Vessel.cpp','SuperVessel.cpp','Planet.cpp','Base.cpp','Baseobj.cpp')

def canonical(source):
    return source.replace('orbiter::production::RandomInteger()','rand()').replace('orbiter::production::RandomMaximum','RAND_MAX')

def restore_cloud_microtexture_default(source):
    # The file-based constructor omitted the false default already present in
    # the numerical constructor. Accept exactly that initialization repair;
    # compare every remaining byte, including configuration enabling logic.
    original='Planet::Planet (char *fname)\n: CelestialBody (fname)\n{\n\tint i, n;\n\tdouble d;\n\tchar cbuf[256], *pc;\n'
    repaired=original+'\tbCloudMicrotex = false;\n'
    if source.count(repaired)!=1:
        raise ValueError('Declared planet cloud-microtexture default differs')
    return source.replace(repaired,original)

def verify():
    include='#include "Production/Random.h"\n'
    for name in FILES:
        path='Src/Orbiter/'+name
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BEFORE+':'+path]).replace(b'\r\n',b'\n').decode('cp1252')
        if name=='Vessel.cpp':
            from vessel_runtime_source import with_sparse_mesh_slots
            original=with_sparse_mesh_slots(original)
        actual=(ROOT/path).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
        if name=='Vessel.cpp':
            from vessel_runtime_source import restore_hull_transform_cleanup,restore_startup_cleanup
            actual=restore_startup_cleanup(restore_hull_transform_cleanup(actual))
        if name=='Planet.cpp':
            actual=restore_cloud_microtexture_default(actual)
        if actual.count(include)!=1:raise ValueError('Unexpected random-service include: '+path)
        if canonical(actual.replace(include,''))!=original:raise ValueError('Numerical code changed beyond explicit RNG bindings: '+path)
    print('Original RNG expressions, numerical formulas and stage ordering conserved through explicit bindings')
if __name__=='__main__':verify()
