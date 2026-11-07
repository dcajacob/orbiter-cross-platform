#!/usr/bin/env python3
"""Coordinate the existing persistence collectors and independent readers locally."""
import argparse
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import threading
import traceback

from contracts import (PHASES, PROFILES, Scope, atomic_json, load, require,
                       reusable_capture, sha)
from processes import OwnedProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--verify-reuse-only', action='store_true', help='Audit declared closed stages only; launch no collectors')
    args = parser.parse_args()
    request_sha = sha(args.request)
    request = load(args.request)
    require(request['schema'] == 1, 'Unknown coordinator request schema')
    owner = Path(request['owner']).resolve()
    producer = request['collector_commit']
    require(subprocess.check_output(['git', '-C', str(owner), 'rev-parse', 'HEAD'], text=True).strip() == producer,
            'Owning collector checkout must remain at its declared immutable commit')
    scope = Scope.make(request['selected_cases'])
    if args.verify_reuse_only:
        require(request.get('reuse') and set(request['reuse']) <= {p+'/'+s for p in PROFILES for s in PHASES},
                'Explicit valid closed stages required for reuse-only audit')
    require(tuple(request['profiles']) == PROFILES and set(request['packages']) == set(PROFILES),
            'All four independently declared profile packages required')
    require(request['jobs_per_collector'] in (1, 2), 'At most two simulator jobs per collector')
    require(not args.output.exists(), 'Fresh coordinator output required')
    sys.path.insert(0, str(owner / 'Tests/Production/RemainingStockPersistence'))
    import observations
    reader = observations.bind_owner(owner, producer)
    spec = importlib.util.spec_from_file_location('closeout_pair_reader', owner / 'Tests/Production/RemainingStockPersistence/audit.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    config = reader.native.settings(reader.protocols.V2)
    args.output.mkdir(parents=True)
    lock = threading.RLock()
    stop = threading.Event()
    active = {}
    report = dict(status='running', schema=1, request_sha256=request_sha,
                  coordinator_sha256=sha(__file__), collector_commit=producer,
                  diagnostic_only=scope.selected, cases=list(scope.cases), stages={}, failures={},
                  native_admission_qualified=False, phase6_complete=False,
                  maximum_native_simulators=2 * request['jobs_per_collector'])

    def save():
        with lock:
            atomic_json(args.output / 'status.json', report)

    def cancel(_signal=None, _frame=None):
        stop.set()
        with lock:
            records = list(active.items())
        for key, process in records:
            receipt = process.cancel()
            with lock:
                report['stages'][key]['process'] = receipt
        save()

    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)

    def inspect(root, profile, phase, selected):
        return observations.inspect_native(root, owner, reader, profile, phase, selected=selected)

    def command(profile, phase, output):
        package = Path(request['packages'][profile])
        argv = [sys.executable, '-B', str(owner / 'Tests/Production/RemainingStockPersistence/capture_native.py'),
                '--build', str(package / 'engine'), '--build-record', str(package / 'build.json'),
                '--output', str(output), '--phase', phase, '--jobs', str(request['jobs_per_collector'])]
        if 'runtime_owner' in request:argv+=['--runtime-owner',request['runtime_owner']]
        if 'observer_delay_ms' in request:
            require(type(request['observer_delay_ms']) is int and request['observer_delay_ms'] in (0,120),'Explicit observer pacing required')
            argv+=['--observer-delay-ms',str(request['observer_delay_ms'])]
        for name in ('assets', 'data', 'planets', 'compositor-tools', 'gtk-plugin', 'gtk-build-record'):
            argv += ['--' + name, request['inputs'][name]]
        for path in request['inputs']['libraries']:
            argv += ['--library', path]
        if scope.selected:
            for case in scope.cases:
                argv += ['--case', case]
        if phase == 'windows-save-reload':
            for name in ('windows-parent-capture', 'windows-build', 'preserved'):
                argv += ['--' + name, request['windows'][profile][name]]
        return argv

    def compare_case(profile, phase, output, case):
        windows = request['windows'][profile]
        reference = Path(windows['writer' if phase == 'stock-writer' else 'reload'])
        pairs = {}
        for repeat in (1, 2):
            name = case + '-' + str(repeat)
            if phase == 'windows-save-reload':
                # compare_pair alone does not enforce the exact Windows input.
                native_input = load(output / name / 'persistence-input.json')
                windows_input = load(reference / name / 'persistence-input.json')
                saved = Path(windows['windows-parent-capture']) / name / 'Scenarios/(Current state).scn'
                require(native_input['saved_input_sha256'] == windows_input['saved_input_sha256'] == sha(saved),
                        'Paired reloads must consume the same exact hashed Windows save')
            pairs[str(repeat)] = audit.compare_pair(reference / name, output / name, reader, config)
        return pairs

    def profile_run(profile):
        for phase in PHASES:
            if args.verify_reuse_only and profile+'/'+phase not in request['reuse']:
                continue
            if stop.is_set():
                return
            key = profile + '/' + phase
            output = args.output / (profile + '-' + phase)
            process = None
            stage = dict(status='starting', output=str(output), comparisons={})
            with lock:
                report['stages'][key] = stage
                save()
            try:
                reused = request.get('reuse', {}).get(key)
                if reused:
                    output = Path(reused['path']).resolve()
                    actual = reusable_capture(output, reused['capture_sha256'], scope, profile, phase,
                        reused['collector_commit'], request['runtime_commit'], inspect)
                    with lock:
                        stage.update(output=str(output), status='reused-after-independent-audit', audit=actual)
                    for case in scope.cases:
                        pairs = compare_case(profile, phase, output, case)
                        with lock:
                            stage['comparisons'][case] = pairs
                else:
                    argv = command(profile, phase, output)
                    with (args.output / (profile + '-' + phase + '.log')).open('w') as log:
                        with lock:
                            if stop.is_set():
                                return
                            process = OwnedProcess(argv, cwd=owner, stdout=log, stderr=subprocess.STDOUT)
                            active[key] = process
                            stage.update(status='running', argv=argv, process=process.receipt())
                            save()
                        checked = set()
                        while True:
                            process.discover()
                            try:
                                captured = load(output / 'capture.json')
                            except (FileNotFoundError, json.JSONDecodeError):
                                captured = None
                            if captured:
                                require(captured.get('runtime_owner',str(owner))==request.get('runtime_owner',str(owner)) and
                                        captured.get('observer_delay_ms',120)==request.get('observer_delay_ms',120),
                                        'Captured runtime owner or observer pacing differs from request')
                                require(not captured['failures'], 'Actual capture failure: ' + str(captured['failures']))
                                require(captured['status'] not in ('failed', 'incomplete'), 'Collector failed or incomplete')
                                for case in scope.cases:
                                    if case in captured['cases'] and case not in checked:
                                        pairs = compare_case(profile, phase, output, case)
                                        with lock:
                                            stage['comparisons'][case] = pairs
                                            save()
                                        checked.add(case)
                            code = process.process.poll()
                            if code is not None:
                                with lock:
                                    stage['process'] = process.receipt()
                                    active.pop(key, None)
                                require(code == 0 and not process.cancelled,
                                        'Collector failed or was cancelled')
                                # The collector can atomically finalize after our
                                # last live read and before poll observes exit.
                                # Only the closed manifest establishes terminal
                                # scope, including cases completed in that gap.
                                captured = load(output / 'capture.json')
                                require(captured.get('runtime_owner',str(owner))==request.get('runtime_owner',str(owner)) and
                                        captured.get('observer_delay_ms',120)==request.get('observer_delay_ms',120),
                                        'Closed runtime owner or observer pacing differs from request')
                                scope.inspect_terminal(captured, profile, phase)
                                require(captured['producer_commit'] == producer and
                                        captured['runtime_source_commit'] == request['runtime_commit'],
                                        'Collected source/runtime identity differs')
                                for case in scope.cases:
                                    if case not in checked:
                                        pairs = compare_case(profile, phase, output, case)
                                        with lock:
                                            stage['comparisons'][case] = pairs
                                        checked.add(case)
                                # Completed stages are audited even if another profile
                                # has just failed. They remain reusable scoped evidence.
                                actual = inspect(output, profile, phase, scope.selection)
                                require(set(checked) == set(scope.cases), 'Complete case comparisons required')
                                with lock:
                                    stage.update(audit=actual, status='collected-compared-and-independently-audited')
                                break
                            if stop.wait(.25):
                                process.cancel()
                                raise ValueError('Cancelled after qualification failure or operator signal')
                with lock:
                    save()
            except BaseException as error:
                with lock:
                    stage.update(status='cancelled' if process and process.cancelled else 'failed',
                                 error=str(error), traceback=traceback.format_exc())
                    report['failures'][key] = str(error)
                cancel()
                if process and process.process.poll() is None:
                    process.cancel()
                with lock:
                    if process:
                        stage['process'] = process.receipt()
                    active.pop(key, None)
                    save()
                return

    save()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(profile_run, PROFILES))
    require(sha(args.request) == request_sha, 'Coordinator request changed during execution')
    report['status'] = ('stopped-after-qualification-failure' if report['failures'] else
                        'cancelled' if stop.is_set() else
                        'audited-reusable-captures-only' if args.verify_reuse_only else
                        'diagnostic-collected-and-audited' if scope.selected else
                        'full-native-collected-and-audited-awaiting-closeout')
    save()
    return int(bool(report['failures']) or stop.is_set())


if __name__ == '__main__':
    sys.exit(main())
