#!/usr/bin/env python3
"""Operate real DG systems with buffered keys and reload their original scenario state."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent/'Cockpit'))
from reference import fixture, stage, mesa_files

# Stock DG subsystem construction order, shared by DeltaGlider and DG-S.
# These are the animated mechanisms, rather than their panel/VC control levers.
ANIMATIONS = dict(AIRBRAKE=4, GEAR=7, AIRLOCK=11, IAIRLOCK=12,
                  HATCH=13, RADIATOR=16, NOSECONE=17)
KEYS = ((4, 34, False), (6, 37, False), (8, 32, False),
        (10, 24, False), (12, 24, True), (14, 22, False),
        (16, 48, False), (20, 48, False))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def states(path):
    """Read only the focus vessel; closed defaults are omitted by AnimState2."""
    result = dict.fromkeys(ANIMATIONS, (0., 0.))
    inside = False
    found = False
    for line in path.read_text().splitlines():
        if line.startswith('DG:'):
            require(not found, 'Duplicate DG vessel in saved scenario')
            inside = found = True
        elif line == 'END':
            inside = False
        elif inside and (parts := line.split()) and parts[0] in result:
            require(len(parts) == 3, 'Malformed original subsystem state')
            value = tuple(map(float, parts[1:]))
            require(all(math.isfinite(v) for v in value) and 0 <= value[0] <= 1,
                    'Invalid saved subsystem state: '+parts[0])
            result[parts[0]] = value
    require(found, 'Saved original DG vessel missing')
    return result


def keyboard(closing=False):
    actions = []
    for tick, code, control in KEYS:
        control = control or (closing and code == 48)
        if control:
            actions.append((tick, 'pre', 'key', 29))
        actions.extend(((tick, 'pre', 'key', code), (tick+1, 'pre', 'key', -code)))
        if control:
            actions.append((tick+1, 'pre', 'key', -29))
    return sorted(actions, key=lambda action: action[0])


def launch_native(args, out, source, frames, actions):
    out.mkdir()
    (out/'flight.scn').write_text(source)
    (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                                  '\nMenubarMode = 1\nInfobarMode = 1\n')
    commands = [*actions, (frames-1, 'after', 'save', 0)]
    (out/'replay.csv').write_text('tick,phase,action,value\n'+''.join(
        ','.join(map(str, action))+'\n' for action in commands))
    command = [str(args.build/'orbiter-production'), '--config', str(out/'Orbiter.cfg'),
               '--scenario', str(out/'flight.scn'), '--save', str(out/'saved.scn'),
               '--replay', str(out/'replay.csv'), '--evidence', str(out),
               '--frames', str(frames), '--fixed-step', '0.25', '--run']
    for key in ('assets', 'data', 'planets'):
        command.extend(('--'+key, str(getattr(args, key))))
    command.extend(('--modules', str(args.build/'NativeModules')))
    (out/'invocation.json').write_text(json.dumps(command, indent=2)+'\n')
    with (out/'console.log').open('w') as log:
        subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=180)


def dispatches(actions):
    """The native pre-step queue is consumed at the next frame's input boundary."""
    control = False
    result = []
    for tick, phase, action, code in actions:
        require(phase == 'pre' and action == 'key', 'Unsupported systems keyboard schedule')
        if abs(code) == 29:
            control = code > 0
        elif code > 0:
            result.append((tick+1, code, int(control)))
    return result


