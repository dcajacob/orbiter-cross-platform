#!/usr/bin/env python3
"""Exercise real tank ownership and deletion in the unqualified native test host."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'Tests/Production/StockScenarios'),
               str(ROOT/'Tests/Production/WaylandInput'), str(ROOT/'Tests/Production/Client')]
from compositor import Compositor
from intentional_exit import build_identity, environment as probe_environment
from run_client import png

TOUR = '2024 Edition/3 Minute Tour of Kennedy Space Center.scn'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_lf(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def control(radius):
    # Supplemental lifecycle controls, never replacements for stock scenarios.
    return f'''BEGIN_ENVIRONMENT
  System Sol
  Date MJD 51982.5
END_ENVIRONMENT
BEGIN_FOCUS
  Ship Observer
END_FOCUS
BEGIN_CAMERA
  TARGET Observer
  MODE Extern
  POS 3 0 0
  TRACKMODE TargetRelative
  FOV 50
END_CAMERA
BEGIN_SHIPS
Observer:ShuttlePB
  STATUS Orbiting Earth
  RPOS 7000000 0 0
  RVEL 0 0 7500
  AROT 0 0 0
  FUEL 1.0
END
ControlTank:Atlantis_Tank
  STATUS Orbiting Earth
  RPOS {radius} 0 0
  RVEL 0 0 465
  AROT 0 0 0
  PRPLEVEL 0:1.0
END
END_SHIPS
'''


def compile_probe(build, output):
    source = Path(__file__).with_name('TankPostStepProbe.cpp')
    commands = json.loads((build/'compile_commands.json').read_text())
    command = next(item for item in commands if item['file'].endswith('/Atlantis_Tank.cpp'))
    argv = list(command['arguments']) if 'arguments' in command else shlex.split(command['command'])
    # Use the actual tank compiler, includes, ABI and sanitizer flags.
    index = argv.index('-o')
    del argv[index:index+2]
    index = argv.index('-c')
    del argv[index:index+2]
    probe = output/'tank-post-step-probe.so'
    argv += ['-shared', str(source), '-L'+str(build), '-Wl,-rpath,'+str(build),
             '-lorbiter_production_vessels',
             '-lorbiter_production_boundary', '-Wl,--no-undefined', '-ldl', '-o', str(probe)]
    (output/'probe-command.json').write_text(json.dumps(argv, indent=2)+'\n')
    with (output/'probe-build.log').open('w') as log:
        subprocess.run(argv, cwd=command['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
    return probe


def inspect(folder, kind, returncode):
    require(returncode == 0, 'Actual native process failed: '+str(returncode))
    text = (folder/'console.log').read_text(errors='replace')
    markers = ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
               'AddressSanitizer:DEADLYSIGNAL', 'Orbiter native production:', 'Lua error:')
    require(not any(marker in text for marker in markers), 'Native diagnostic reported an error')
    marker = json.loads((folder/'unqualified-atlantis-diagnostic.json').read_text())
    require(marker['native_admission_qualified'] is False and marker['phase6_complete'] is False,
            'Unqualified test-host marker missing')
    life = json.loads((folder/'graphics-lifecycle.json').read_text())
    require(life == dict(rendered_frames=60, successful_presents=60, context_deleted=True),
            'Incomplete real presentation or graphics teardown')
    with (folder/'flight-state.csv').open(newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    groups = {}
    strings = {'object', 'class', 'dock', 'focus', 'attached'}
    for row in rows:
        require(None not in row and None not in row.values(), 'Incomplete finalized state row')
        require(all(math.isfinite(float(value)) for key, value in row.items() if key not in strings),
                'Nonfinite actual vessel state')
        require(float(row['fuel']) >= 0 and float(row['mass']) > 0, 'Invalid actual fuel or mass')
        require(float(row['seconds']) == int(row['tick'])*.25, 'Actual fixed-step clock changed')
        group = groups.setdefault(int(row['tick']), {})
        require(row['object'] not in group, 'Duplicate vessel at a finalized tick')
        group[row['object']] = row
    require(set(groups) == set(range(61)), 'Incomplete finalized all-vessel ticks')
    with (folder/'tank-post-step.csv').open(newline='') as stream:
        callbacks = list(csv.DictReader(stream))
    require(callbacks and all(None not in row and None not in row.values() for row in callbacks),
            'Original tank callbacks were not observed')
    require(all(math.isfinite(float(row[key])) for row in callbacks for key in ('seconds', 'altitude_mean')),
            'Nonfinite actual tank callback input')
    below_connected = 0
    if kind == 'stock-tour':
        initial = {name: row['class'] for name, row in groups[0].items()}
        require(initial == {'GL-01S': 'DG-S', 'STS-101': 'Atlantis',
                            'STS-101_ET': 'Atlantis_Tank',
                            'STS-101-SRB1': 'Atlantis_SRB', 'STS-101-SRB2': 'Atlantis_SRB'},
                'Complete unchanged stock tour population differs')
        for group in groups.values():
            require({name: row['class'] for name, row in group.items()} == initial,
                    'A live stock launch-stack vessel disappeared')
            tank = group['STS-101_ET']
            require(tank['dock'] == 'STS-101', 'External tank lost its live orbiter connection')
        require(len(callbacks) == 60 and all(row['object'] == 'STS-101_ET' and
                row['orbiter'] == 'STS-101' for row in callbacks), 'Original tank callback sequence differs')
        require([float(row['seconds']) for row in callbacks] == [tick*.25 for tick in range(1, 61)],
                'Connected tank callback clock differs')
        below_connected = sum(float(row['altitude_mean']) < 0 for row in callbacks)
        require(below_connected > 0, 'Regression never exercised a connected below-ground tank')
    else:
        first = groups[0]['ControlTank']
        require(first['class'] == 'Atlantis_Tank' and first['dock'] == '',
                'Supplemental control does not start with a real undocked tank')
        below = kind == 'detached-below'
        require(all(row['object'] == 'ControlTank' and row['orbiter'] == '' for row in callbacks),
                'Actual control callback has a different vessel or connection')
        require(len(callbacks) == (1 if below else 60), 'Detached tank callback count differs')
        require([float(row['seconds']) for row in callbacks] ==
                [tick*.25 for tick in range(1, 2 if below else 61)], 'Detached tank callback clock differs')
        require(all((float(row['altitude_mean']) < 0) == below for row in callbacks),
                'Actual post-step control altitude has the wrong sign')
        for tick, group in groups.items():
            expected = {'Observer'} if below and tick else {'Observer', 'ControlTank'}
            require(set(group) == expected, 'Detached tank lifetime differs at tick '+str(tick))
            if 'ControlTank' in group:
                require(group['ControlTank']['dock'] == '', 'Control tank unexpectedly docked')
    rgba = folder/'scene.rgba'
    require(rgba.stat().st_size == 1280*720*4, 'Real captured framebuffer missing')
    png(folder/'scene.png', rgba.read_bytes(), 1280, 720)
    return dict(status='passed', returncode=returncode, lifecycle=life,
                finalized_ticks=len(groups), all_vessel_rows=len(rows),
                connected_below_ground_samples=below_connected, original_tank_callbacks=len(callbacks))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'build-record', 'assets', 'data', 'planets', 'compositor-tools', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--library', type=Path, action='append', default=[])
    a = p.parse_args()
    for name in ('build', 'build_record', 'assets', 'data', 'planets', 'compositor_tools', 'output'):
        setattr(a, name, getattr(a, name).resolve())
    record = json.loads(a.build_record.read_text())
    identity = build_identity(a.build/'orbiter-production', a.build/'NativeModules',
                              a.build_record, record['source_base'])
    require(identity['sanitizer_linked'], 'Fully enabled ASan/UBSan runtime required')
    candidate = a.build/'production_atlantis_diagnostic'
    require(record['candidate_runtime_files_sha256'][candidate.relative_to(ROOT).as_posix()] == digest(candidate),
            'Diagnostic executable differs from fresh build record')
    guarded = {**record['source_sha256_lf'], **record['dependency_sha256_lf']}
    require(all(digest_lf(ROOT/name) == value for name, value in guarded.items()), 'Owning input changed')
    resources = json.loads((a.assets/'remaining-vessels-resources.json').read_text())['staged_files_sha256']
    require(all(digest(a.assets/name) == value for name, value in resources.items()), 'Staged resource changed')
    require((a.assets/'Scenarios'/TOUR).read_bytes() == (ROOT/'Scenarios'/TOUR).read_bytes(),
            'Complete stock scenario changed')
    protected = {ROOT/name: value for name, value in
                 {**record['runtime_files_sha256'], **record['candidate_runtime_files_sha256']}.items()}
    observer_sources = {Path(__file__).resolve(), Path(__file__).with_name('TankPostStepProbe.cpp').resolve(),
                        ROOT/'Tests/Production/NativeScene/Orbiter.cfg'}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if ROOT in path.parents and path.suffix == '.py':
                observer_sources.add(path)
    observer_commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    for path in observer_sources:
        body = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                        observer_commit+':'+path.relative_to(ROOT).as_posix()])
        require(body == path.read_bytes(), 'Observer differs from immutable producer: '+str(path))
    for path in (a.build_record, Path(__file__), Path(__file__).with_name('TankPostStepProbe.cpp'),
                 a.build/'compile_commands.json', a.assets/'remaining-vessels-resources.json'):
        protected[path] = digest(path)
    protected.update({path: digest(path) for path in observer_sources})
    a.output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', protocol='atlantis-tank-lifetime-v5', runtime_identity=identity,
                  candidate_sha256=digest(candidate), source_inputs=len(guarded), asset_inputs=len(resources),
                  observer_sha256=digest(Path(__file__)), native_admission_qualified=False, phase6_complete=False,
                  observer_commit=observer_commit,
                  observer_source_sha256={path.relative_to(ROOT).as_posix(): digest(path)
                                          for path in sorted(observer_sources)},
                  scope='Real native lifetime regression and supplemental deletion controls; original/native '
                        'state/image parity, stock admission and complete Phase 6 qualification remain pending.',
                  cases={})
    def save():
        (a.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        probe = compile_probe(a.build, a.output)
        protected[probe] = digest(probe)
        report['callback_probe_sha256'] = digest(probe)
        report['callback_probe_source_sha256'] = digest(Path(__file__).with_name('TankPostStepProbe.cpp'))
        report['callback_probe_scope'] = 'Read-only actual post-step inputs; all original arguments forwarded unchanged'
        with Compositor(a.compositor_tools, a.output/'compositor') as display:
            environment = dict(display.environment,
                LD_LIBRARY_PATH=':'.join(map(str, [a.build, *[path.resolve() for path in a.library]])),
                LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe', LP_NUM_THREADS='2',
                ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0', LSAN_OPTIONS='',
                UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            environment['LD_PRELOAD'] = probe_environment(probe, identity)['LD_PRELOAD']
            environment['ORBITER_ATLANTIS_PROBE_LIBRARY'] = str(a.build/'liborbiter_native_atlantis.so')
            for kind, radius in (('stock-tour', None), ('detached-below', 6370000), ('detached-above', 7000000)):
                folder = a.output/kind
                folder.mkdir()
                scenario = a.assets/'Scenarios'/TOUR
                if radius is not None:
                    scenario = folder/'control.scn'
                    scenario.write_text(control(radius))
                config = folder/'Orbiter.cfg'
                config.write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                                  '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                argv = [str(candidate), '--assets', str(a.assets), '--data', str(a.data),
                        '--planets', str(a.planets), '--modules', str(a.build/'NativeModules'),
                        '--scenario', str(scenario), '--config', str(config), '--evidence', str(folder),
                        '--frames', '60', '--fixed-step', '.25', '--capture-time', '12.5', '--run']
                (folder/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
                item = dict(status='running', scenario=str(scenario), scenario_sha256=digest(scenario),
                            supplemental_control=radius is not None)
                report['cases'][kind] = item
                save()
                try:
                    with (folder/'console.log').open('w') as console:
                        process = subprocess.run(argv, cwd=folder, env=environment, stdout=console,
                                                 stderr=subprocess.STDOUT, timeout=180)
                    item.update(inspect(folder, kind, process.returncode))
                except BaseException as error:
                    item.update(status='failed', error=str(error))
                    raise
                finally:
                    item['files_sha256'] = {path.name: digest(path) for path in folder.iterdir() if path.is_file()}
                    save()
                print(json.dumps(dict(case=kind, status=item['status'])), flush=True)
        require(all(digest_lf(ROOT/name) == value for name, value in guarded.items()), 'Owning input changed during test')
        require(all(digest(a.assets/name) == value for name, value in resources.items()), 'Asset changed during test')
        require(all(digest(path) == value for path, value in protected.items()), 'Retained runtime or verifier changed')
        report.update(status='passed', owning_inputs_assets_runtime_and_verifier_unchanged=True)
    except BaseException as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
