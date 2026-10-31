#!/usr/bin/env python3
"""Verify that observation-enabled production files retain every original byte.

Only complete, explicitly marked test blocks may differ from the pre-extraction
source. Line endings are normalized solely for Windows checkout compatibility.
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '38b7c627878ea893390675616897071f8bb8e90f'
BLOCK = re.compile(rb'// ORBITER_PRODUCTION_OBSERVATION_BEGIN\r?\n.*?// ORBITER_PRODUCTION_OBSERVATION_END\r?\n',re.S)
OBSERVED = {'Src/Orbiter/Orbiter.cpp','Src/Orbiter/Vessel.cpp','Src/Orbiter/State.cpp'}


def verify():
    changed = subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',BASE,'--','Src','Orbitersdk','Extern','CMakeLists.txt']).decode().splitlines()
    for name in changed:
        if name not in OBSERVED:
            raise ValueError('non-observation production change before behavior capture: '+name)
    for name in OBSERVED:
        original = subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).replace(b'\r\n',b'\n')
        actual = (ROOT/name).read_bytes()
        if actual.count(b'// ORBITER_PRODUCTION_OBSERVATION_BEGIN') != actual.count(b'// ORBITER_PRODUCTION_OBSERVATION_END'):
            raise ValueError('unbalanced observation markers: '+name)
        if BLOCK.sub(b'',actual).replace(b'\r\n',b'\n') != original:
            raise ValueError('original production implementation changed: '+name)
    print('Production source matches frozen revision after removal of test-only observation blocks')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    verify()
