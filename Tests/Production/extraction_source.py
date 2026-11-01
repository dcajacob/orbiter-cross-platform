#!/usr/bin/env python3
"""Audit the declared extraction against the preserved observation-only source.

This replaces the pre-extraction prohibition on *any* production change with an
explicit file/byte ledger. It never refreshes references or permits an undeclared
source or public SDK change. Runtime behavior remains gated separately against
the original Windows references, not against newly generated expected values.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import re

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = '684bd5b27005feecfa9effe796bd216f85e3392f'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def checksum(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def verify():
    from observation_source import BASE, BLOCK, OBSERVED
    # First prove that the accepted observation source still conserves every
    # pre-extraction production byte. Never reinterpret that historic capture.
    changed = git('diff', '--name-only', BASE, CAPTURE, '--', 'Src', 'Orbitersdk', 'Extern', 'CMakeLists.txt').decode().splitlines()
    if set(changed) - OBSERVED:
        raise ValueError('observation source contains non-observation production changes')
    for name in OBSERVED:
        observed = git('show', CAPTURE+':'+name)
        if BLOCK.sub(b'', observed).replace(b'\r\n', b'\n') != git('show', BASE+':'+name).replace(b'\r\n', b'\n'):
            raise ValueError('frozen observation source changed: '+name)
    ledger = json.loads(Path(__file__).with_name('phase3-extraction.lock.json').read_text())
    if ledger['observed_source'] != CAPTURE or ledger['production_source'] != BASE:
        raise ValueError('extraction baseline identity changed')
    declared = ledger['files']
    current = git('diff', '--name-only', CAPTURE, '--', 'Src', 'Orbitersdk', 'Extern', 'CMakeLists.txt').decode().splitlines()
    if set(current) - set(declared):
        raise ValueError('undeclared production change: '+str(sorted(set(current)-set(declared))))
    for name, entry in declared.items():
        if checksum((ROOT/name).read_bytes()) != entry['sha256_lf']:
            raise ValueError('extraction ledger does not match source: '+name)
        if entry['original_sha256_lf'] is not None and checksum(git('show', CAPTURE+':'+name)) != entry['original_sha256_lf']:
            raise ValueError('original extraction source changed: '+name)
    # Only the file loader and unused application include leave this source.
    # All force formulas, recurrence/stage ordering and private numerical fields
    # remain verbatim from the original production implementation.
    if (ROOT/'Src/Orbiter/PinesGravFile.cpp').exists():
        original = git('show', CAPTURE+':Src/Orbiter/PinesGrav.cpp').replace(b'\r\n',b'\n')
        start = original.index(b'int PinesGravProp::readGravModel(')
        end = original.index(b'Vector PinesGravProp::GetPinesGrav', start)
        expected = (original[:start]+original[end:]).replace(b'#include <fstream>\n',b'').replace(b'#include "Orbiter.h"\n',b'')
        if expected != (ROOT/'Src/Orbiter/PinesGrav.cpp').read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('production Pines force/recurrence implementation changed')
        original = git('show', CAPTURE+':Src/Orbiter/PinesGrav.h').replace(b'\r\n',b'\n')
        actual = (ROOT/'Src/Orbiter/PinesGrav.h').read_bytes().replace(b'\r\n',b'\n')
        if original.split(b'private:',1)[1] != actual.split(b'private:',1)[1]:
            raise ValueError('production Pines numerical workspace changed')
    if (ROOT/'Src/Orbiter/CelbodyFile.cpp').exists():
        original=git('show',CAPTURE+':Src/Orbiter/Celbody.cpp').replace(b'\r\n',b'\n')
        actual=(ROOT/'Src/Orbiter/Celbody.cpp').read_bytes().replace(b'\r\n',b'\n')
        def calculation_methods(source):
            return source[source.index(b'CelestialBody::~CelestialBody'):source.index(b'void CelestialBody::RegisterModule')]
        canonical=calculation_methods(actual)
        substitutions=(
            (b'CelestialClock().',b'td.'),(b'UInt32',b'DWORD'),
            (b'GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);',b'TRACENEW'),
            (b'el->Setup (mass, cbody->Mass(), td.MJD_ref, td.MJD_ref);',b'el->Setup (mass, cbody->Mass(), td.MJD_ref);'),
            (b'el->Update (bpos, bvel, td.SimT1);',b'el->Update (bpos, bvel);'),
            (b'el->Update (*gpos, *gvel, td.SimT1);',b'el->Update (*gpos, *gvel);'),
            (b'GetCelestialServices().HasModule(*this)',b'module'),
            (b'GetCelestialServices().Ephemeris(*this, mjd, req, res)',b'module->clbkEphemeris (mjd, req, res)'),
            (b'GetCelestialServices().FastEphemeris(*this, simt, req, res)',b'module->clbkFastEphemeris (simt, req, res)'),
            (b'orbiter::math::PositiveAngle (',b'posangle ('),(b'rotation_off, PI2);',b'rotation_off);'),
            (b'GetBodyServices().CheckUpdateState(s1 != nullptr);',b'dCHECK(s1, "Update state not available")'),
            (b'\tjcoeff            = nullptr;\n',b''),(b'\tsecondary         = nullptr;\n',b''),
            (b'\tmemset(&modIntf, 0, sizeof(modIntf));\n',b''),
            (b'if (nsecondary) memcpy (tmp, secondary,',b'memcpy (tmp, secondary,'))
        for before,after in substitutions:canonical=canonical.replace(before,after)
        if canonical!=calculation_methods(original):
            raise ValueError('production celestial formulas/order changed beyond explicit host/time substitutions')
        nonmember=b'// =======================================================================\n// Nonmember functions'
        sdk=b'// =======================================================================\n// Class CELBODY: API interface class'
        if actual[actual.index(nonmember):]!=original[original.index(nonmember):original.index(sdk)]:
            raise ValueError('production polar/ephemeris interpretation changed')
        adapter=(ROOT/'Src/Orbiter/CelbodySdk.cpp').read_bytes().replace(b'\r\n',b'\n')
        if adapter[adapter.index(sdk):]!=original[original.index(sdk):]:
            raise ValueError('Windows celestial SDK implementations changed')
        original=git('show',CAPTURE+':Src/Orbiter/Celbody.h').replace(b'\r\n',b'\n')
        actual=(ROOT/'Src/Orbiter/Celbody.h').read_bytes().replace(b'\r\n',b'\n')
        canonical=actual.split(b'protected:',1)[1].replace(b'orbiter::production::UInt32',b'DWORD').replace(b'void* hMod',b'HINSTANCE hMod')
        if canonical.rstrip(b'\n')!=original.split(b'protected:',1)[1].rstrip(b'\n'):
            raise ValueError('celestial numerical state layout changed beyond portable scalar/module handle spelling')
    mesh_records=ROOT/'Orbitersdk/include/OrbiterMeshData.h'
    if mesh_records.exists():
        original=git('show', CAPTURE+':Orbitersdk/include/OrbiterAPI.h').replace(b'\r\n',b'\n')
        extracted=mesh_records.read_bytes().replace(b'\r\n',b'\n')
        ranges=[]
        for index,name in enumerate((b'COLOUR4',b'NTVERTEX',b'MATERIAL')):
            block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} '+name+rb';',original,re.S)
            if not block or extracted.count(block[0])!=1:
                raise ValueError('public mesh SDK record was not conserved verbatim: '+name.decode())
            ranges.append((original.rfind(b'/**',0,block.start()),block.end(),
                b'#include "OrbiterMeshData.h"' if index==0 else b''))
        celestial_records=ROOT/'Orbitersdk/include/OrbiterCelestialData.h'
        if celestial_records.exists():
            data=celestial_records.read_bytes().replace(b'\r\n',b'\n')
            start=original.index(b'const double PI    =')
            end=original.index(b'\n',original.index(b'const double ATMD ',start))+1
            if data.count(original[start:end])!=1:
                raise ValueError('SDK constants were not conserved verbatim')
            ranges.append((start,end,b'#include "OrbiterCelestialData.h"\n'))
            block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} ATMPARAM;',original,re.S)
            if not block or data.count(block[0])!=1:
                raise ValueError('SDK ATMPARAM was not conserved verbatim')
            ranges.append((original.rfind(b'/**',0,block.start()),block.end(),b''))
            start=original.index(b'// Object types\n')
            end=original.index(b'\n',original.index(b'#define OBJTP_SURFBASE',start))+1
            if data.count(original[start:end])!=1:
                raise ValueError('SDK object types were not conserved verbatim')
            ranges.append((start,end,b''))
            celapi=git('show',CAPTURE+':Orbitersdk/include/CelBodyAPI.h').replace(b'\r\n',b'\n')
            start=celapi.index(b'#define EPHEM_TRUEPOS')
            end=celapi.index(b'\n',celapi.index(b'#define EPHEM_POLAR',start))+1
            if data.count(celapi[start:end])!=1:
                raise ValueError('SDK ephemeris flags were not conserved verbatim')
            expected=celapi[:start]+b'#include "OrbiterCelestialData.h"\n'+celapi[end:]
            if expected!=(ROOT/'Orbitersdk/include/CelBodyAPI.h').read_bytes().replace(b'\r\n',b'\n'):
                raise ValueError('Windows celestial SDK changed beyond its value extraction')
        expected=original
        for start,end,replacement in sorted(ranges,reverse=True):
            expected=expected[:start]+replacement+expected[end:]
        if expected!=(ROOT/'Orbitersdk/include/OrbiterAPI.h').read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Windows SDK changed beyond the verbatim value extraction')
    print('Verified original observation-only source and', len(declared),
          'explicit extraction files; frozen runtime references remain required')


if __name__ == '__main__':
    verify()
