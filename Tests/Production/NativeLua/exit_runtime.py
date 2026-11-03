#!/usr/bin/env python3
"""Verify explicit Lua process exit on the real native application and full stock scenes."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent/'WaylandInput'), str(HERE.parent/'StockScenarios')]
from compositor import Compositor
from inventory import ships, require

MARKERS = ('runtime error:', 'ERROR: AddressSanitizer', 'ERROR: LeakSanitizer',
           'LeakSanitizer has encountered', 'AddressSanitizer:DEADLYSIGNAL',
           'LuaCall (', 'Orbiter native production:', 'Production teardown:')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def compile_probe(build, output, sanitized):
    compiler = next(line.split('=', 1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                    if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    probe = output/'exit-probe.so'
    argv = [compiler, '-std=c++17', '-fPIC', '-shared', '-Wl,--no-undefined']
    if sanitized:
        argv += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    for folder in [ROOT/'Orbitersdk/include', ROOT/'Src/Orbiter',
                   ROOT/'Src/Module/LuaScript/LuaInterpreter', build/'native-sdk',
                   build/'native-lua/sdk/include']:
        argv += ['-I'+str(folder)]
    argv += [str(HERE/'ExitProbe.cpp')]
    for folder in [build, build/'NativeModules/Plugin', build/'native-lua']:
        argv += ['-L'+str(folder), '-Wl,-rpath,'+str(folder)]
    argv += ['-lorbiter_production_vessels', '-lorbiter_production_boundary',
             '-l:LuaInterpreter.so', '-llua', '-ldl', '-o', str(probe)]
    (output/'probe-command.json').write_text(json.dumps(argv, indent=2)+'\n')
    with (output/'probe-build.log').open('w') as log:
        subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True)
    return probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'fixed', 'sanitized', 'assets', 'data', 'planets', 'dependencies', 'output'):
        parser.add_argument('--'+name, required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--sanitizer-library-path', required=True, action='append',
                        type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    require(not args.output.exists(), 'Exit verification output exists; replacement forbidden')
    builds = {label: getattr(args, label) for label in ('baseline', 'fixed', 'sanitized')}
    protected = [ROOT/name for name in json.loads((HERE.parent/'phase3-extraction.lock.json').read_text())['files']]
    protected += [Path(__file__), HERE/'ExitProbe.cpp', HERE.parent/'WaylandInput/compositor.py',
                  ROOT/'Scenarios/Tests/VesselApiTest.scn', ROOT/'Script/Tests/VesselApiTest.lua']
    for build in builds.values():
        protected += [build/'orbiter-production', build/'CMakeCache.txt', *build.rglob('*.so')]
    before = {str(path): digest(path) for path in protected}
    args.output.mkdir(parents=True)
    report = dict(status='running', phase6_complete=False, files_sha256=before, runs={}, failures={})
    manifest = args.output/'verification.json'

    def save():
        manifest.write_text(json.dumps(report, indent=2)+'\n')

    save()
    baseline_scene = (ROOT/'Scenarios/Navigation/Lunar transfer/Lunar transfer 1.scn').read_bytes()
    stock_scene = (ROOT/'Scenarios/Tests/VesselApiTest.scn').read_bytes()
    require((args.assets/'Scenarios/Tests/VesselApiTest.scn').read_bytes() == stock_scene, 'Staged stock scene changed')
    require((args.assets/'Script/Tests/VesselApiTest.lua').read_bytes() == (ROOT/'Script/Tests/VesselApiTest.lua').read_bytes(),
            'Staged stock script changed')
    cases = [
        ('async-zero', 'async', 0, 'oapi.exit(0)'),
        ('async-seven', 'async', 7, 'oapi.exit(7)'),
        ('sync-seven', 'sync', 7, 'oapi.exit(7)'),
        ('direct-seven', 'direct', 7, 'oapi.exit(7)'),
        ('protected-zero', 'direct', 0, 'xpcall(function() oapi.exit(0) end, function() io.open("following-error-handler.txt", "w"):close() end)'),
        ('nested-coroutine-seven', 'async', 7,
         'local child = coroutine.create(function() oapi.exit(7) end); '
         'local parent = coroutine.create(function() pcall(coroutine.resume, child); io.open("following-parent.txt", "w"):close() end); '
         'pcall(coroutine.resume, parent)'),
        ('cross-vm-zero', 'cross-vm', 0, 'nested_native_exit()'),
        ('unchanged-vessel-api', 'stock', 0, None),
    ]
    try:
        with Compositor(args.dependencies, args.output/'compositor') as display:
            for label in ('baseline', 'fixed', 'sanitized'):
                build = builds[label]
                group = args.output/label; group.mkdir()
                sanitized = label in ('baseline', 'sanitized')
                probe = compile_probe(build, group, sanitized) if label != 'baseline' else None
                asan = subprocess.check_output(['cc', '-print-file-name=libasan.so'], text=True).strip()
                for name, mode, code, script in (cases[-1:] if label == 'baseline' else cases):
                    out = group/name; out.mkdir()
                    source = stock_scene if mode == 'stock' else baseline_scene
                    (out/'flight.scn').write_bytes(source)
                    (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\nInstrumentUpdateInterval = 0.25\n')
                    (out/'exit-mode.txt').write_text(mode+'\n')
                    if script:
                        (out/'exit.lua').write_text('io.open("before-exit.txt", "w"):close()\n'+script+
                            '\nio.open("following-exit.txt", "w"):close()\n')
                    original_save = b'Existing save must survive an explicit process exit.\n'
                    (out/'saved.scn').write_bytes(original_save)
                    (out/'replay.csv').write_text('tick,phase,action,value\n')
                    env = dict(display.environment, LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe', LP_NUM_THREADS='2',
                               LD_LIBRARY_PATH=str(build))
                    for key in ('LD_PRELOAD', 'ASAN_OPTIONS', 'LSAN_OPTIONS', 'UBSAN_OPTIONS'):
                        env.pop(key, None)
                    if sanitized:
                        env.update(LD_LIBRARY_PATH=':'.join(map(str, [build, *args.sanitizer_library_path])),
                                   ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0', LSAN_OPTIONS='',
                                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    if probe:
                        env['LD_PRELOAD'] = asan+':'+str(probe) if sanitized else str(probe)
                    argv = [str(build/'orbiter-production')]
                    for key in ('assets', 'data', 'planets'):
                        argv += ['--'+key, str(getattr(args, key))]
                    argv += ['--modules', str(build/'NativeModules'), '--config', str(out/'Orbiter.cfg'),
                             '--scenario', str(out/'flight.scn'), '--save', str(out/'saved.scn'), '--evidence', str(out),
                             '--replay', str(out/'replay.csv'), '--frames', '60', '--fixed-step', '.25',
                             '--frame-delay-ms', '120', '--run']
                    (out/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
                    key = label+'/'+name
                    try:
                        with (out/'console.log').open('w') as log:
                            completed = subprocess.run(argv, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                        result = dict(status='process-exited', returncode=completed.returncode)
                        report['runs'][key] = result; save()
                        text = (out/'console.log').read_text(errors='replace')
                        if label == 'baseline':
                            require('=== All tests passed ===' in text, 'Baseline stock script assertions did not pass')
                            require('ERROR: LeakSanitizer' in text and completed.returncode != 0,
                                    'Retained original leak no longer reproduced')
                            require(not (out/'graphics-lifecycle.json').exists(), 'Baseline unexpectedly completed graphics teardown')
                            result['status'] = 'expected-defect-reproduced'; save(); continue
                        require(completed.returncode == code, 'Requested process exit code changed')
                        require(not any(marker in text for marker in MARKERS), 'Runtime, Lua, teardown or sanitizer diagnostic')
                        life = json.loads((out/'graphics-lifecycle.json').read_text())
                        result['lifecycle'] = life
                        require(life['context_deleted'] and life['rendered_frames'] == life['successful_presents'], 'Graphics teardown incomplete')
                        require(0 < life['successful_presents'] < 60, 'Explicit exit did not stop before the frame limit')
                        require((out/'saved.scn').read_bytes() == original_save, 'Explicit exit saved or replaced the current state')
                        state = rows(out/'flight-state.csv')
                        first = [row for row in state if row['tick'] == '0']
                        expected = {(name, kind.lower()) for name, kind in ships(source.decode('cp1252')).items()}
                        require({(row['object'], row['class'].lower()) for row in first} == expected and len(first) == len(expected),
                                'Full initial vessel graph was reduced or substituted')
                        result['initial_vessels'] = sorted(expected)
                        result['finalized_ticks'] = len({row['tick'] for row in state})
                        if mode == 'stock':
                            require('=== All tests passed ===' in text, 'Unchanged stock script did not finish its assertions')
                        else:
                            require((out/'before-exit.txt').exists(), 'Exit script never ran')
                            require(not list(out.glob('following-*.txt')), 'Lua continued after exit')
                            events = (out/'exit-dispatch.csv').read_text().splitlines()
                            require('4,exit.dispatch' in events, 'Exit dispatched at the wrong native boundary')
                            require(life['successful_presents'] == 4, 'Extra presentation after explicit exit')
                            require('4,update.return' not in events and '4,end.enter' not in events and
                                    not any('after.exit' in line for line in events), 'Native callbacks continued after exit')
                            loaded = (out/'exit-loaded.txt').read_text()
                            require(str(build/'NativeModules/Plugin/LuaInterpreter.so') in loaded, 'Different interpreter loaded')
                            if sanitized:
                                for directory in args.sanitizer_library_path:
                                    require(str(directory) in loaded, 'Private sanitizer dependency was not mapped')
                        result.update(status='passed', save_unchanged=True, following_lua_instructions=False,
                                      files_sha256={str(path.relative_to(out)): digest(path) for path in out.iterdir() if path.is_file()})
                        print(key, 'passed', flush=True)
                    except Exception as error:
                        report['failures'][key] = str(error)
                        print(key, 'failed:', error, flush=True)
                    save()
        require(before == {str(path): digest(path) for path in protected}, 'Source or retained runtime drift')
        report.update(sources_and_binaries_unchanged=True,
                      status='passed' if not report['failures'] and len(report['runs']) == 17 else 'failed')
        save()
    except BaseException as error:
        report.update(status='interrupted-or-failed', error=str(error)); save(); raise
    require(report['status'] == 'passed', 'Lua exit verification incomplete')


if __name__ == '__main__':
    main()
