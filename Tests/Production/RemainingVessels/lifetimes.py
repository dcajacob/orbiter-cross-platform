"""Whole-world lifetime facet of the existing native capture runner.

This diagnostic does not replace physical interactions, persistence, full stock
parity or the actual F5 paused-attachment control. Audit its closed files again
after capture; a successful launcher alone does not establish lifetime coverage.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / 'Closeout'), str(HERE.parent / 'StockScenarios'),
               str(HERE.parent / 'WaylandInput'), str(HERE.parent / 'RemainingStockRepaired')]
from contracts import atomic_json, load, require, sha
from processes import OwnedProcess
from intentional_exit import build_identity
from compositor import Compositor
from inventory import ships
import data_inputs

FRAMES = 60
SESSIONS = 20
STRINGS = {'object', 'class', 'dock', 'focus', 'attached'}
DIAGNOSTICS = ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
               'AddressSanitizer:DEADLYSIGNAL', 'Production teardown:',
               'LeakSanitizer has encountered', 'Suppressions used:', 'Lua error:',
               'Orbiter native production:')


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def inspect_world(folder, expected):
    life = load(folder / 'graphics-lifecycle.json')
    require(life == dict(rendered_frames=FRAMES, successful_presents=FRAMES,
                         context_deleted=True), 'Incomplete sixty-frame graphics lifetime')
    groups = {}
    for row in rows(folder / 'flight-state.csv'):
        require(None not in row and None not in row.values(), 'Incomplete finalized state row')
        tick = int(row['tick'])
        groups.setdefault(tick, []).append(row)
        require(all(math.isfinite(float(v)) for k, v in row.items() if k not in STRINGS),
                'Nonfinite lifetime state')
    require(set(groups) == set(range(FRAMES + 1)), 'Incomplete lifetime tick coverage')
    for group in groups.values():
        require(len(group) == len(expected) and
                {r['object']: r['class'] for r in group} == expected,
                'Original complete lifetime roster differs')
    image = folder / 'scene.rgba'
    require(image.stat().st_size == 1280 * 720 * 4, 'Incomplete lifetime frame')
    return dict(lifecycle=life, finalized_ticks=len(groups), vessels=len(expected),
                files_sha256={p.name: sha(p) for p in folder.iterdir() if p.is_file()})


def inspect_loader(console, modules):
    result = {}
    for module in modules:
        # Match the actual absolute DSO, not a similarly named host helper.
        suffix = str(Path(modules[module]).resolve()) if isinstance(modules, dict) else '/NativeModules/Vessel/' + module + '.so'
        counts = {event: len(re.findall(r'calling ' + event + r': [^\n]*' +
                                       re.escape(suffix) + r'(?: \[0\])?\s*\n', console))
                  for event in ('init', 'fini')}
        require(counts == dict(init=SESSIONS, fini=SESSIONS),
                'Actual module initialization/finalization count differs: ' + module)
        destroyed = len(re.findall(r'file=[^\n]*' + re.escape(suffix) +
                                  r'[^\n]*destroying link map', console))
        require(destroyed == SESSIONS, 'Module was retained instead of unloaded: ' + module)
        result[module] = dict(counts, destroyed_link_maps=destroyed)
    return result


def inspect_case(folder, case):
    receipt = load(folder / 'process-receipt.json')
    require(receipt['terminal'] is True and receipt['cancelled'] is False and
            receipt['actual_returncode'] == 0 and receipt['actual_collector_pid'] > 0 and
            len(receipt['owned_process_identities']) >= 1, 'Actual clean simulator receipt missing')
    invocation = load(folder / 'invocation.json')
    argv = invocation['argv']
    require(argv[argv.index('--sessions') + 1] == str(SESSIONS) and
            argv[argv.index('--frames') + 1] == str(FRAMES) and
            argv[argv.index('--fixed-step') + 1] == '0.015625' and
            argv[argv.index('--capture-time') + 1] == '0.78125' and
            '--run' in argv and '--fixed-ui-clock' in argv,
            'Bounded lifetime invocation differs')
    require(sha(argv[0]) == invocation['executable_sha256'] and
            sha(argv[argv.index('--scenario') + 1]) == invocation['scenario_sha256'],
            'Lifetime executable or original scenario changed')
    require(invocation['environment'] == dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
            LSAN_OPTIONS='', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',
            LD_PRELOAD=None, LD_DEBUG='files'), 'Unsuppressed lifetime environment differs')
    console = (folder / 'console.log').read_text(errors='replace')
    require(not any(marker in console for marker in DIAGNOSTICS), 'Runtime/sanitizer diagnostic')
    worlds = [inspect_world(folder / ('session-' + str(n)), case['vessels'])
              for n in range(1, SESSIONS + 1)]
    require(all(load(folder / ('session-' + str(n)) / 'numerics.json')['math'] ==
                case['actual_math_profile'] for n in range(1, SESSIONS + 1)),
            'Actual lifetime automatic/SSE2 mode differs')
    require({p.name for p in folder.glob('session-*') if p.is_dir()} ==
            {'session-' + str(n) for n in range(1, SESSIONS + 1)}, 'Unexpected lifetime count')
    # Preserve every repeat for parity audits. This lifetime facet does not
    # invent a byte-identity budget for legitimate process-global RNG progress.
    distinct = {name: len({w['files_sha256'][name] for w in worlds})
                for name in ('flight-state.csv', 'scene.rgba', 'camera.csv', 'visual-meshes.csv')}
    return dict(status='passed-twenty-world-lifetimes-diagnostic-only', worlds=worlds,
                module_lifetimes=inspect_loader(console, case['modules']),
                distinct_repeat_digests=distinct,
                console_sha256=sha(folder / 'console.log'),
                invocation_sha256=sha(folder / 'invocation.json'),
                process_receipt_sha256=sha(folder / 'process-receipt.json'))


def audit(path):
    path = Path(path).resolve()
    report = load(path)
    require(report['protocol'] == 'remaining-stock-lifetimes-v1' and
            report['status'] == 'captured-lifetimes-awaiting-independent-audit' and
            report['diagnostic_only'] is True and report['failures'] == {} and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False,
            'Incomplete or incorrectly scoped lifetime capture')
    require(set(report['cases']) == set(report['cases_requested']), 'Lifetime selection incomplete')
    runtime = report['runtime']
    build = load(runtime['build_record'])
    checked_identity = build_identity(Path(runtime['build']) / 'orbiter-production',
        Path(runtime['build']) / 'NativeModules', Path(runtime['build_record']),
        build['source_base'], Path(report['runtime_owner']))
    require(checked_identity == report['runtime_identity'], 'Independent lifetime ABI identity differs')
    require(data_inputs.inspect(Path(runtime['data']), Path(runtime['planets'])) ==
            report['actual_original_data'], 'Original lifetime data changed')
    require(all(sha(p) == value for p, value in report['guarded_files_sha256'].items()),
            'Owning source, package, provider, original resource or runner changed')
    cases = {c['id']: c for c in load(HERE.parent / 'RemainingStock/cases.json')['cases']}
    classes = load(HERE.parent / 'RemainingStock/cases.json')['classes']
    actual = {}
    for name, case in report['cases'].items():
        require(case['vessels'] == cases[name]['declared_vessels'], 'Original lifetime roster identity differs')
        expected_modules = {classes[k]['module'] for k in case['vessels'].values() if classes[k]['module']}
        require(case['modules'] == {module: str(Path(runtime['build']) / 'NativeModules/Vessel' /
                    (module + '.so')) for module in expected_modules} and
                case['actual_math_profile'] == 'amd-6121d02-' +
                ('sse2' if checked_identity['math_profile'] == 'sse2' else 'fma3'),
                'Actual lifetime module or math identity differs')
        folder = path.parent / name
        invocation = load(folder / 'invocation.json')
        argv = invocation['argv']
        scenario = Path(runtime['assets']) / cases[name]['scenario_entry_point']
        require(argv[argv.index('--scenario') + 1] == str(scenario) and
                scenario.read_bytes() == (Path(report['runtime_owner']) /
                cases[name]['scenario_entry_point']).read_bytes(), 'Audited original scenario differs')
        checked = inspect_case(path.parent / name, case)
        require(checked == case['result'], 'Closed lifetime evidence changed: ' + name)
        actual[name] = checked
    return dict(status='audited-twenty-world-lifetimes-diagnostic-only',
                capture_sha256=sha(path), runtime_identity=report['runtime_identity'],
                cases=actual, worlds=len(actual) * SESSIONS,
                successful_presents=len(actual) * SESSIONS * FRAMES,
                owning_bytes_unchanged=True, diagnostic_only=True,
                native_admission_qualified=False, phase6_complete=False)


def capture(args):
    require(not args.output.exists() and 1 <= args.jobs <= 4 and args.case,
            'Fresh selected lifetime output and one to four workers required')
    config = load(HERE.parent / 'RemainingStock/cases.json')
    cases = [c for c in config['cases'] if c['id'] in args.case]
    require(len(cases) == len(set(args.case)) == len(args.case), 'Unknown/duplicate lifetime selection')
    build = load(args.build_record)
    identity = build_identity(args.build / 'orbiter-production', args.build / 'NativeModules',
                              args.build_record, build['source_base'], args.owner)
    require(identity['sanitizer_linked'], 'Unsuppressed ASan/UBSan/LSan package required')
    executable = args.build / 'production_remaining_stock_diagnostic'
    require(build['candidate_runtime_files_sha256'][executable.relative_to(args.owner).as_posix()]
            == sha(executable), 'Actual diagnostic executable differs')
    guards = {}
    for group in ('source_sha256_lf', 'dependency_sha256_lf'):
        for name, value in build[group].items():
            path = args.owner / name
            require(hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                    == value, 'Owning build input changed: ' + name)
            guards[str(path)] = sha(path)
    for group in ('runtime_files_sha256', 'candidate_runtime_files_sha256', 'generated_source_files_sha256'):
        for name, value in build[group].items():
            require(sha(args.owner / name) == value, 'Retained package changed: ' + name)
            guards[str(args.owner / name)] = value
    resources = load(args.assets / 'remaining-vessels-resources.json')['staged_files_sha256']
    for name, value in resources.items():
        require(sha(args.assets / name) == value, 'Original resource changed: ' + name)
        guards[str(args.assets / name)] = value
    helpers = [HERE / 'native.py', Path(__file__), HERE.parent / 'RemainingStock/cases.json',
               HERE.parent / 'NativeScene/Orbiter.cfg', args.build_record,
               args.assets / 'remaining-vessels-resources.json', args.gtk_plugin, args.gtk_build_record,
               args.compositor_tools / 'test-tools.json',
               Path(data_inputs.__file__),
               *[HERE.parent / name for name in ('stock-data.lock.json', 'standard-planets.lock.json')],
               *[Path(sys.modules[n].__file__) for n in ('contracts', 'processes', 'intentional_exit',
                                                       'inventory', 'compositor')]]
    for path in helpers:
        guards[str(path)] = sha(path)
    gtk = load(args.gtk_build_record)
    require(gtk['status'] == 'built' and gtk['baseline'] is False and
            gtk['plugin_sha256'] == sha(args.gtk_plugin) and gtk['sanitizers'] is True,
            'Pinned sanitizer-enabled decoration provider required')
    for library in args.library:
        for path in library.glob('*.so*'):
            if path.is_file(): guards[str(path)] = sha(path)
    producer = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    for path in (HERE / 'native.py', Path(__file__)):
        require(subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                        producer + ':' + path.relative_to(ROOT).as_posix()]) == path.read_bytes(),
                'Lifetime runner must match immutable producer')
    original_data = data_inputs.inspect(args.data, args.planets)
    args.output.mkdir(parents=True)
    report = dict(protocol='remaining-stock-lifetimes-v1', status='running',
                  runtime_identity=identity, runtime_owner=str(args.owner), producer_commit=producer,
                  runtime={name: str(getattr(args, name)) for name in
                           ('build', 'build_record', 'assets', 'data', 'planets')},
                  actual_original_data=original_data,
                  guarded_files_sha256=guards, diagnostic_only=True, cases_requested=[c['id'] for c in cases],
                  cases={}, failures={}, native_admission_qualified=False, phase6_complete=False)
    path = args.output / 'lifetimes.json'
    atomic_json(path, report)

    def run_case(case):
        folder = args.output / case['id']
        folder.mkdir()
        scenario = args.assets / case['scenario_entry_point']
        expected = ships(scenario.read_text())
        require(expected == case['declared_vessels'] and
                scenario.read_bytes() == (args.owner / case['scenario_entry_point']).read_bytes(),
                'Complete original lifetime scene changed')
        modules = {name: str(args.build / 'NativeModules/Vessel' / (name + '.so'))
                   for name in sorted({config['classes'][kind]['module'] for kind in expected.values()
                                       if config['classes'][kind]['module']})}
        descriptor = dict(vessels=expected, modules=modules, actual_math_profile='amd-6121d02-' +
                          ('sse2' if identity['math_profile'] == 'sse2' else 'fma3'))
        cfg = (HERE.parent / 'NativeScene/Orbiter.cfg').read_text()
        for line in ('PropStages = 1\n', 'PropStage0 = 1 1 1\n', 'PropSubsampling = 1\n'):
            require(cfg.count(line) == 1, 'Unexpected original propagator fixture')
            cfg = cfg.replace(line, '')
        (folder / 'Orbiter.cfg').write_text(cfg + '\nMenubarMode = 1\nInfobarMode = 1\n')
        (folder / 'replay.csv').write_text('tick,phase,action,value\n')
        with Compositor(args.compositor_tools, folder / 'compositor', 1, 'gl', repeat_rate=0) as display:
            env = dict(display.environment, LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
                       LP_NUM_THREADS='2', LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent),
                       LD_LIBRARY_PATH=':'.join(map(str, [args.build, *args.library])),
                       ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0', LSAN_OPTIONS='',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1', LD_DEBUG='files')
            env.pop('LD_PRELOAD', None)
            argv = list(map(str, [executable, '--assets', args.assets, '--data', args.data,
                '--planets', args.planets, '--modules', args.build / 'NativeModules', '--scenario', scenario,
                '--config', folder / 'Orbiter.cfg', '--evidence', folder, '--save', folder / 'saved.scn',
                '--frames', FRAMES, '--sessions', SESSIONS, '--fixed-step', '0.015625',
                '--replay', folder / 'replay.csv', '--fixed-ui-clock', '--capture-time', '0.78125', '--run']))
            invocation = dict(argv=argv, executable_sha256=sha(executable),
                              scenario_sha256=sha(scenario), environment={k: env.get(k) for k in
                              ('ASAN_OPTIONS', 'LSAN_OPTIONS', 'UBSAN_OPTIONS', 'LD_PRELOAD', 'LD_DEBUG')})
            atomic_json(folder / 'invocation.json', invocation)
            with (folder / 'console.log').open('w') as log:
                owned = OwnedProcess(argv, cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    owned.process.wait(timeout=1800)
                finally:
                    atomic_json(folder / 'process-receipt.json', owned.cancel())
        descriptor['result'] = inspect_case(folder, descriptor)
        return descriptor

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending = {pool.submit(run_case, case): case['id'] for case in cases}
        for future in concurrent.futures.as_completed(pending):
            name = pending[future]
            try:
                report['cases'][name] = future.result()
            except BaseException as error:
                report['failures'][name] = dict(error=str(error), traceback=traceback.format_exc())
            atomic_json(path, report)
            print(name, 'failed' if name in report['failures'] else 'twenty lifetimes captured', flush=True)
    require(all(sha(p) == value for p, value in guards.items()), 'Guarded lifetime inputs changed')
    require(data_inputs.inspect(args.data, args.planets) == original_data, 'Original lifetime data changed')
    report['status'] = ('failed' if report['failures'] else 'captured-lifetimes-awaiting-independent-audit')
    atomic_json(path, report)
    require(not report['failures'], 'Lifetime failures retained; no class admission')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Fresh independent lifetime audit required')
    atomic_json(args.output, audit(args.capture))
