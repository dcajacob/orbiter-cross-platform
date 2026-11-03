"""Check the stock instrument and switch algorithms against their original sources."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = 'f725194209634f7fd5d1d44d426cfa9b5e303e37'


def verify():
    stems = ('FuelMfd', 'Horizon', 'InstrAoa', 'InstrHsi', 'InstrVs', 'MomentInd', 'DGSwitches')
    for stem in stems:
        for suffix in ('cpp', 'h'):
            name = 'Src/Vessel/DeltaGlider/' + stem + '.' + suffix
            original = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':' + name])
            source = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
            for portable, old in ((b'oapi::UInt32', b'DWORD'), (b'oapi::UInt16', b'WORD'), (b'oapi::UInt', b'UINT')):
                source = re.sub(rb'\b' + portable + rb'\b', old, source)
            source = source.replace(b'../Common/Instrument.h', b'..\\Common\\Instrument.h')
            if source != original.replace(b'\r\n', b'\n'):
                raise ValueError('Stock DG instrument changed beyond SDK type and path spellings: ' + name)
    print('Original DG fuel, attitude, AOA, HSI, vertical speed, angular rate and cockpit switch algorithms conserved')
