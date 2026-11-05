#!/usr/bin/env python3
"""Exercise complete, paused Atlantis worlds through real F5 and normal exit.

No preload observer is used. Original scene bytes seed F5, so this checks
attachment/world lifetime rather than actual-save persistence or flight parity.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[3]
SCENE = Path('Scenarios/Space Shuttle Atlantis/Atlantis ISS Resupply.scn')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', type=Path, default=ROOT,
                        help='Owning source checkout of the selected immutable package')
    for name in ('package', 'assets', 'data', 'planets', 'compositor-tools',
                 'gtk-plugin', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--library', type=Path, action='append', default=[])
    parser.add_argument('--worlds', type=int, choices=range(1, 21), default=20)
    parser.add_argument('--expect-use-after-free', action='store_true',
                        help='Require the original paused-shutdown failure on an old package')
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, name, value.resolve())
    args.library = [path.resolve() for path in args.library]
    require(not args.output.exists(), 'Fresh evidence output required')
    require(args.gtk_plugin.is_file(), 'Explicit decoration plugin missing')
    require(all(path.is_dir() for path in args.library), 'Library directory missing')
    require('LD_PRELOAD' not in os.environ, 'No preload observer is permitted')
    sys.path[:0] = [str(args.owner / 'Tests/Production/WaylandInput'),
                   str(args.owner / 'Tests/Production/StockScenarios')]
    from compositor import Compositor
    from intentional_exit import build_identity
    from inventory import ships

    engine = args.package / 'engine'
    record_path = args.package / 'build.json'
    build = load(record_path)
    identity = build_identity(engine / 'orbiter-production', engine / 'NativeModules',
                              record_path, build['source_base'])
    require(identity['sanitizer_linked'], 'ASan/UBSan package required')
    for name, value in build['dependency_sha256_lf'].items():
        body = (args.owner / name).read_bytes().replace(b'\r\n', b'\n')
        require(hashlib.sha256(body).hexdigest() == value, 'Build dependency changed: ' + name)
    executable = engine / 'production_remaining_stock_diagnostic'
    require(sha(executable) == build['candidate_runtime_files_sha256'][
        executable.relative_to(args.owner).as_posix()], 'Diagnostic executable changed')
    require((args.assets / SCENE).read_bytes() == (args.owner / SCENE).read_bytes(),
            'Complete stock scenario bytes changed')
    expected = ships((args.assets / SCENE).read_text())
    require(expected == {'ISS': 'ProjectAlpha_ISS', 'STS-101': 'Atlantis',
                         'Leonardo': 'Leonardo_mplm'}, 'Complete original ship list differs')
    resources = load(args.assets / 'remaining-vessels-resources.json')['staged_files_sha256']
    require(all(sha(args.assets / name) == value for name, value in resources.items()),
            'Staged resource bytes changed')

    config_path = args.owner / 'Tests/Production/NativeScene/Orbiter.cfg'
    config = config_path.read_text()
    for line in ('PropStages = 1\n', 'PropStage0 = 1 1 1\n', 'PropSubsampling = 1\n'):
        require(config.count(line) == 1, 'Unexpected original fixture propagator settings')
        config = config.replace(line, '')
    args.output.mkdir(parents=True)
    (args.output / 'Orbiter.cfg').write_text(config + '\nMenubarMode = 1\nInfobarMode = 1\n')
    reload_path = args.output / 'original-reload.scn'
    reload_path.write_bytes((args.assets / SCENE).read_bytes())
    for index in range(1, args.worlds + 1):
        folder = args.output if index == 1 else args.output / ('session-' + str(index))
        folder.mkdir(exist_ok=True)
        (folder / 'ui-evidence.enabled').touch()

    guards = {str(args.owner / name): sha(args.owner / name)
              for group in ('source_sha256_lf', 'dependency_sha256_lf')
              for name in build[group]}
    for group in ('runtime_files_sha256', 'candidate_runtime_files_sha256',
                  'generated_source_files_sha256'):
        for name, value in build[group].items():
            require(sha(args.owner / name) == value, 'Package input changed: ' + name)
            guards[str(args.owner / name)] = value
    for path in (Path(__file__), record_path, args.assets / SCENE, config_path,
                 args.output / 'Orbiter.cfg', reload_path, args.gtk_plugin,
                 args.assets / 'remaining-vessels-resources.json'):
        guards[str(path)] = sha(path)
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if args.owner in path.parents and path.suffix == '.py':
                guards[str(path)] = sha(path)
    report = dict(status='running', started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  scope=__doc__, runtime_identity=identity, actual_executable=str(executable),
                  actual_executable_sha256=sha(executable), original_objects=expected,
                  requested_worlds=args.worlds, expected_baseline_use_after_free=args.expect_use_after_free,
                  guarded_files_sha256=guards, resource_files_sha256=resources,
                  worlds_observed_ready=0, physical_keys=[], no_preload_observer=True,
                  cloud_builds_used=False, raw_evidence_uploaded=False,
                  native_admission_qualified=False, phase6_complete=False)

    def save():
        report['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (args.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        with Compositor(args.compositor_tools, args.output / 'compositor', 1, 'gl',
                        repeat_rate=0) as display:
            environment = dict(display.environment,
                               ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                               LSAN_OPTIONS='', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',
                               LD_LIBRARY_PATH=':'.join(map(str, [engine, *args.library])),
                               LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent))
            require('LD_PRELOAD' not in environment, 'Preload observer appeared')
            argv = list(map(str, [executable, '--assets', args.assets, '--data', args.data,
                                 '--planets', args.planets, '--modules', engine / 'NativeModules',
                                 '--scenario', args.assets / SCENE, '--config', args.output / 'Orbiter.cfg',
                                 '--evidence', args.output, '--save', reload_path, '--capture-time', '0']))
            report['argv'] = argv
            with (args.output / 'console.log').open('w') as log:
                process = subprocess.Popen(argv, cwd=args.output, env=environment,
                                           stdout=log, stderr=subprocess.STDOUT)
                report['actual_pid'] = process.pid
                save()

                def wait_ready(folder):
                    deadline = time.monotonic() + 180
                    while time.monotonic() < deadline:
                        require(process.poll() is None, 'Actual app exited: ' + str(process.returncode))
                        frame = folder / 'scene.rgba'
                        ui = folder / 'ui-frames.csv'
                        if (display.surface(process.pid) and frame.exists() and
                                frame.stat().st_size == 1280 * 720 * 4 and ui.exists() and
                                len(ui.read_text().splitlines()) >= 60):
                            return
                        time.sleep(.1)
                    raise RuntimeError('Complete paused world did not render')

                def key(code, down):
                    display.command(f'key {process.pid} {code} {int(down)}')
                    report['physical_keys'].append(dict(code=code, down=bool(down),
                                                        monotonic_ns=time.monotonic_ns()))

                try:
                    for index in range(1, args.worlds + 1):
                        folder = args.output if index == 1 else args.output / ('session-' + str(index))
                        wait_ready(folder)
                        display.command('focus ' + str(process.pid))
                        report['worlds_observed_ready'] = index
                        save()
                        if index < args.worlds:
                            key(63, True)
                            key(63, False)
                    key(1, True)
                    process.wait(timeout=90)
                finally:
                    if process.poll() is None:
                        try:
                            display.command(f'key {process.pid} 1 1')
                            process.wait(timeout=30)
                        except (OSError, RuntimeError, subprocess.TimeoutExpired):
                            process.terminate()
                            process.wait(timeout=30)
                    report['actual_exitcode'] = process.returncode
                    save()

        console = (args.output / 'console.log').read_text(errors='replace')
        if args.expect_use_after_free:
            require(process.returncode != 0 and 'ERROR: AddressSanitizer: heap-use-after-free' in console
                    and 'Vessel::UpdateAttachments()' in console, 'Original attachment failure not reproduced')
            report['status'] = 'reproduced-paused-attachment-teardown-use-after-free-without-observer'
        else:
            require(process.returncode == 0 and report['worlds_observed_ready'] == args.worlds,
                    'World lifetime sequence incomplete')
            lives = []
            count = 0
            for index in range(1, args.worlds + 1):
                folder = args.output if index == 1 else args.output / ('session-' + str(index))
                life = load(folder / 'graphics-lifecycle.json')
                require(life['context_deleted'] and life['rendered_frames'] ==
                        life['successful_presents'] >= 60, 'Graphics lifetime incomplete')
                lives.append(life)
                with (folder / 'flight-state.csv').open() as stream:
                    rows = list(csv.DictReader(stream))
                require(len(rows) == 3 and {row['object']: row['class'] for row in rows} == expected,
                        'World dropped an original vessel')
                by_name = {row['object']: row for row in rows}
                require(by_name['STS-101']['dock'] == 'ISS' and
                        by_name['STS-101']['attached'] == 'Leonardo;' and
                        by_name['Leonardo']['attached'] == 'STS-101;',
                        'Original docking or reciprocal payload attachment missing')
                for row in rows:
                    require(row['tick'] == row['seconds'] == '0', 'World advanced before teardown')
                    for name in ('mjd', 'rx', 'ry', 'rz', 'vx', 'vy', 'vz', 'mass', 'fuel',
                                 'wx', 'wy', 'wz', *[f'm{i}{j}' for i in range(1, 4) for j in range(1, 4)]):
                        require(math.isfinite(float(row[name])), 'Nonfinite vessel state: ' + name)
                count += len(rows)
            require(not any(value in console for value in
                            ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
                             'AddressSanitizer:DEADLYSIGNAL', 'Production teardown:',
                             'LeakSanitizer has encountered', 'Suppressions used:')),
                    'Runtime or sanitizer diagnostic')
            report.update(status='passed-actual-paused-attached-docked-world-lifetimes',
                          lifecycles=lives, clean_contexts=len(lives),
                          successful_presents=sum(life['successful_presents'] for life in lives),
                          finite_original_vessel_rows=count, sanitizer_suppressions=False)
        require(all(sha(path) == value for path, value in guards.items()), 'Guarded input changed')
        require(all(sha(args.assets / name) == value for name, value in resources.items()),
                'Resource input changed during capture')
        report['all_guarded_inputs_unchanged'] = True
        save()
        print(report['status'], identity['profile'], args.worlds, 'worlds', flush=True)
    except BaseException as error:
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
        save()
        raise


if __name__ == '__main__':
    main()
