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
    mesh_records=ROOT/'Orbitersdk/include/OrbiterMeshData.h'
    if mesh_records.exists():
        original=git('show', CAPTURE+':Orbitersdk/include/OrbiterAPI.h').replace(b'\r\n',b'\n')
        extracted=mesh_records.read_bytes().replace(b'\r\n',b'\n')
        ranges=[]
        for name in (b'COLOUR4',b'NTVERTEX',b'MATERIAL'):
            block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} '+name+rb';',original,re.S)
            if not block or extracted.count(block[0])!=1:
                raise ValueError('public mesh SDK record was not conserved verbatim: '+name.decode())
            ranges.append((original.rfind(b'/**',0,block.start()),block.end()))
        expected=original
        for index,(start,end) in reversed(list(enumerate(ranges))):
            expected=expected[:start]+(b'#include "OrbiterMeshData.h"' if index==0 else b'')+expected[end:]
        if expected!=(ROOT/'Orbitersdk/include/OrbiterAPI.h').read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Windows SDK changed beyond the verbatim mesh record extraction')
    print('Verified original observation-only source and', len(declared),
          'explicit extraction files; frozen runtime references remain required')


if __name__ == '__main__':
    verify()
