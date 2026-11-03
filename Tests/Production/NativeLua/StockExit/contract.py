"""Identity and complete-trace checks for the untouched stock vessel API exit."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parents[1]/'StockScenarios'))
from inventory import ships, require, digest

ERRORS = (' - FAILED!', 'Assertion failed', 'Lua error:', 'LuaCall (',
          'Orbiter native production:', 'Production teardown:', 'runtime error:',
          'ERROR: AddressSanitizer', 'ERROR: LeakSanitizer',
          'LeakSanitizer has encountered', 'AddressSanitizer:DEADLYSIGNAL',
          'Could not find a module')


def sha_lf(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def settings():
    value = json.loads((HERE/'case.json').read_text())
    require(re.fullmatch('[0-9a-f]{40}', value['application_source']), 'Original source must be immutable')
    for path, expected in [('Scenarios/'+value['scenario'], value['scenario_sha256_lf']),
                           (value['script'], value['script_sha256_lf'])]:
        frozen = subprocess.check_output(['git', '-C', str(ROOT), 'show', value['application_source']+':'+path])
        require(hashlib.sha256(frozen.replace(b'\r\n', b'\n')).hexdigest() == expected == sha_lf(ROOT/path),
                'Stock exit source changed: '+path)
    require(value['fixed_step'] == .25 and value['frames'] == 60 and value['repeats'] == 2 and
            value['expected_exit_code'] == 0, 'Stock exit observation limits changed')
    require(len(ships((ROOT/'Scenarios'/value['scenario']).read_text())) == 8,
            'Complete stock API scene must retain all eight vessels')
    return value


def expected_events(config):
    source = (ROOT/config['script']).read_text()
    source = source[source.index('oapi.set_tacc(10)'):]
    events = []
    for line in source.splitlines():
        match = re.fullmatch(r'add_line\(("(?:\\.|[^"\\])*")\)', line.strip())
        if match:
            value = json.loads(match[1])
            if value: events.append(value)
        elif line.strip() == 'pass()':
            events.append(' - passed')
    require(events[0] == '=== Lua script unit tests ===' and events[-1] == '=== All tests passed ===',
            'Stock assertion log protocol changed')
    return events


def log_events(text):
    result = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if 'Test: ' in line:
            result.append(line[line.index('Test: '):])
        elif line.endswith(' - passed'):
            result.append(' - passed')
        else:
            for marker in ['=== Lua script unit tests ===', '--- vessel module ---',
                           '--- vessel class ---', '=== All tests passed ===']:
                if line.endswith(marker): result.append(marker)
    return result


def rows(path):
    with path.open(newline='', encoding='ascii') as stream:
        reader = csv.DictReader(stream); result = list(reader)
        require(reader.fieldnames and all(None not in row and None not in row.values() for row in result),
                'Malformed stock exit trace: '+str(path))
        return result


def inspect(out, config, host, returncode):
    require(host in ('native-linux', 'original-windows'), 'Unknown stock exit host')
    require(returncode == config['expected_exit_code'], 'Stock script did not return the original exit code')
    require(not (out/'stock-exit-failure.txt').exists(), 'Stock exit observer failed')
    scenario = out/('Scenarios/Behavior.scn' if host == 'original-windows' else 'flight.scn')
    require(scenario.read_bytes() == (ROOT/'Scenarios'/config['scenario']).read_bytes(), 'Stock scenario bytes changed')
    text = (out/('Orbiter.log' if host == 'original-windows' else 'console.txt')).read_text(errors='replace')
    require(not any(marker in text for marker in ERRORS), 'Stock assertion, Lua, runtime or sanitizer error')
    events = expected_events(config)
    require(log_events(text) == events, 'Stock assertions are incomplete, reordered or duplicated')
    renderer = json.loads((out/('stock-exit-renderer.json' if host == 'original-windows' else 'renderer-info.json')).read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width'] == 1280 and
            renderer['client_height'] == 720, 'Actual stock exit renderer or geometry differs')
    phases = rows(out/'stock-exit-phases.csv')
    count = len(phases)
    require(0 < count < config['frames'], 'Stock script did not intentionally terminate before the frame limit')
    require([(int(row['completed_frames']), row['phase']) for row in phases] ==
            [(i, 'app.frame.end') for i in range(1, count+1)], 'Finalized stock exit boundaries are incomplete')
    require(not (out/'stock-exit-normal-end.txt').exists(), 'Original stock script reached normal session end')
    state = rows(out/'stock-vessel-state.csv'); groups = {}
    expected = {(name, kind.lower()) for name, kind in ships(scenario.read_text()).items()}
    for row in state:
        require(all(math.isfinite(float(value)) for key, value in row.items() if key not in ('object', 'class')),
                'Nonfinite stock exit vessel state')
        groups.setdefault(int(row['tick']), []).append(row)
    require(set(groups) == set(range(count+1)), 'Missing finalized all-vessel exit ticks')
    for tick, group in groups.items():
        require(len(group) == len(expected) and {(r['object'], r['class'].lower()) for r in group} == expected,
                'Incomplete stock exit vessel manifest at tick '+str(tick))
        require(sum(int(row['focus']) for row in group) == 1, 'Invalid stock exit focus manifest')
    docks = rows(out/'stock-vessel-docks.csv'); keys = set()
    for row in docks:
        key = (int(row['tick']), row['object'], int(row['index']))
        require(key not in keys, 'Duplicate stock exit docking port'); keys.add(key)
        require(all(math.isfinite(float(value)) for name, value in row.items() if name not in ('object', 'docked')),
                'Nonfinite stock exit docking port')
    require(keys == {(int(r['tick']), r['object'], i) for r in state for i in range(int(r['docks']))},
            'Incomplete stock exit docking-port observations')
    life_path = out/'graphics-lifecycle.json'
    life = json.loads(life_path.read_text()) if life_path.exists() else None
    if host == 'native-linux':
        require(life == dict(rendered_frames=count, successful_presents=count, context_deleted=True),
                'Native stock exit presentations or graphics teardown incomplete')
        require((out/'saved.scn').read_bytes() == b'Existing save preserved across stock oapi.exit.\n',
                'Stock explicit exit saved over the current state')
    else:
        require(life is None, 'Preserved abrupt exit unexpectedly used normal graphics shutdown')
    return dict(status='captured', host=host, returncode=returncode, completed_frames=count,
                finalized_ticks=count+1, all_vessel_rows=len(state), docking_rows=len(docks),
                declared_vessels=len(expected), assertion_events=len(events), assertion_passes=events.count(' - passed'),
                lifecycle=life, renderer=renderer, files_sha256={str(p.relative_to(out)): digest(p) for p in out.iterdir()
                                            if p.is_file() and p.suffix in ('.csv', '.txt', '.log', '.json', '.scn')})
