#!/usr/bin/env python3
"""Observe Shuttle-A keys and persistence without reducing the stock scene."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE.parent.parent/'StockVessels'), str(HERE.parent.parent/'Cockpit'),
                str(HERE.parent.parent), str(HERE.parent.parent/'Client')]
from original import loaded_modules, source_digest
from inventory import ships
from mesa_runtime import require, digest
from stage import run as stage
from run_client import mesa_files, png
from compare_client import image_ssim
from original import rows

TRACE_FILES = ('stock-vessel-state.csv', 'stock-vessel-docks.csv',
               'stock-vessel-attachments.csv', 'shuttle-a-cockpit.csv', 'shuttle-a-animations.csv')
ERRORS = ('Lua error:', 'LuaCall (', 'runtime error:', 'ERROR: AddressSanitizer',
          'ERROR: LeakSanitizer', 'LeakSanitizer has encountered', 'AddressSanitizer:DEADLYSIGNAL',
          'Could not find a module', 'Orbiter native production:')


def settings():
    value = json.loads((HERE/'cases.json').read_text())
    stock = json.loads((HERE.parent/'cases.json').read_text())
    case = next(c for c in stock['cases'] if c['scenario'] == value['scenario'])
    require(value['application_source'] == stock['application_source'] and
            value['sha256_lf'] == case['sha256_lf'] and value['fixed_step'] == stock['fixed_step'],
            'Controls fixture differs from preserved original source/clock')
    path = ROOT/'Scenarios'/value['scenario']
    original = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                       value['application_source']+':Scenarios/'+value['scenario']])
    require(source_digest(path) == value['sha256_lf'] and
            original.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n'),
            'Complete stock controls scenario changed')
    value['budgets'] = stock['budgets']
    value['image_ssim_minimum'] = stock['image_ssim_minimum']
    return value


def actions(config, case, phase):
    commands = []
    if phase == 'moving' and case['cockpit'] == 3:
        commands.append((0, 'pre', 'key', 66))  # Ordinary F8, from unchanged panel scenario.
        commands.append((1, 'pre', 'key', -66))
    if phase in ('moving', 'retract'):
        for tick, key, control in config['keys']:
            if control:
                commands.append((tick, 'pre', 'key', 29))
            commands.extend(((tick, 'pre', 'key', key), (tick+1, 'pre', 'key', -key)))
            if control:
                commands.append((tick+1, 'pre', 'key', -29))
    return sorted(commands, key=lambda c: c[0])


def dispatches(commands):
    # The native pre-step tape queues keys for the next input boundary.
    control = False
    result = []
    for tick, phase, action, key in commands:
        require(phase == 'pre' and action == 'key', 'Unexpected controls action')
        if abs(key) == 29:
            control = key > 0
        elif key > 0:
            result.append((tick+1, key, int(control)))
    return result


def saved_state(path, config):
    result = dict.fromkeys(config['animations'], (0, 0.))
    found = inside = False
    present = set()
    for raw in path.read_bytes().decode('cp1252').splitlines():
        line = raw.strip()
        if line.startswith(config['focus']+':'):
            require(not found, 'Duplicate saved focus vessel')
            found = inside = True
        elif line == 'END':
            inside = False
        elif inside and (parts := line.split()) and parts[0] in result:
            require(len(parts) == 3 and parts[0] not in present, 'Malformed saved mechanism')
            present.add(parts[0])
            state, position = int(parts[1]), float(parts[2])
            require(0 <= state <= 3 and math.isfinite(position) and 0 <= position <= 1,
                    'Invalid saved mechanism state')
            result[parts[0]] = (state, position)
    require(found and {'DOCKSTATE', 'GEAR'} <= present, 'Incomplete saved Shuttle-A state')
    return result


def manifest(source):
    return {name: kind.lower() for name, kind in ships(source.decode('cp1252')).items()}


def inspect(out, config, case, phase, source):
    total = config['phases'][phase]
    expected = manifest(source)
    require(expected == manifest((out/'flight.scn').read_bytes()) ==
            manifest((out/'saved.scn').read_bytes()), 'Complete controls vessel graph changed')
    state = rows(out/'stock-vessel-state.csv')
    groups = {}
    for row in state:
        require(all(math.isfinite(float(v)) for k, v in row.items() if k not in ('object', 'class')),
                'Nonfinite all-vessel controls state')
        groups.setdefault(int(row['tick']), []).append(row)
    require(set(groups) == set(range(total+1)), 'Missing finalized controls ticks')
    initial_mjd = float(groups[0][0]['mjd'])
    for tick, group in groups.items():
        require(len(group) == len(expected) and {r['object']: r['class'].lower() for r in group} == expected,
                'Background vessel missing or substituted in controls observation')
        require(all(float(r['seconds']) == tick*config['fixed_step'] and
                    abs(float(r['mjd'])-initial_mjd-tick*config['fixed_step']/86400) <= config['budgets']['mjd_days']
                    for r in group), 'Controls fixed clock differs')
        require([r['object'] for r in group if r['focus'] == '1'] == [config['focus']], 'Controls focus changed')
        require(all(float(r['mass']) > 0 and float(r['empty_mass']) > 0 and float(r['fuel']) >= 0 for r in group),
                'Invalid controls vessel mass')
    for filename, count_key, peer in (('stock-vessel-docks.csv', 'docks', 'docked'),
                                      ('stock-vessel-attachments.csv', None, 'attached')):
        data = rows(out/filename)
        key = lambda r: (int(r['tick']), r['object'], int(r['index'])) if count_key else (
            int(r['tick']), r['object'], int(r['parent']), int(r['index']))
        expected_keys = {(int(r['tick']), r['object'], i) for r in state for i in range(int(r['docks']))} if count_key else {
            (int(r['tick']), r['object'], parent, i) for r in state for parent, field in ((0, 'children'), (1, 'parents'))
            for i in range(int(r[field]))}
        require(len(data) == len(expected_keys) and {key(r) for r in data} == expected_keys,
                'Incomplete or duplicate controls ports: '+filename)
        for row in data:
            require(row[peer] == '' or row[peer] in expected, 'Unknown controls attachment/dock peer')
            require(all(math.isfinite(float(v)) for k, v in row.items() if k not in ('object', peer, 'id')),
                    'Nonfinite controls port')
    cockpit = rows(out/'shuttle-a-cockpit.csv')
    require(len(cockpit) == total+1 and [int(r['tick']) for r in cockpit] == list(range(total+1)),
            'Incomplete controls cockpit trace')
    for row in cockpit:
        mode = 2 if phase == 'moving' and case['cockpit'] == 3 and int(row['tick']) < 2 else case['cockpit']
        require(row['object'] == config['focus'] and row['class'].lower() == 'shuttlea' and int(row['cockpit']) == mode,
                'Ordinary cockpit selection failed')
    animation_rows = rows(out/'shuttle-a-animations.csv')
    animations = {(int(r['tick']), int(r['index'])): float(r['state']) for r in animation_rows}
    require(len(animation_rows) == len(animations) == (total+1)*6 and
            set(animations) == {(t, i) for t in range(total+1) for i in range(6)} and
            all(r['object'] == config['focus'] for r in animation_rows) and
            all(math.isfinite(v) and 0 <= v <= 1 for v in animations.values()), 'Incomplete mechanism trajectories')
    require(all(animations[t, i] == 0 for t in range(total+1) for i in (0, 1)),
            'Uncommanded engine pod changed')
    saved = saved_state(out/'saved.scn', config)
    for label, index in config['animations'].items():
        require(abs(animations[total, index]-saved[label][1]) <= .000050001,
                'Saved position differs from real mechanism: '+label)
    life = json.loads((out/'graphics-lifecycle.json').read_text())
    require(life == dict(rendered_frames=total, successful_presents=total, context_deleted=True),
            'Incomplete controls rendering/teardown')
    renderer = json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width'] == 1280 and renderer['client_height'] == 720,
            'Controls comparison renderer/viewport differs')
    errors = out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(), 'Controls graphics error')
    log = (out/'console.log').read_text(errors='replace')
    if (out/'Orbiter.log').exists():
        log += (out/'Orbiter.log').read_text(errors='replace')
    for marker in ERRORS:
        require(marker not in log, 'Controls runtime error: '+marker)
    if phase in ('resume', 'retract'):
        require(len((out/'scene.rgba').read_bytes()) == 1280*720*4 and
                set(expected) <= {r['object'] for r in rows(out/'scene.csv') if r['type'] == 'vessel'},
                'Complete controls scene capture missing')
    return saved, animations, dict(finalized_all_vessel_rows=len(state), lifecycle=life, renderer=renderer,
                                    saved={k: list(v) for k, v in saved.items()}, input_sha256=digest(out/'flight.scn'))


def build_probe(build, output, sanitized=False):
    compiler = next(line.split('=', 1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                    if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    path = output/'shuttle-a-controls-probe.so'
    flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if sanitized else []
    subprocess.run([compiler, '-std=c++17', '-fPIC', '-shared', '-Wl,--no-undefined', *flags,
                    '-I'+str(ROOT/'Orbitersdk/include'), '-I'+str(ROOT/'Src/Orbiter'), str(HERE/'NativeProbe.cpp'),
                    '-L'+str(build), '-lorbiter_production_vessels', '-lorbiter_production_boundary', '-ldl', '-o', str(path)],
                   check=True)
    return path


def launch(args, config, case, repeat, phase, source, probe, expected_modules):
    out = args.output/(case['id']+'-'+str(repeat))/phase
    out.parent.mkdir(parents=True, exist_ok=True)
    total = config['phases'][phase]
    commands = actions(config, case, phase)
    expected = dispatches(commands)
    if args.original:
        def configure(directory):
            cfg = directory/'Orbiter.cfg'
            cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver', '  ProductionCockpitDriver\n  OGLClient')+
                           '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
            (directory/'Scenarios/Behavior.scn').write_bytes(source)
            (directory/'flight.scn').write_bytes(source)
            (directory/'shuttle-a-controls.txt').write_text(f'{total} {len(expected)}\n'+
                ''.join(f'{t} {key} {control}\n' for t, key, control in expected))
            (directory/'ogl-evidence.enabled').touch()
            mesa_files(args.mesa, directory)
        stage(args.executable, args.data, args.planets, out,
              dict(frames=total, fixed_step=config['fixed_step']), configure)
        failure = out/'shuttle-a-failure.txt'
        require(not failure.exists(), 'Original controls observer failed: '+(failure.read_text() if failure.exists() else ''))
        require((out/'shuttle-a-complete.txt').read_text().strip() == str(total), 'Original controls shutdown incomplete')
        require([(int(r['tick']), int(r['key']), int(r['control'])) for r in rows(out/'shuttle-a-inputs.csv')] == expected,
                'Original dispatched key schedule differs')
        shutil.copyfile(out/'Scenarios/ShuttleAControlsResult.scn', out/'saved.scn')
        shutil.copyfile(out/'console.txt', out/'console.log')
        actual_math = (out/'math-profile.txt').read_text().strip()
        require(actual_math in ('fma3', 'sse2') and (args.math_profile != 'sse2' or actual_math == 'sse2'),
                'Actual original CRT profile differs')
        modules = loaded_modules(out, expected_modules)
        require({'shuttlea.dll', 'deltaglider.dll'} <= {Path(m['path']).name.lower() for m in modules},
                'Original stock vessel DLL was not loaded')
    else:
        out.mkdir()
        (out/'flight.scn').write_bytes(source)
        (out/'Orbiter.cfg').write_text((HERE.parent.parent/'NativeScene/Orbiter.cfg').read_text()+
            '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
        (out/'replay.csv').write_text('tick,phase,action,value\n'+''.join(
            ','.join(map(str, c))+'\n' for c in [*commands, (total-1, 'after', 'save', 0)]))
        command = [str(args.executable), '--config', str(out/'Orbiter.cfg'), '--scenario', str(out/'flight.scn'),
                   '--save', str(out/'saved.scn'), '--evidence', str(out), '--replay', str(out/'replay.csv'),
                   '--frames', str(total), '--fixed-step', str(config['fixed_step']), '--capture-time', '12.5', '--run']
        for name in ('assets', 'data', 'planets'):
            command += ['--'+name, str(getattr(args, name))]
        command += ['--modules', str(args.executable.parent/'NativeModules')]
        (out/'invocation.json').write_text(json.dumps(command, indent=2)+'\n')
        environment = dict(os.environ)
        # Preserve an explicit sanitizer preload before this read-only observer.
        environment['LD_PRELOAD'] = ':'.join(filter(None, (
            str(args.sanitizer_runtime) if args.sanitizer_runtime else None, environment.get('LD_PRELOAD'), str(probe))))
        with (out/'console.log').open('w') as log:
            subprocess.run(command, cwd=out, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240)
        actual_math = json.loads((out/'numerics.json').read_text())['math']
        require(actual_math == 'amd-6121d02-'+('sse2' if args.math_profile == 'sse2' else 'fma3'),
                'Actual native math profile differs')
        modules = None
    require((out/'flight.scn').read_bytes() == source, 'Controls scenario bytes changed while running')
    saved, animations, report = inspect(out, config, case, phase, source)
    report.update(actual_math=actual_math, loaded_modules=modules)
    if phase in ('resume', 'retract'):
        png(out/'scene.png', (out/'scene.rgba').read_bytes(), 1280, 720)
    filenames = [*TRACE_FILES, 'flight.scn', 'saved.scn', 'console.log', 'graphics-lifecycle.json',
                 'renderer-info.json', 'renderer-modules.txt', 'invocation.json', 'Orbiter.cfg']
    if args.original:
        filenames += ['shuttle-a-controls.txt', 'shuttle-a-inputs.csv', 'shuttle-a-complete.txt',
                      'math-profile.txt', 'mesa-bindings.json', 'Orbiter.log', 'Scenarios/Behavior.scn']
    else:
        filenames += ['replay.csv', 'numerics.json']
    if phase in ('resume', 'retract'):
        filenames += ['scene.rgba', 'scene.csv', 'camera.csv']
    report['files_sha256'] = {name: digest(out/name) for name in filenames}
    print(case['id'], repeat, phase, 'captured', total, 'presents', flush=True)
    return out, saved, animations, report


def run_case(args, config, case, repeat, probe, expected_modules):
    source = (ROOT/'Scenarios'/config['scenario']).read_bytes()
    previous = None
    initial = {label: (1, 1.) if label == 'DOCKSTATE' else (0, 0.) for label in config['animations']}
    result = {}
    for phase in config['phases']:
        out, saved, animations, report = launch(args, config, case, repeat, phase, source, probe, expected_modules)
        for label, index in config['animations'].items():
            require(animations[0, index] == (previous or initial)[label][1], 'Saved mechanism was not restored: '+label)
            values = [animations[t, index] for t in range(config['phases'][phase]+1)]
            if phase == 'moving':
                require(saved[label][0] == (2 if label == 'DOCKSTATE' else 3) and 0 < saved[label][1] < 1,
                        'Ordinary keyboard failed to save moving mechanism: '+label)
            elif phase == 'resume':
                require(saved[label] == ((0, 0.) if label == 'DOCKSTATE' else (1, 1.)) and
                        any(0 < v < 1 for v in values), 'Saved motion failed to resume without input: '+label)
            else:
                require(saved[label] == initial[label], 'Mechanism failed to return to original state: '+label)
                if phase == 'retract':
                    require(any(0 < v < 1 for v in values), 'Retraction skipped mechanism motion: '+label)
                else:
                    require(all(v == initial[label][1] for v in values), 'Restored endpoint moved without input: '+label)
            increasing = (label != 'DOCKSTATE') == (phase in ('moving', 'resume'))
            require(all(a <= b if increasing else a >= b for a, b in zip(values, values[1:])),
                    'Mechanism reversed its commanded motion: '+label)
        result[phase] = report
        previous = saved
        source = (out/'saved.scn').read_bytes()
    return result


def capture(args):
    config = settings()
    require(not args.output.exists(), 'Controls output exists; replacement is forbidden')
    if args.original:
        require(sys.platform == 'win32', 'Original capture requires native Windows')
        require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2') == '1') == (args.math_profile == 'sse2'),
                'Original requested CRT profile differs from environment')
        os.environ.update(LIBGL_ALWAYS_SOFTWARE='true', GALLIUM_DRIVER='llvmpipe')
        runtime = json.loads((args.executable.parent/'test-runtime.json').read_text())
        client = json.loads((args.executable.parent/'control-reference-runtime.json').read_text())
        require(runtime['source_commit'] == client['application_source'] == config['application_source'],
                'Wrong preserved original application/SDK/client source')
        binaries = {name: args.executable.parent/name for name in {**runtime['files'], **client['client_files_sha256']}}
        binaries['Modules/Plugin/ProductionCockpitDriver.dll'] = args.executable.parent/'Modules/Plugin/ProductionCockpitDriver.dll'
        for name, checksum in {**runtime['files'], **client['client_files_sha256']}.items():
            if name != 'Modules/Plugin/ProductionCockpitDriver.dll':
                require(digest(binaries[name]) == checksum, 'Preserved original binary changed: '+name)
        expected_modules = {}
        for name, path in binaries.items():
            expected_modules.setdefault(Path(name).name.casefold(), set()).add(digest(path))
    else:
        require(args.assets and args.runtime_source_commit, 'Native capture requires assets and runtime source identity')
        require((args.assets/'Scenarios'/config['scenario']).read_bytes() == (ROOT/'Scenarios'/config['scenario']).read_bytes(),
                'Native staged stock scenario differs')
        runtime = client = None
        expected_modules = None
        binaries = {p.relative_to(args.executable.parent).as_posix(): p
                    for p in [args.executable, *sorted(args.executable.parent.rglob('*.so'))]}
    binary_hashes = {name: digest(path) for name, path in binaries.items()}
    sources = [HERE/name for name in ('cases.json', 'Driver.cpp', 'Observation.h', 'NativeProbe.cpp',
                                      'CMakeLists.txt', 'capture.py', 'compare.py')] + [HERE.parent/'cases.json',
        HERE.parent.parent/'StockVessels/Observation.h', HERE.parent.parent/'StockVessels/original.py',
        HERE.parent.parent/'StockVessels/verify_original.py', HERE.parent.parent/'NativeScene/Orbiter.cfg']
    source_hashes = {p.relative_to(ROOT).as_posix(): source_digest(p) for p in sources}
    args.output.mkdir(parents=True)
    report = dict(status='running', phase6_complete=False, producer='preserved-original-windows' if args.original else 'native',
        configuration=args.configuration, math_profile=args.math_profile, application_source=config['application_source'],
        runtime_source_commit=args.runtime_source_commit, runtime=runtime, client=client,
        producer_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        source_sha256_lf=source_hashes, binary_sha256=binary_hashes, cases={}, failures={})
    if args.sanitizer_runtime:
        report['sanitizer_runtime_sha256'] = digest(args.sanitizer_runtime)
    path = args.output/'controls-report.json'
    def save():
        path.write_text(json.dumps(report, indent=2)+'\n')
    save()
    probe = None if args.original else build_probe(args.executable.parent, args.output, bool(args.sanitizer_runtime))
    if probe:
        report['probe_sha256'] = digest(probe)
    for case in config['cases']:
        try:
            repeats = [run_case(args, config, case, repeat, probe, expected_modules) for repeat in (1, 2)]
            comparisons = {}
            for phase in config['phases']:
                paths = [args.output/(case['id']+'-'+str(repeat))/phase for repeat in (1, 2)]
                for name in TRACE_FILES:
                    require((paths[0]/name).read_bytes() == (paths[1]/name).read_bytes(),
                            'Controls deterministic repeat differs: '+case['id']+'/'+phase+'/'+name)
                if phase in ('resume', 'retract'):
                    similarity = image_ssim(*[(p/'scene.rgba').read_bytes() for p in paths], 1280, 720)
                    require(similarity >= config['image_ssim_minimum'], 'Repeated controls frame exceeds unchanged SSIM budget')
                    comparisons[phase] = similarity
            report['cases'][case['id']] = dict(runs=repeats, repeat_ssim=comparisons)
        except Exception as error:
            report['failures'][case['id']] = str(error)
            print(case['id'], 'failed:', error, flush=True)
        save()
    require(binary_hashes == {name: digest(p) for name, p in binaries.items()} and
            source_hashes == {p.relative_to(ROOT).as_posix(): source_digest(p) for p in sources},
            'Controls sources or runtime changed during capture')
    report['status'] = 'passed' if not report['failures'] and len(report['cases']) == len(config['cases']) else 'failed'
    report['sources_and_runtime_unchanged'] = True
    save()
    require(report['status'] == 'passed', 'Shuttle-A controls capture is incomplete')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-inputs', action='store_true')
    parser.add_argument('--original', action='store_true')
    for name in ('executable', 'data', 'planets', 'mesa', 'assets', 'output'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve())
    parser.add_argument('--configuration', choices=('Debug', 'Release'))
    parser.add_argument('--math-profile', choices=('automatic', 'sse2'))
    parser.add_argument('--runtime-source-commit')
    parser.add_argument('--sanitizer-runtime', type=lambda p: Path(p).resolve(),
                        help='Preload this ASan runtime in the native application before the instrumented observer')
    args = parser.parse_args()
    if args.verify_inputs:
        config = settings()
        print('Verified complete', len(manifest((ROOT/'Scenarios'/config['scenario']).read_bytes())),
              'vessel fixture against preserved original', config['application_source'])
        return
    require(all(getattr(args, name) for name in ('executable', 'data', 'planets', 'output', 'configuration', 'math_profile')),
            'Missing controls capture arguments')
    require(args.mesa if args.original else args.assets, 'Original requires Mesa; native requires assets')
    require(not args.sanitizer_runtime or (not args.original and args.sanitizer_runtime.is_file()),
            'Sanitizer runtime must name a native ASan library')
    capture(args)


if __name__ == '__main__':
    main()
