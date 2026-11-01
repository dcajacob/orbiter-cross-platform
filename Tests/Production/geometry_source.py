#!/usr/bin/env python3
"""Conserve SDK geometry declarations/formulas without platform headers."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='97d024a5'
def original(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n')
def current(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n')
def verify():
    name='Orbitersdk/include/OrbiterAPI.h';source=original(name)
    start=source.index(b'/**\n * \\brief 4-element vector\n */');end=source.index(b'//@}',start)
    records=source[start:end]
    if records.rstrip() not in current('Orbitersdk/include/OrbiterGeometry.h'):
        raise ValueError('SDK geometry value records changed')
    source=source[:start]+b'#include "OrbiterGeometry.h"\n'+source[end:]
    start=source.rfind(b'/**',0,source.index(b'inline VECTOR3 _V(double x, double y, double z)'))
    end=source.index(b'inline RECT _R',start);calculations=source[start:end]
    if calculations.rstrip() not in current('Orbitersdk/include/OrbiterVectorMath.h'):
        raise ValueError('SDK geometry calculations changed')
    source=source[:start]+b'#include "OrbiterVectorMath.h"\n\n'+source[end:]
    actual=current(name)
    if (ROOT/'Orbitersdk/include/OrbiterVesselData.h').exists():
        from vessel_values_source import restore_api
        actual=restore_api(actual)
    if source!=actual or original('Orbitersdk/include/OrbiterVector.h')!=current('Orbitersdk/include/OrbiterVector.h'):
        raise ValueError('Windows SDK changed beyond geometry extraction')
    print('Original SDK vector/matrix layouts and inline calculations extracted verbatim')
if __name__=='__main__':verify()