def launch_original(args, out, case, source, frames, actions):
    runtime = json.loads((args.executable.parent/'test-runtime.json').read_text())
    require(runtime['source_commit'] == 'f725194209634f7fd5d1d44d426cfa9b5e303e37',
            'Wrong preserved original application/SDK source')
    expected = dispatches(actions)
    def configure(directory):
        config = directory/'Orbiter.cfg'
        config.write_text(config.read_text().replace('  ProductionBehaviorDriver',
            '  ProductionCockpitDriver\n  OGLClient')+'\nMenubarMode = 1\nInfobarMode = 1\n')
        (directory/'Scenarios/Behavior.scn').write_text(source)
        (directory/'flight.scn').write_text(source)
        (directory/'systems-case.txt').write_text(f"{frames} {case['cockpit']} {len(expected)}\n"+
            ''.join(f'{tick} {key} {control}\n' for tick, key, control in expected))
        (directory/'ogl-evidence.enabled').touch()
        mesa_files(args.mesa, directory)
    stage(args.executable, args.data, args.planets, out,
          dict(frames=frames, fixed_step=.25), configure)
    require(not (out/'cockpit-failure.txt').exists() and
            (out/'cockpit-complete.txt').read_text().strip() == str(frames),
            'Original systems observer did not complete')
    actual = [(int(r['tick']), int(r['key']), int(r['control']))
              for r in rows(out/'system-inputs.csv')]
    require(actual == expected, 'Original dispatched keys differ from native consumption schedule')
    shutil.copyfile(out/'console.txt', out/'console.log')
    shutil.copyfile(out/'Scenarios/SystemsResult.scn', out/'saved.scn')
    profile = (out/'math-profile.txt').read_text().strip()
    require(profile in ('fma3', 'sse2'), 'Unknown actual original math profile')
    (out/'numerics.json').write_text(json.dumps(dict(math='windows-crt-'+profile))+'\n')


def launch(args, case, name, source, frames, actions):
    out = args.output/case['id']/name
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.original:
        launch_original(args, out, case, source, frames, actions)
    else:
        launch_native(args, out, source, frames, actions)
    log = (out/'console.log').read_text()
    if args.original:
        log += (out/'Orbiter.log').read_text(errors='replace')
    for marker in ('Lua error:', 'LuaCall (', 'ERROR: AddressSanitizer',
                   'ERROR: LeakSanitizer', 'runtime error:'):
        require(marker not in log, 'Runtime error during '+str(out)+': '+marker)
    lifecycle = json.loads((out/'graphics-lifecycle.json').read_text())
    require(lifecycle == dict(rendered_frames=frames, successful_presents=frames,
                              context_deleted=True), 'Incomplete systems graphics lifecycle')
    errors = out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(), 'Systems graphics errors')
    cockpit = rows(out/'cockpit-state.csv')
    require([int(r['tick']) for r in cockpit] == list(range(frames+1)) and
            all(r['object'] == 'DG' and r['class'] == case['class'] and
                int(r['cockpit']) == case['cockpit'] for r in cockpit),
            'Original vessel or requested cockpit did not finish')
    require(all(math.isfinite(float(value)) for row in cockpit for key, value in row.items()
                if key not in ('object', 'class')), 'Nonfinite DG cockpit/physical state')
    animations = {label: [] for label in ANIMATIONS}
    for row in rows(out/'flight-animations.csv'):
        if row['object'] != 'DG':
            continue
        for label, index in ANIMATIONS.items():
            if int(row['index']) == index:
                require(int(row['tick']) == len(animations[label]),
                        'Missing or duplicate mechanism animation sample')
                value = float(row['state'])
                require(math.isfinite(value) and 0 <= value <= 1,
                        'Invalid real mechanism animation')
                animations[label].append(value)
    require(all(len(v) == frames+1 for v in animations.values()),
            'Incomplete original mechanism animation traces')
    saved = states(out/'saved.scn')
    for label, values in animations.items():
        require(abs(values[-1]-saved[label][0]) <= .000050001,
                'Saved mechanism and final real animation disagree: '+label)
    evidence = ('flight.scn', 'saved.scn', 'flight-animations.csv',
                'cockpit-state.csv', 'console.log', 'graphics-lifecycle.json')
    evidence += ('systems-case.txt', 'system-inputs.csv', 'Orbiter.log') if args.original else ('replay.csv',)
    report = dict(frames=frames, lifecycle=lifecycle, saved=saved,
                  numerics=json.loads((out/'numerics.json').read_text()),
                  evidence={name: digest(out/name) for name in evidence})
    print('Completed', case['id'], name, frames, 'frames', flush=True)
    return out, saved, animations, report


def restored(animations, saved):
    for label, values in animations.items():
        require(values[0] == saved[label][0],
                'Fresh process failed to restore the original mechanism: '+label)


