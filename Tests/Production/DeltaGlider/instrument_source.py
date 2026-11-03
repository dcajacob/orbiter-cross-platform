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
            if stem == 'MomentInd':
                # The 63 temporary VC vertices now have automatic storage.
                original = original.replace(b'int nvtx;', b'static constexpr int nvtx = 7*3*3;')
                original = original.replace(b'\tnvtx = 7*3*3;\n', b'')
                original = original.replace(b'static NTVERTEX *vtx = 0;\n\tif (!vtx) vtx = new NTVERTEX[nvtx];',
                                            b'NTVERTEX vtx[nvtx];')
            if source != original.replace(b'\r\n', b'\n'):
                raise ValueError('Stock DG instrument changed beyond SDK type and path spellings: ' + name)
    verify_subsystems()
    verify_vessel()
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
            if stem == 'DockingSubsys':
                original = original.replace('isDocked = false;\n\tdockTime', 'isDocked = false;\n\tisSealing = false;\n\tdockTime')
            if stem == 'HoverSubsys':
                original = original.replace('ctrl(hhac), bsrc(blitsrc)\n{\n\tbtgt = 0;',
                    'ctrl(hhac), btgt(0), bsrc(blitsrc), holdmode_disp(HoverHoldComponent::HOLD_NONE), hold_disp(false), holdstr("         ")\n{')
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


def verify_vessel():
    from vessel_runtime_source import aliases, equal
    name = 'Src/Vessel/DeltaGlider/DeltaGlider.cpp'
    original = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':' + name]).decode('cp1252')
    source = aliases((ROOT / name).read_bytes().decode('cp1252'))
    first = 'static const DWORD ntdvtx_geardown'
    last = '// API callback interface'
    actual = source[source.index(first):source.index(last)]
    expected = original[original.index(first):original.index(last)]
    actual = actual.replace('dg::RandomInteger()', 'rand()').replace('dg::ComparePrefix', '_strnicmp')
    # Signed scan count/seat numbers and bounded skin input preserve valid state.
    expected = expected.replace('DWORD i, res, pi[4];','int i, res, pi[4];')
    expected = expected.replace('if (pi[i]-1 < 4)','if (pi[i] >= 1 && pi[i] <= 4)')
    expected = expected.replace('sscanf (line+4, "%s", skinpath);','if (sscanf (line+4, "%31s", skinpath) != 1) continue;')
    equal(expected, actual, 'Stock DeltaGlider flight, animations, panel, VC, UI and callbacks')
    entry = 'DLLCLBK VESSEL *ovcInit'
    end = '// Scenario editor interface'
    equal(original[original.index(entry):original.index(end)], source[source.index(entry):source.index(end)],
          'Stock DG vessel creation and release')
    editor = 'DeltaGlider *GetDG (HWND'
    equal(original[original.index(editor):], source[source.index(editor):source.rindex('#else')],
          'Stock Windows DG scenario editor')
    print('Stock DeltaGlider and DG-S main vessel flight and cockpit implementations conserved')
