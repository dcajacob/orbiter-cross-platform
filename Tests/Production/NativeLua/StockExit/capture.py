#!/usr/bin/env python3
"""Capture the unchanged vessel API script's exit in preserved Windows or native builds."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

from contract import HERE, ROOT, digest, inspect, require, settings, sha_lf

sys.path[:0] = [str(HERE.parents[1]/'StockVessels'), str(HERE.parents[1]/'Cockpit'),
                str(HERE.parents[1]), str(HERE.parents[1]/'Client'), str(HERE.parents[1]/'WaylandInput')]
from original import loaded_modules
from stage import run as stage
from run_client import mesa_files
from compositor import Compositor


def report_for(args, config, host):
    return dict(status='running', phase6_complete=False, host=host, configuration=args.configuration,
                math_profile=args.math_profile, case=config,
                producer_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                source_sha256_lf={str(path.relative_to(ROOT)): sha_lf(path) for path in
                    [*sorted(p for p in HERE.iterdir() if p.is_file()), HERE.parents[1]/'StockVessels/Observation.h']},
                runs=[], failures={}, corpus_termination_policy_changed=False)


def finish_repeats(output, report):
    if len(report['runs']) == 2 and not report['failures']:
        for name in ('stock-vessel-state.csv', 'stock-vessel-docks.csv', 'stock-exit-phases.csv'):
            require((output/'run-1'/name).read_bytes() == (output/'run-2'/name).read_bytes(),
                    'Repeated stock exit observations differ: '+name)
        report.update(status='captured-awaiting-original-audit', repeated_traces_byte_identical=True)
    else:
        report['status'] = 'incomplete'


def capture_original(args, config):
    require(sys.platform == 'win32', 'Original exit capture requires native Windows')
    runtime_root = args.executable.parent
    runtime = json.loads((runtime_root/'control-reference-runtime.json').read_text())
    preserved = json.loads((runtime_root/'test-runtime.json').read_text())
    require(runtime['application_source'] == preserved['source_commit'] == config['application_source'],
            'Wrong preserved original application or SDK')
    protected = {name: checksum for name, checksum in
                 {**preserved['files'], **runtime['client_files_sha256']}.items()
                 if name != 'Modules/Plugin/ProductionCockpitDriver.dll'}
    require(all(digest(runtime_root/name) == value for name, value in protected.items()),
            'Preserved original application/SDK/client differs')
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2') == '1') == (args.math_profile == 'sse2'),
            'Original CRT selection differs from requested profile')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true', GALLIUM_DRIVER='llvmpipe')
    observer = runtime_root/'Modules/Plugin/ProductionCockpitDriver.dll'
    observer_sha = digest(observer)
    expected_modules = {}
    for name, checksum in {**protected, 'Modules/Plugin/ProductionCockpitDriver.dll': observer_sha}.items():
        expected_modules.setdefault(Path(name).name.casefold(), set()).add(checksum)
    report = report_for(args, config, 'original-windows')
    report.update(runtime=runtime, preserved_files_sha256=protected, observer_sha256=observer_sha)
    manifest = args.output/'capture.json'
    def save(): manifest.write_text(json.dumps(report, indent=2)+'\n')
    save()
    for repeat in (1, 2):
        out = args.output/('run-'+str(repeat))
        try:
            def configure(directory):
                cfg = directory/'Orbiter.cfg'
                cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver',
                    '  ProductionCockpitDriver\n  OGLClient')+
                    '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\nInstrumentUpdateInterval = 0.25\n')
                (directory/'Scenarios/Behavior.scn').write_bytes((ROOT/'Scenarios'/config['scenario']).read_bytes())
                require(sha_lf(directory/config['script']) == config['script_sha256_lf'], 'Staged original script changed')
                (directory/'ogl-evidence.enabled').touch(); mesa_files(args.mesa, directory)
            # stage runs check=True; a successful return proves the actual exit code was zero.
            stage(args.executable, args.data, args.planets, out, config, configure)
            (out/'process-result.json').write_text(json.dumps(dict(returncode=0, source='checked original subprocess result'))+'\n')
            result = inspect(out, config, 'original-windows', 0)
            result['actual_math'] = (out/'math-profile.txt').read_text().strip()
            require(result['actual_math'] in ('fma3', 'sse2'), 'Unknown original CRT math implementation')
            require(args.math_profile != 'sse2' or result['actual_math'] == 'sse2', 'Original SSE2 was not selected')
            result['loaded_modules'] = loaded_modules(out, expected_modules)
            require({'lua.dll', 'luainline.dll', 'luainterpreter.dll'} <=
                    {Path(entry['path']).name.casefold() for entry in result['loaded_modules']},
                    'Preserved Lua stack did not load')
            report['runs'].append(result)
            print('original run', repeat, 'captured', result['completed_frames'], 'frames', flush=True)
        except Exception as error:
            report['failures'][str(repeat)] = str(error)
            print('original run', repeat, 'failed:', error, flush=True)
        save()
    finish_repeats(args.output, report)
    require(all(digest(runtime_root/name) == value for name, value in protected.items()), 'Preserved original files changed')
    require(digest(observer) == observer_sha, 'Original observer changed')
    report['preserved_runtime_unchanged'] = True; save()
    require(not report['failures'] and len(report['runs']) == 2, 'Original stock exit capture incomplete')


def capture_native(args, config):
    build = args.build
    cache_path = build/'CMakeCache.txt'
    cache = dict(line.split('=', 1) for line in cache_path.read_text().splitlines()
                 if '=' in line and not line.startswith(('#', '//')))
    require(cache['CMAKE_BUILD_TYPE:STRING'] == args.configuration, 'Declared native configuration differs from actual build')
    require(cache['ORBITER_MATH_FORCE_SSE2:BOOL'] == ('ON' if args.math_profile == 'sse2' else 'OFF'),
            'Declared native math selection differs from actual build')
    flags = [cache['CMAKE_C_FLAGS:STRING'], cache['CMAKE_CXX_FLAGS:STRING']]
    require(all(('-fsanitize=address,undefined' in value) if args.sanitize else ('-fsanitize' not in value) for value in flags),
            'Declared instrumentation differs from actual C/C++ configuration')
    linked = subprocess.check_output(['readelf', '-d', str(build/'orbiter-production')], text=True)
    require(('libasan.so' in linked and 'libubsan.so' in linked) if args.sanitize else
            ('libasan.so' not in linked and 'libubsan.so' not in linked), 'Actual executable instrumentation differs')
    report = report_for(args, config, 'native-linux')
    report['build_identity'] = dict(configuration=args.configuration, math=args.math_profile, instrumentation=flags,
                                    actual_sanitizer_linked=args.sanitize, cmake_cache_sha256=digest(cache_path))
    protected = [build/'orbiter-production', cache_path, *build.rglob('*.so')]
    protected += [ROOT/name for name in json.loads((HERE.parents[1]/'phase3-extraction.lock.json').read_text())['files']]
    before = {str(path): digest(path) for path in protected}
    report['protected_files_sha256'] = before
    compiler = cache['CMAKE_CXX_COMPILER:FILEPATH']
    probe = args.output/'stock-exit-probe.so'
    command = [compiler, '-std=c++17', '-fPIC', '-shared', '-Wl,--no-undefined']
    if args.sanitize: command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += ['-I'+str(ROOT/'Orbitersdk/include'), '-I'+str(ROOT/'Src/Orbiter'), str(HERE/'NativeProbe.cpp'),
                '-L'+str(build), '-Wl,-rpath,'+str(build), '-lorbiter_production_vessels',
                '-lorbiter_production_boundary', '-ldl', '-o', str(probe)]
    (args.output/'probe-command.json').write_text(json.dumps(command, indent=2)+'\n')
    with (args.output/'probe-build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    manifest = args.output/'capture.json'
    def save(): manifest.write_text(json.dumps(report, indent=2)+'\n')
    save()
    surface = Compositor(args.dependencies, args.output/'compositor') if args.dependencies else contextlib.nullcontext(None)
    with surface as display:
        environment = display.environment if display else os.environ
        for repeat in (1, 2):
            out = args.output/('run-'+str(repeat)); out.mkdir()
            try:
                (out/'flight.scn').write_bytes((ROOT/'Scenarios'/config['scenario']).read_bytes())
                (out/'Orbiter.cfg').write_text((HERE.parents[1]/'NativeScene/Orbiter.cfg').read_text()+
                    '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\nInstrumentUpdateInterval = 0.25\n')
                (out/'saved.scn').write_bytes(b'Existing save preserved across stock oapi.exit.\n')
                (out/'replay.csv').write_text('tick,phase,action,value\n')
                require(sha_lf(args.assets/config['script']) == config['script_sha256_lf'], 'Staged native script changed')
                env = dict(environment, LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe', LP_NUM_THREADS='2',
                           LD_LIBRARY_PATH=':'.join(map(str, [build, *args.library_directory])))
                for key in ('LD_PRELOAD', 'ASAN_OPTIONS', 'LSAN_OPTIONS', 'UBSAN_OPTIONS'): env.pop(key, None)
                env['LD_PRELOAD'] = str(probe)
                if args.sanitize:
                    asan = subprocess.check_output([compiler, '-print-file-name=libasan.so'], text=True).strip()
                    env.update(LD_PRELOAD=asan+':'+str(probe), ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                               LSAN_OPTIONS='', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                argv = [str(build/'orbiter-production'), '--assets', str(args.assets), '--data', str(args.data),
                        '--modules', str(build/'NativeModules'), '--planets', str(args.planets),
                        '--scenario', str(out/'flight.scn'), '--config', str(out/'Orbiter.cfg'),
                        '--evidence', str(out), '--save', str(out/'saved.scn'), '--replay', str(out/'replay.csv'),
                        '--frames', '60', '--fixed-step', '.25', '--run']
                (out/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
                with (out/'console.txt').open('w') as log:
                    process = subprocess.run(argv, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                (out/'process-result.json').write_text(json.dumps(dict(returncode=process.returncode))+'\n')
                result = inspect(out, config, 'native-linux', process.returncode)
                loaded = (out/'renderer-modules.txt').read_text()
                for path in (build/'NativeModules/Plugin/LuaInline.so', build/'NativeModules/Plugin/LuaInterpreter.so',
                             build/'native-lua/liblua.so'):
                    require(str(path) in loaded, 'Different native Lua library loaded: '+str(path))
                if args.sanitize:
                    for folder in args.library_directory: require(str(folder) in loaded, 'Private sanitizer dependency not mapped')
                require(json.loads((out/'native-window.json').read_text())['backend'] == args.backend, 'Wrong actual window backend')
                result['actual_math'] = json.loads((out/'numerics.json').read_text())['math']
                report['runs'].append(result)
                print('native run', repeat, 'captured', result['completed_frames'], 'frames', flush=True)
            except Exception as error:
                report['failures'][str(repeat)] = str(error)
                print('native run', repeat, 'failed:', error, flush=True)
            save()
    finish_repeats(args.output, report)
    require(before == {str(path): digest(path) for path in protected}, 'Retained native runtime or owning source changed')
    report['sources_and_runtime_unchanged'] = True; save()
    require(not report['failures'] and len(report['runs']) == 2, 'Native stock exit capture incomplete')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', action='store_true')
    for name in ('executable', 'build', 'assets', 'mesa', 'dependencies'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve())
    for name in ('data', 'planets', 'output'):
        parser.add_argument('--'+name, required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--configuration', required=True, choices=('Debug', 'Release'))
    parser.add_argument('--math-profile', required=True, choices=('automatic', 'sse2'))
    parser.add_argument('--backend', choices=('wayland', 'x11'))
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--library-directory', action='append', default=[], type=lambda p: Path(p).resolve())
    args = parser.parse_args(); config = settings()
    require(not args.output.exists(), 'Stock exit capture exists; replacement forbidden')
    require(bool(args.executable and args.mesa) if args.original else bool(args.build and args.assets and args.backend),
            'Required original or native runtime paths missing')
    require(not args.dependencies or args.backend == 'wayland', 'Private display requires Wayland')
    args.output.mkdir(parents=True)
    if args.original: capture_original(args, config)
    else: capture_native(args, config)


if __name__ == '__main__': main()