def run_case(args, case):
    # All seven mechanisms are still moving at this checkpoint. AIRBRAKE has
    # passed its half stop after the second B, so its saved direction means full.
    moving, saved, animations, first = launch(args, case, 'moving', fixture(case), 24, keyboard())
    for label, values in animations.items():
        require(values[0] == 0 and 0 < saved[label][0] < 1 and saved[label][1] > 0,
                'Keyboard failed to start and persist a moving mechanism: '+label)
        require(all(a <= b for a, b in zip(values, values[1:])),
                'Deployment moved backwards: '+label)
    opened, full, animations, second = launch(args, case, 'resume',
                                             (moving/'saved.scn').read_text(), 216, [])
    restored(animations, saved)
    for label, values in animations.items():
        require(full[label] == (1., 0.) and values[-1] == 1. and
                any(saved[label][0] < v < 1 for v in values),
                'Saved motion did not resume and finish without more input: '+label)
        require(all(a <= b for a, b in zip(values, values[1:])),
                'Restored deployment moved backwards: '+label)
    closed, defaults, animations, third = launch(args, case, 'retract',
                                                 (opened/'saved.scn').read_text(), 240, keyboard(True))
    restored(animations, full)
    for label, values in animations.items():
        require(defaults[label] == (0., 0.) and values[-1] == 0 and
                any(0 < v < 1 for v in values), 'Keyboard failed to close mechanism: '+label)
        require(all(a >= b for a, b in zip(values, values[1:])),
                'Retraction moved forwards: '+label)
    _, final, animations, fourth = launch(args, case, 'closed-reload',
                                          (closed/'saved.scn').read_text(), 4, [])
    restored(animations, defaults)
    require(final == defaults and all(all(v == 0 for v in values) for values in animations.values()),
            'Omitted closed scenario defaults did not survive a fresh process')
    return dict(vessel=case['class'], cockpit=case['cockpit'], mechanisms=list(ANIMATIONS),
                moving=first, resume=second, retract=third, closed_reload=fourth)


