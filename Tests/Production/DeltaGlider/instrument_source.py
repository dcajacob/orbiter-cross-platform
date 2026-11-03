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
    verify_subsystems()
    print('Original DG fuel, attitude, AOA, HSI, vertical speed, angular rate and cockpit switch algorithms conserved')


def verify_subsystems():
    # Compare every stock flight/control implementation with the reference
    # application. Header-only forward declarations don't change any members.
    from vessel_runtime_source import tokens
    stems = ('AAPSubsys', 'AerodynSubsys', 'AvionicsSubsys', 'DockingSubsys',
             'FailureSubsys', 'GearSubsys', 'HoverSubsys', 'HudCtrl', 'LightSubsys',
             'MainRetroSubsys', 'MfdSubsys', 'PressureSubsys', 'RcsSubsys',
             'ScramSubsys', 'ThermalSubsys')
    for stem in stems:
        for suffix in ('cpp', 'h'):
            name = f'Src/Vessel/DeltaGlider/{stem}.{suffix}'
            original = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':' + name]).decode('cp1252')
            source = (ROOT / name).read_bytes().decode('cp1252')
            for portable, old in [('oapi::UInt32', 'DWORD'), ('oapi::UInt16', 'WORD'), ('oapi::UInt', 'UINT'),
                                  ('oapi::SdkRectangle', 'RECT'), ('dg::CompareText', '_stricmp'),
                                  ('dg::ComparePrefix', 'strnicmp' if stem == 'LightSubsys' else '_strnicmp'),
                                  ('dg::RandomLampPhase()', '(double)rand()/(double)RAND_MAX')]:
                source = source.replace(portable, old)
            if suffix == 'h':
                original = re.sub(r'^class \w+;\s*', '', original, flags=re.M)
                source = re.sub(r'^class \w+;\s*', '', source, flags=re.M)
            if stem == 'AAPSubsys':
                original = original.replace('#include "Orbitersdk.h"', '')
                source = source.replace('#include <string>', '')
                if suffix == 'cpp':
                    # Vessel names are now quoted into a dynamically sized Lua command.
                    a = original.index('char setVesselCmd[256]')
                    b = original.index('// set autopilot vessel', a)
                    c = source.index('std::string setVesselCmd = "setvessel(vessel.get_interface(\'"')
                    d = source.index('// set autopilot vessel', c)
                    assert 'oapiAsyncScriptCmd (hAAP, setVesselCmd.c_str());' in source[c:d]
                    original = original[:a] + original[b:]
                    source = source[:c] + source[d:]
            if tokens(original) != tokens(source):
                raise ValueError('Stock DG flight or control behavior differs: ' + name)
    print('All 15 stock DG and DG-S subsystem implementations conserved through SDK and platform bindings')
