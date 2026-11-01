#!/usr/bin/env python3
"""Conserve original production formulas across explicit platform adapters."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
BASE='684bd5b27005feecfa9effe796bd216f85e3392f'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).replace(b'\r\n',b'\n')
def verify():
    name='Src/Celbody/SPICE/spice.cpp';source=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
    source=source.replace(b'#ifndef ORBITER_NATIVE_MODULE\n',b'').split(b'\n#else\n#include "NativeSpiceFactory.inc"\n#endif',1)[0]
    for before,after in [(b'#include "SpicePlatform.h"',b'#include "Orbitersdk.h"'),
        (b'SpiceAtmosphereParameters',b'ATMPARAM'),(b'SpiceAtmosphere',b'ATMOSPHERE'),(b'SpiceModuleBase',b'CELBODY2'),
        (b'SpiceBodyContext',b'OBJHANDLE'),(b'SpiceConfiguration',b'FILEHANDLE'),(b'SpiceReadString',b'oapiReadItem_string'),
        (b'SpiceReadReal',b'oapiReadItem_float'),(b'SpiceLog',b'oapiWriteLog'),(b'SpiceTimeToMJD',b'oapiTime2MJD'),
        (b'std::snprintf',b'sprintf_s'),(b'std::sscanf',b'sscanf_s'),(b'SpiceKernelPath(kernel_name).c_str()',b'kernel_name.c_str()')]:
        source=source.replace(before,after)
    for method,kind in [('show_error','void'),('Interpolate','void'),('calc_gm','double')]:
        source=source.replace(('\t'+kind+' '+method+'(').encode(),('\t'+kind+' SpiceBody::'+method+'(').encode())
    if source.rstrip(b'\n')!=old(name).rstrip(b'\n'):raise ValueError('production SPICE changed beyond declared host/type adapters')
    for model in ['EarthAtmJ71G','EarthAtm2006','MarsAtm2006']:
        for suffix in ['h','cpp']:
            name=f'Src/Celbody/Atmosphere/{model}/{model}.{suffix}'
            source=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            source=source.replace(b'#ifndef ORBITER_NATIVE_MODULE\n',b'').split(b'\n#else\n#include "../NativeAtmosphereFactory.inc"\n#endif',1)[0]
            for before,after in [(b'AtmosphereConstants',b'ATMCONST'),(b'AtmosphereCelestial',b'CELBODY2'),
                (b'AtmosphereBase',b'ATMOSPHERE'),(b'AtmosphereBodyHandle',b'OBJHANDLE'),(b'AtmosphereSimMJD(cbody)',b'oapiGetSimMJD()'),
                (b'AtmosphereGlobalPosition (cbody, hBody,',b'oapiGetGlobalPos (hBody,'),
                (b'AtmosphereGlobalToEquatorial (cbody, hBody,',b'oapiGlobalToEqu (hBody,'),(b'AtmosphereNegate(gsun)',b'-gsun'),
                (b'#include "../AtmospherePlatform.h"',b'#include "OrbiterAPI.h"\n#include "CelbodyAPI.h"')]:source=source.replace(before,after)
            if source.rstrip(b'\n')!=old(name).rstrip(b'\n'):raise ValueError('production atmosphere formulas/order changed: '+name)
    print('Original SPICE and three stock atmosphere implementations conserved after declared platform/type adapters')
if __name__=='__main__':verify()