def compare(original, native):
    from behavior_suite import distance, quaternion, quaternion_angle
    settings = json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    budgets = settings['budgets']
    reports = [json.loads((p/'systems-report.json').read_text()) for p in (original, native)]
    require(all(r['status'] == 'passed' and not r['failures'] for r in reports),
            'Failed systems capture cannot be compared')
    require(reports[0].get('producer') == 'preserved-original-windows' and
            reports[0].get('application_source') == 'f725194209634f7fd5d1d44d426cfa9b5e303e37' and
            reports[1].get('producer') == 'native', 'Wrong original/native systems capture identity')
    expected = {c['id'] for c in settings['cases'] if c.get('class') in ('DeltaGlider', 'DG-S')}
    require(all(set(r['cases']) == expected for r in reports), 'Incomplete systems capture cases')
    results = {}
    for case in sorted(expected):
        result = {}
        for name in ('moving', 'resume', 'retract', 'closed-reload'):
            a, b = (directory/case/name for directory in (original, native))
            for directory, report in zip((a, b), reports):
                phase = 'closed_reload' if name == 'closed-reload' else name
                for filename, checksum in report['cases'][case][phase]['evidence'].items():
                    require(digest(directory/filename) == checksum, 'Systems evidence changed: '+str(directory/filename))
            require(states(a/'saved.scn') == states(b/'saved.scn'), 'Original saved mechanisms differ: '+case+'/'+name)
            left = [r for r in rows(a/'flight-animations.csv') if r['object'] == 'DG' and int(r['index']) in ANIMATIONS.values()]
            right = [r for r in rows(b/'flight-animations.csv') if r['object'] == 'DG' and int(r['index']) in ANIMATIONS.values()]
            # Each producer writes its own handle order. Compare by tick/handle.
            animation = lambda data: {(int(r['tick']), int(r['index'])): float(r['state']) for r in data}
            require(animation(left) == animation(right), 'Original mechanism animation trajectory differs: '+case+'/'+name)
            left, right = rows(a/'cockpit-state.csv'), rows(b/'cockpit-state.csv')
            require(len(left) == len(right), 'Original/native systems state sample count differs')
            maxima = dict(position_m=0., velocity_m_s=0., rotation_rad=0., angular_velocity_rad_s=0., mjd_days=0., propellant_fraction=0.)
            for x, y in zip(left, right):
                for key in ('tick', 'seconds', 'object', 'class', 'cockpit', 'hud', 'meshes', 'thrusters'):
                    require(x[key] == y[key], 'Original systems discrete state differs: '+key)
                vector = lambda row, keys: [float(row[k]) for k in keys]
                errors = dict(position_m=distance(vector(x, ('x','y','z')), vector(y, ('x','y','z'))),
                    velocity_m_s=distance(vector(x, ('vx','vy','vz')), vector(y, ('vx','vy','vz'))),
                    rotation_rad=quaternion_angle(quaternion(x), quaternion(y)),
                    angular_velocity_rad_s=distance(vector(x, ('wx','wy','wz')), vector(y, ('wx','wy','wz'))),
                    mjd_days=abs(float(x['mjd'])-float(y['mjd'])))
                for key, value in errors.items():
                    require(math.isfinite(value) and value <= budgets[key], 'Original systems physical-state budget exceeded: '+case+'/'+name+'/'+key)
                    maxima[key] = max(maxima[key], value)
                for key in ('mass', 'fuel'):
                    ratio = abs(float(x[key])-float(y[key]))/max(budgets['propellant_absolute_kg'], abs(float(x[key]))*budgets['propellant_relative'])
                    require(math.isfinite(ratio) and ratio <= 1, 'Original systems mass/propellant budget exceeded')
                    maxima['propellant_fraction'] = max(maxima['propellant_fraction'], ratio)
            original_math = json.loads((a/'numerics.json').read_text())['math'].split('-')[-1]
            require(json.loads((b/'numerics.json').read_text())['math'].endswith('-'+original_math),
                    'Original/native systems CPU math profiles differ')
            result[name] = dict(exact_mechanism_trajectories=True, exact_saved_position_and_speed=True, maxima=maxima)
        results[case] = result
    return dict(status='passed', cases=results)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'compare':
        parser = argparse.ArgumentParser(description='Compare preserved original and native DG systems with unchanged cockpit budgets')
        for name in ('original', 'native', 'output'):
            parser.add_argument('--'+name, type=Path, required=True)
        args = parser.parse_args(sys.argv[2:])
        report = compare(args.original, args.native)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'planets', 'output'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve(), required=True)
    for name in ('build', 'assets', 'executable', 'mesa'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve())
    parser.add_argument('--original', action='store_true')
    parser.add_argument('--case', action='append', choices=('dg_panel', 'dg_vc', 'dgs_panel', 'dgs_vc'))
    args = parser.parse_args()
    require(args.executable and args.mesa if args.original else args.build and args.assets,
            'Original mode requires --executable/--mesa; native mode requires --build/--assets')
    args.output.mkdir(parents=True, exist_ok=False)
    settings = json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    report = dict(status='pending', scope='Buffered keyboard, animated mechanisms and original scenario persistence',
                  producer='preserved-original-windows' if args.original else 'native',
                  cases={}, failures={}, source=subprocess.check_output(
                      ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
    if args.original:
        report['application_source'] = json.loads((args.executable.parent/'test-runtime.json').read_text())['source_commit']
        report['observer_sha256'] = digest(args.executable.parent/'Modules/Plugin/ProductionCockpitDriver.dll')
    for case in settings['cases']:
        if case.get('class') not in ('DeltaGlider', 'DG-S') or (args.case and case['id'] not in args.case):
            continue
        try:
            report['cases'][case['id']] = run_case(args, case)
        except Exception as error:
            report['failures'][case['id']] = str(error)
            print('Failed', case['id'], error, flush=True)
    report['status'] = 'failed' if report['failures'] else 'passed'
    (args.output/'systems-report.json').write_text(json.dumps(report, indent=2)+'\n')
    require(report['cases'] and not report['failures'], 'Native DG systems/persistence gate failed')


if __name__ == '__main__':
    main()
