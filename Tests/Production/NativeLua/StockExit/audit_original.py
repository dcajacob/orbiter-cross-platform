#!/usr/bin/env python3
"""Independently audit all four preserved Windows stock-exit profiles."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import sys

from contract import HERE, ROOT, digest, inspect, require, settings, sha_lf

sys.path.insert(0, str(HERE.parents[1]/'StockVessels'))
from verify_original import compare_state

OBSERVER = 'Modules/Plugin/ProductionCockpitDriver.dll'
PROTOCOL = {str((HERE/name).relative_to(ROOT)).replace('\\', '/') for name in
            ('CMakeLists.txt', 'Driver.cpp', 'NativeProbe.cpp', 'capture.py', 'contract.py',
             'Gate.Test.py', 'README.md', 'case.json')}
PROTOCOL.add('Tests/Production/StockVessels/Observation.h')


def safe_name(name):
    name = name.replace('\\', '/')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name, 'Unsafe reference source path')
    return name


def module_audit(out, recorded, expected):
    invocation = json.loads((out/'invocation.json').read_text())
    run_root = PureWindowsPath(invocation['argv'][0]).parent
    bindings = json.loads((out/'mesa-bindings.json').read_text())
    runtime = bindings['runtime']
    lock_path = ROOT/'Tests/Production/mesa-ucrt64.lock.json'
    lock = json.loads(lock_path.read_text())
    require(runtime['lock_sha256'] == digest(lock_path) and
            {p['name']: p['sha256'] for p in runtime['packages']} ==
            {p['name']: p['sha256'] for p in lock['packages']}, 'Actual original Mesa package pins differ')
    mesa = {PurePosixPath(name).name.casefold(): entry['sha256'] for name, entry in runtime['files'].items()
            if name.lower().endswith('.dll')}
    effective = {name.casefold(): entry['effective_sha256'] for name, entry in bindings['bindings'].items()}
    raw_paths = {str(PureWindowsPath(line)).casefold() for line in (out/'renderer-modules.txt').read_text().splitlines()
                 if PureWindowsPath(line).suffix.lower() in ('.dll', '.exe')}
    require(raw_paths == {str(PureWindowsPath(entry['path'])).casefold() for entry in recorded['loaded_modules']},
            'Recorded module inventory differs from the actual original DLL list')
    names = set()
    for entry in recorded['loaded_modules']:
        path = PureWindowsPath(entry['path']); name = path.name.casefold(); names.add(name)
        if path.is_relative_to(run_root):
            allowed = {effective.get(name, mesa[name])} if name in mesa else expected.get(name, set())
            require(entry['sha256'] in allowed, 'Original loaded application/module bytes differ: '+name)
        else:
            require(len(path.parts) > 1 and path.parts[1].casefold() == 'windows', 'Unrecorded external original DLL')
    require({'orbiter.exe', 'oglclient.dll', 'opengl32.dll', 'productioncockpitdriver.dll',
             'lua.dll', 'luainterpreter.dll', 'luainline.dll', 'deltaglider.dll', 'shuttlea.dll', 'shuttlepb.dll'} <= names,
            'Required original application, renderer, Lua or vessel module was not loaded')


def audit_profile(base, profile, config, producer, preserved_root=None, metadata_pins=None):
    configuration, math_profile = profile.split('-', 1)
    capture = base/'stock-exit-original'
    report = json.loads((capture/'capture.json').read_text())
    require(report['status'] == 'captured-awaiting-original-audit' and not report['failures'] and
            report['host'] == 'original-windows' and report['configuration'] == configuration and
            report['math_profile'] == math_profile and report['producer_commit'] == producer and
            report['case'] == config and len(report['runs']) == 2 and
            report['preserved_runtime_unchanged'] and not report['corpus_termination_policy_changed'],
            'Original profile is failed, incomplete or mismatched: '+profile)
    source = {safe_name(name): value for name, value in report['source_sha256_lf'].items()}
    relative_folder = HERE.relative_to(ROOT).as_posix()
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', producer, '--',
                                       relative_folder], text=True).splitlines()
    expected_sources = {name for name in tracked if str(PurePosixPath(name).parent) == relative_folder}
    expected_sources.add('Tests/Production/StockVessels/Observation.h')
    require(PROTOCOL <= set(source) == expected_sources, 'Original observer source manifest is incomplete')
    for name, expected in source.items():
        body = subprocess.check_output(['git', '-C', str(ROOT), 'show', producer+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n', b'\n')).hexdigest() == expected,
                'Original observer producer source differs: '+name)
    runtime_root = base/'stock-exit-runtime'
    preserved = json.loads((runtime_root/'test-runtime.json').read_text())
    runtime = json.loads((runtime_root/'control-reference-runtime.json').read_text())
    if preserved_root:
        require(sha_lf(runtime_root/'test-runtime.json') == sha_lf(preserved_root/'test-runtime.json') and
                sha_lf(runtime_root/'control-reference-runtime.json') == sha_lf(preserved_root/'control-reference-runtime.json'),
                'Original runtime metadata differs from the independently retained application/SDK/client')
    if metadata_pins:
        require(sha_lf(runtime_root/'test-runtime.json') == metadata_pins['runtime_metadata_sha256_lf'] and
                sha_lf(runtime_root/'control-reference-runtime.json') == metadata_pins['client_metadata_sha256_lf'],
                'Original runtime metadata differs from its independently audited pins')
    pins = json.loads((ROOT/'Tests/Production/Cockpit/Reference/provenance.json').read_text())
    require(preserved['source_commit'] == runtime['application_source'] == pins['application_source'] == config['application_source'] and
            runtime['runtime_archive_sha256'] == pins['runtime_artifacts'][configuration]['sha256'] and
            runtime['client_archive_sha256'] == pins['artifacts'][configuration]['sha256'] and runtime == report['runtime'],
            'Preserved original application/client provenance differs')
    protected = {name: value for name, value in {**preserved['files'], **runtime['client_files_sha256']}.items() if name != OBSERVER}
    require(protected == report['preserved_files_sha256'], 'Original application/SDK/client file set changed')
    if preserved_root:
        for name, expected in protected.items():
            require(digest(preserved_root/safe_name(name)) == expected, 'Independently retained original runtime drift: '+name)
    observer = runtime_root/OBSERVER
    require(digest(observer) == report['observer_sha256'], 'Executed original observer binary differs')
    build = base/'stock-exit-driver'
    cache = dict(line.split('=', 1) for line in (build/'CMakeCache.txt').read_text().splitlines()
                 if '=' in line and not line.startswith(('#', '//')))
    require(cache['CMAKE_BUILD_TYPE:STRING'] == configuration, 'Actual original observer build configuration differs')
    commands = json.loads((build/'compile_commands.json').read_text())
    expected_crt = 'MDd' if configuration == 'Debug' else 'MD'
    require(len(commands) == 1 and re.findall(r'(?:^|\s)[/-](MDd?)(?=\s|$)', commands[0]['command']) == [expected_crt],
            'Original observer actual CRT linkage differs')
    expected_modules = {}
    for name, value in {**protected, OBSERVER: report['observer_sha256']}.items():
        expected_modules.setdefault(PurePosixPath(name).name.casefold(), set()).add(value)
    results = []
    for repeat, recorded in enumerate(report['runs'], 1):
        out = capture/('run-'+str(repeat))
        for name, expected in recorded['files_sha256'].items():
            require(digest(out/safe_name(name)) == expected, 'Original attempt artifact changed: '+name)
        require(json.loads((out/'process-result.json').read_text())['returncode'] == recorded['returncode'] == 0,
                'Actual original process exit differs')
        require(json.loads((out/'invocation.json').read_text())['driver_sha256'] == report['observer_sha256'],
                'Original staged observer differs from the executed observer')
        actual = inspect(out, config, 'original-windows', recorded['returncode'])
        require(all(recorded[key] == value for key, value in actual.items()), 'Recomputed original exit outcome differs')
        require(recorded['actual_math'] == (out/'math-profile.txt').read_text().strip() and
                recorded['actual_math'] in ('fma3', 'sse2') and
                (math_profile != 'sse2' or recorded['actual_math'] == 'sse2'), 'Actual original CRT selection differs')
        module_audit(out, recorded, expected_modules)
        results.append({key: actual[key] for key in ('completed_frames', 'finalized_ticks', 'all_vessel_rows',
                       'docking_rows', 'declared_vessels', 'assertion_events', 'assertion_passes', 'renderer')})
    for name in ('stock-vessel-state.csv', 'stock-vessel-docks.csv', 'stock-exit-phases.csv'):
        require((capture/'run-1'/name).read_bytes() == (capture/'run-2'/name).read_bytes(),
                'Original repeat is not deterministic: '+name)
    gate = json.loads((capture/'gate-control.json').read_text())
    required_controls = {'missing_background_ship', 'missing_docking_port', 'missing_last_tick', 'nonfinite_state',
                         'duplicate_docking_port', 'missing_assertion', 'forged_completion', 'wrong_scenario',
                         'wrong_exit_code', 'incomplete_teardown', 'wrong_renderer'}
    require(gate['status'] == 'passed' and gate['original_capture_unchanged'] and
            required_controls <= {item['control'] for item in gate['controls']} and
            len({item['control'] for item in gate['controls']}) == len(gate['controls']),
            'Original damaged-evidence controls failed or incomplete')
    return dict(capture_sha256=digest(capture/'capture.json'), observer_sha256=digest(observer), runs=results,
                actual_math=report['runs'][0]['actual_math'], preserved_files=len(protected),
                runtime_metadata_sha256=digest(runtime_root/'test-runtime.json'),
                client_metadata_sha256=digest(runtime_root/'control-reference-runtime.json'),
                runtime_metadata_sha256_lf=sha_lf(runtime_root/'test-runtime.json'),
                client_metadata_sha256_lf=sha_lf(runtime_root/'control-reference-runtime.json'),
                gate_sha256=digest(capture/'gate-control.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts', 'download-manifest', 'output'):
        parser.add_argument('--'+name, required=True, type=lambda p: Path(p).resolve())
    for name in ('preserved-debug', 'preserved-release', 'metadata-lock'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve())
    parser.add_argument('--producer-commit', required=True)
    args = parser.parse_args(); config = settings()
    require(not args.output.exists(), 'Original exit audit output exists')
    require(re.fullmatch('[0-9a-f]{40}', args.producer_commit), 'Original observer producer must be immutable')
    require((args.preserved_debug and args.preserved_release) or args.metadata_lock,
            'Independent original runtime roots or audited metadata pins are required')
    pins = json.loads(args.metadata_lock.read_text()) if args.metadata_lock else None
    if pins:
        require(pins['status'] == 'audited-original-observations' and pins['automatic_refresh'] is False and
                pins['producer_commit'] == args.producer_commit and pins['application_source'] == config['application_source'],
                'Original metadata pins are not an audited immutable reference')
    downloads = json.loads(args.download_manifest.read_text())
    require(downloads['status'] == 'passed' and downloads['source_commit'] == args.producer_commit and
            len(downloads['artifacts']) == 4, 'Original archive matrix incomplete')
    result = dict(status='failed', phase6_complete=False, producer_commit=args.producer_commit,
                  application_source=config['application_source'], download_manifest_sha256=digest(args.download_manifest),
                  verifier_sha256=digest(Path(__file__)), profiles={}, build_pairs={}, corpus_termination_policy_changed=False)
    budgets = json.loads((ROOT/'Tests/Production/Cockpit/cases.json').read_text())
    try:
        for configuration in ('Debug', 'Release'):
            preserved_root = getattr(args, 'preserved_'+configuration.lower())
            for math_profile in ('automatic', 'sse2'):
                profile = configuration+'-'+math_profile
                entry = next(item for item in downloads['artifacts'] if item['profile'] == profile)
                require(entry['name'] == 'original-stock-lua-exit-'+profile and
                        digest(ROOT/safe_name(entry['path'])) == entry['sha256'] and
                        (ROOT/entry['path']).stat().st_size == entry['bytes'], 'Original archive identity differs')
                if pins:
                    pinned = next(item for item in pins['artifacts'] if item['profile'] == profile)
                    require(all(entry[key] == pinned[key] for key in ('id', 'name', 'bytes', 'sha256')),
                            'Original transport differs from its pinned artifact')
                result['profiles'][profile] = audit_profile(args.artifacts/profile, profile, config, args.producer_commit,
                    preserved_root, pins['runtime_metadata'][configuration] if pins else None)
        stops = {(run['completed_frames'], run['finalized_ticks'], run['all_vessel_rows'], run['docking_rows'])
                 for profile in result['profiles'].values() for run in profile['runs']}
        require(len(stops) == 1, 'Original profiles terminate at different boundaries')
        for math_profile in ('automatic', 'sse2'):
            left, right = [args.artifacts/(c+'-'+math_profile)/'stock-exit-original/run-1' for c in ('Debug', 'Release')]
            result['build_pairs'][math_profile] = compare_state(left, right, budgets)
        result.update(status='passed', processes=8, completed_frames=next(iter(stops))[0],
                      all_vessel_rows=sum(r['all_vessel_rows'] for p in result['profiles'].values() for r in p['runs']),
                      docking_rows=sum(r['docking_rows'] for p in result['profiles'].values() for r in p['runs']))
    except BaseException as error:
        result['error'] = str(error); raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Audited eight original exits, all vessels/ports, exact repeats, actual modules, source and paired build budgets')


if __name__ == '__main__': main()
