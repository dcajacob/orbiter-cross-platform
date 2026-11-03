#!/usr/bin/env python3
"""Check DG laptop thrust modifiers independently of camera keys in real vessels."""
import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

from systems import ROOT, fixture, digest, require

KEYMAP = ROOT/'Tests/Production/Flight/keymap-dg-laptop.cfg'
SCHEDULE = [(0, 56), (0, 201), (20, -201), (25, 209), (50, -209),
            (55, 199), (75, -199), (80, 207), (105, -207), (110, -56),
            (115, 199), (120, -199), (125, 201), (130, -201), (135, 209), (140, -209)]


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def verify(out):
    inputs = {int(r['tick']): bytes.fromhex(r['keys']) for r in rows(out/'input-state.csv')}
    thrust = rows(out/'thrust-state.csv')
    require(len(thrust) == 151 and [int(r['tick']) for r in thrust] == list(range(151)),
            'Incomplete initial/finalized native thrust-profile trace')
    for r in thrust:
        require(all(math.isfinite(float(r[k])) for k in ('main', 'hover', 'rcs', 'exhaust')),
                'Nonfinite thrust-profile state')
        require(float(r['rcs']) == 0, 'Thrust modifier also fired an RCS jet')
    curves = {}
    for name, code, field, increasing in [('main_increase', 201, 'main', True),
                                          ('main_decrease', 209, 'main', False),
                                          ('hover_increase', 199, 'hover', True),
                                          ('hover_decrease', 207, 'hover', False)]:
        selected = [r for r in thrust if (k := inputs[int(r['input_tick'])])[56] and k[code]]
        values = [float(r[field]) for r in selected]
        other = 'hover' if field == 'main' else 'main'
        require(len(values) >= 15 and any(v > 0 for v in values), 'Modified thrust key did not operate: '+name)
        require(all(float(r[other]) == 0 for r in selected), 'Thrust key changed the other engine group: '+name)
        require(all(b >= a if increasing else b <= a for a, b in zip(values, values[1:])),
                'Modified thrust key reversed its intended direction: '+name)
        if not increasing:
            require(values[-1] == 0, 'Decreasing thrust key did not reach the original zero stop: '+name)
        curves[name] = dict(samples=len(values), first=values[0], last=values[-1], maximum=max(values))
    for field, lo, hi in [('main', 22, 25), ('hover', 77, 80)]:
        values = [float(r[field]) for r in thrust if lo <= int(r['input_tick']) <= hi]
        require(len(values) >= 3 and len(set(values)) == 1 and values[0] > 0,
                'Original latched thrust did not remain constant after release: '+field)
    bare = [r for r in thrust if int(r['input_tick']) >= 112]
    require(len(bare) >= 35 and all(float(r[k]) == 0 for r in bare for k in ('main', 'hover', 'rcs', 'exhaust')),
            'Bare camera keys fired an engine or a thrust group remained on')
    camera = rows(out/'cockpit-camera.csv')
    modified_ticks = {tick+1 for tick, keys in inputs.items() if keys[56]}
    require(all(float(r['phi']) == 0 and float(r['theta']) == 0 for r in camera if int(r['tick']) in modified_ticks),
            'Modified engine controls also moved the camera')
    life = json.loads((out/'graphics-lifecycle.json').read_text())
    require(life['context_deleted'] and life['successful_presents'] == 150, 'Thrust-profile lifecycle failed')
    errors = out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(), 'Thrust-profile OpenGL errors')
    return dict(status='passed', curves=curves, bare_camera_engine_neutrality=True,
                no_rcs=True, original_latched_release=True, lifecycle=life,
                input_sha256=digest(out/'input-state.csv'), thrust_sha256=digest(out/'thrust-state.csv'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'assets', 'data', 'planets', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.exists(), 'Thrust-profile output exists; replacement is forbidden')
    out.mkdir(parents=True)
    (out/'driver.py').write_bytes(Path(__file__).read_bytes())
    cases = json.loads((ROOT/'Tests/Production/CockpitControls/cases.json').read_text())['cases']
    results = {}
    for case in cases:
        if case['cockpit'] == 1:
            continue
        directory = out/case['id']
        directory.mkdir()
        (directory/'cockpit.scn').write_text(fixture(case))
        (directory/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                                           '\nMenubarMode = 1\nInfobarMode = 1\n')
        for marker in ('control-evidence.enabled', 'vc-picking.enabled'):
            (directory/marker).write_text('DG thrust/camera modifier separation\n')
        (directory/'replay.csv').write_text('tick,phase,action,value\n'+''.join(
            f'{tick},pre,key,{code}\n' for tick, code in SCHEDULE))
        argv = [str((args.build/'orbiter-production').resolve())]
        for name in ('assets', 'data', 'planets'):
            argv += ['--'+name, str(getattr(args, name).resolve())]
        argv += ['--modules', str((args.build/'NativeModules').resolve()), '--config', str(directory/'Orbiter.cfg'),
                 '--scenario', str(directory/'cockpit.scn'), '--keymap', str(KEYMAP),
                 '--replay', str(directory/'replay.csv'), '--evidence', str(directory),
                 '--frames', '150', '--fixed-step', str(1/60), '--run']
        (directory/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
        with (directory/'console.log').open('w') as log:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
        results[case['id']] = verify(directory)
    report = dict(status='passed', source_sha256=digest(Path(__file__)), keymap_sha256=digest(KEYMAP),
                  transport='Native replay input queue, original key map and real stock vessel immediate controls',
                  cases=results)
    (out/'thrust-profile.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
