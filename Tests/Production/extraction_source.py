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
    if 'Src/Orbiter/elevmgrFile.cpp' in declared:
        from elevation_source import verify as verify_elevation
        verify_elevation()
    if 'Src/Orbiter/Production/NavigationServices.cpp' in declared:
        from navigation_source import verify as verify_navigation
        verify_navigation()
    if 'Src/Orbiter/Production/ConfigurationTypes.h' in declared:
        from configuration_source import verify as verify_configuration
        verify_configuration()
    if 'Src/Celbody/SPICE/spice.cpp' in declared:
        from SpiceModules.source_audit import verify as verify_celestial_modules
        verify_celestial_modules()
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
    if 'Src/Orbiter/PsysGravity.cpp' in declared:
        # Move the entire force/source-selection section, including its summation
        # order and ephemeris calls. No alternate native force implementation.
        parent = 'bef087ce'
        original = git('show', parent+':Src/Orbiter/Psys.cpp').replace(b'\r\n',b'\n')
        start = original.index(b'void PlanetarySystem::ScanGFieldSources (')
        end = original.index(b'void PlanetarySystem::Update (bool force)',start)
        extracted = (ROOT/'Src/Orbiter/PsysGravity.cpp').read_bytes().replace(b'\r\n',b'\n')
        extracted = extracted[extracted.index(b'void PlanetarySystem::ScanGFieldSources ('):].replace(b'orbiter::production::UInt32',b'DWORD')
        def force_text(source):
            return b'\n'.join(line.rstrip(b' \t') for line in source.splitlines()).rstrip(b'\n')
        if force_text(extracted) != force_text(original[start:end]):
            raise ValueError('production world gravity formulas/source selection or accumulation order changed')
        canonical = (ROOT/'Src/Orbiter/Psys.cpp').read_bytes().replace(b'\r\n',b'\n').replace(
            b'#include "Base.h"\n#include "Star.h"\n#include "Planet.h"\n',b'').replace(
            b'orbiter::production::UInt32 PlanetarySystem::nBase(const Planet *planet) const { return planet->nBase(); }\n'
            b'Base *PlanetarySystem::GetBase (const Planet *planet, orbiter::production::UInt32 i) { return planet->GetBase(i); }\n\n',b'')
        if canonical != original[:start]+original[end:]:
            raise ValueError('production world lifecycle/configuration changed outside gravity extraction')
        original = git('show',parent+':Src/Orbiter/Psys.h').replace(b'\r\n',b'\n')
        actual = (ROOT/'Src/Orbiter/PsysCore.h').read_bytes().replace(b'\r\n',b'\n')
        canonical = actual.split(b'private:',1)[1].replace(b'orbiter::production::SceneLabelList',b'oapi::GraphicsClient::LABELLIST').replace(
            b'#endif // !ORBITER_PRODUCTION_SYSTEM_CORE_H',b'#endif // !__PSYS_H')
        if canonical != original.split(b'private:',1)[1]:
            raise ValueError('production planetary-system private storage changed')
    mesh_records=ROOT/'Orbitersdk/include/OrbiterMeshData.h'
    if 'Src/Orbiter/ZTreeMgr.cpp' in declared:
        original=git('show',CAPTURE+':Src/Orbiter/ZTreeMgr.cpp').replace(b'\r\n',b'\n')
        actual=(ROOT/'Src/Orbiter/ZTreeMgr.cpp').read_bytes().replace(b'\r\n',b'\n')
        original=original[original.index(b'DWORD ZTreeMgr::Idx'):original.index(b'DWORD ZTreeMgr::ReadData')]
        original=original[original.index(b'if (lvl <= 4)'):]
        actual=actual[actual.index(b'std::uint32_t ZTreeMgr::Idx'):actual.index(b'std::uint32_t ZTreeMgr::ReadData')]
        actual=actual[actual.index(b'if (lvl<=4)'):].replace(b'std::uint32_t',b'DWORD').replace(b'UINT32_MAX',b'(DWORD)-1')
        def mapping_tokens(source):
            return re.sub(rb'\s+',b'',re.sub(rb'//[^\n]*',b'',source))
        if mapping_tokens(original)!=mapping_tokens(actual):
            raise ValueError('production quadtree mapping changed beyond scalar spelling/whitespace and bounds checks')
    if 'Src/Orbiter/Star.cpp' in declared:
        original=git('show',CAPTURE+':Src/Orbiter/Star.cpp').replace(b'\r\n',b'\n')
        actual=(ROOT/'Src/Orbiter/Star.cpp').read_bytes().replace(b'\r\n',b'\n')
        canonical=actual[actual.index(b'Star::Star (double'):].replace(
            b'GetBodyServices().ConfigPath(fname)',b'g_pOrbiter->ConfigPath (fname)').replace(
            b'GetCelestialServices().HasModule(*this) && GetCelestialServices().HasEphemeris(*this)',b'module && module->bEphemeris()')
        if canonical!=original[original.index(b'Star::Star (double'):] :
            raise ValueError('production Star behavior changed beyond host service substitutions')
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
        handles = ROOT/'Orbitersdk/include/OrbiterHandles.h'
        if handles.exists():
            start = original.index(b'/// \\brief Handle for objects (vessels, stations, planets)')
            end = original.index(b'//@}',start)
            if handles.read_bytes().replace(b'\r\n',b'\n').count(original[start:end]) != 1:
                raise ValueError('Orbiter opaque handles were not conserved verbatim')
            ranges.append((start,end,b'#include "OrbiterHandles.h"\n'))
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
