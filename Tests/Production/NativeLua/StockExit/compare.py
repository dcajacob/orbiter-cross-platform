#!/usr/bin/env python3
"""Compare a complete native stock exit against its independently audited Windows profile."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

from contract import HERE, ROOT, digest, inspect, require, settings
from audit_original import PROTOCOL, safe_name

sys.path.insert(0, str(HERE.parents[1]/'StockVessels'))
from verify_original import compare_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'original-audit', 'native', 'build-record', 'runtime-root', 'output'):
        parser.add_argument('--'+name, required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--profile', required=True, choices=tuple(c+'-'+m for c in ('Debug', 'Release') for m in ('automatic', 'sse2')))
    parser.add_argument('--runtime-source-commit', required=True)
    args = parser.parse_args(); config = settings()
    require(not args.output.exists(), 'Stock exit comparison output exists')
    require(re.fullmatch('[0-9a-f]{40}', args.runtime_source_commit), 'Runtime source must be immutable')
    audit = json.loads(args.original_audit.read_text())
    require(audit['status'] == 'passed' and len(audit['profiles']) == 4 and audit['processes'] == 8 and
            audit['application_source'] == config['application_source'], 'Complete audited original reference required')
    require(audit['verifier_sha256'] == digest(HERE/'audit_original.py'), 'Original audit verifier identity differs')
    original = args.original/'stock-exit-original'
    original_report = json.loads((original/'capture.json').read_text())
    pinned = audit['profiles'][args.profile]
    require(digest(original/'capture.json') == pinned['capture_sha256'], 'Original profile differs from its audit')
    native = json.loads((args.native/'capture.json').read_text())
    configuration, math_profile = args.profile.split('-', 1)
    require(native['status'] == 'captured-awaiting-original-audit' and not native['failures'] and len(native['runs']) == 2 and
            native['host'] == 'native-linux' and native['configuration'] == configuration and
            native['math_profile'] == math_profile and native['case'] == config and native['sources_and_runtime_unchanged'],
            'Native exit capture failed, incomplete or misidentified')
    require(re.fullmatch('[0-9a-f]{40}', native['producer_commit']), 'Native producer is not immutable')
    sources = {safe_name(name): value for name, value in native['source_sha256_lf'].items()}
    require(PROTOCOL <= set(sources), 'Native observer source manifest incomplete')
    for name, expected in sources.items():
        body = subprocess.check_output(['git', '-C', str(ROOT), 'show', native['producer_commit']+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n', b'\n')).hexdigest() == expected, 'Native observer producer source differs: '+name)
    reference_sources = {safe_name(name): value for name, value in original_report['source_sha256_lf'].items()}
    for name in ('Tests/Production/NativeLua/StockExit/case.json', 'Tests/Production/StockVessels/Observation.h'):
        require(sources[name] == reference_sources[name], 'Original/native observation fields or stock source differ')
    build = json.loads(args.build_record.read_text())
    require(build['status'] == 'built', 'Native runtime build record incomplete')
    owning = build.get('source_sha256_lf', build.get('source_sha256'))
    require(owning and set(owning) == set(json.loads((HERE.parents[1]/'phase3-extraction.lock.json').read_text())['files']),
            'Native owning-source build ledger incomplete')
    for name, expected in owning.items():
        body = subprocess.check_output(['git', '-C', str(ROOT), 'show', args.runtime_source_commit+':'+safe_name(name)])
        require(hashlib.sha256(body.replace(b'\r\n', b'\n')).hexdigest() == expected,
                'Native built input differs from the immutable runtime source: '+name)
    for name, expected in build['runtime_files_sha256'].items():
        require(digest(args.runtime_root/safe_name(name)) == expected, 'Retained native package changed: '+name)
    marker = '/Src/Orbiter/Production/NativeApplication.cpp'
    anchor = next(name for name in native['protected_files_sha256'] if name.endswith(marker))
    recorded_root = Path(anchor[:-len(marker)])
    for name, expected in native['protected_files_sha256'].items():
        relative = Path(name).relative_to(recorded_root)
        require(digest(args.runtime_root/relative) == expected, 'Captured source or runtime binary changed: '+str(relative))
    cache_path = next(Path(name) for name in native['protected_files_sha256'] if name.endswith('/CMakeCache.txt'))
    cache = dict(line.split('=', 1) for line in (args.runtime_root/cache_path.relative_to(recorded_root)).read_text().splitlines()
                 if '=' in line and not line.startswith(('#', '//')))
    require(cache['CMAKE_BUILD_TYPE:STRING'] == configuration and cache['ORBITER_MATH_FORCE_SSE2:BOOL'] ==
            ('ON' if math_profile == 'sse2' else 'OFF'), 'Actual native configuration or math selection differs')
    result = dict(status='failed', phase6_complete=False, profile=args.profile,
                  original_audit_sha256=digest(args.original_audit), original_capture_sha256=pinned['capture_sha256'],
                  native_capture_sha256=digest(args.native/'capture.json'), build_record_sha256=digest(args.build_record),
                  runtime_source_commit=args.runtime_source_commit, source_sha256=digest(Path(__file__)), runs=[])
    budgets = json.loads((ROOT/'Tests/Production/Cockpit/cases.json').read_text())
    try:
        for repeat, recorded in enumerate(native['runs'], 1):
            left = original/('run-'+str(repeat)); right = args.native/('run-'+str(repeat))
            for path, expected in original_report['runs'][repeat-1]['files_sha256'].items():
                require(digest(left/safe_name(path)) == expected, 'Audited original artifact changed')
            for path, expected in recorded['files_sha256'].items():
                require(digest(right/safe_name(path)) == expected, 'Captured native artifact changed')
            actual = inspect(right, config, 'native-linux', recorded['returncode'])
            require(all(recorded[key] == value for key, value in actual.items() if key != 'renderer' or key in recorded),
                    'Recomputed native exit result differs')
            require(actual['completed_frames'] == original_report['runs'][repeat-1]['completed_frames'] == audit['completed_frames'] and
                    actual['finalized_ticks'] == original_report['runs'][repeat-1]['finalized_ticks'], 'Original/native exit boundary differs')
            require(recorded['actual_math'] == json.loads((right/'numerics.json').read_text())['math'],
                    'Recorded native CRT differs from actual runtime numerics')
            require(recorded['actual_math'] == 'amd-6121d02-'+pinned['actual_math'], 'Actual original/native CRT implementations differ')
            errors = compare_state(left, right, budgets)
            require((left/'stock-exit-phases.csv').read_bytes().replace(b'\r\n', b'\n') ==
                    (right/'stock-exit-phases.csv').read_bytes().replace(b'\r\n', b'\n'), 'Original/native completion sequence differs')
            result['runs'].append(dict(status='passed', maxima=errors, completed_frames=actual['completed_frames'],
                                       all_vessel_rows=actual['all_vessel_rows'], docking_rows=actual['docking_rows'],
                                       actual_math=recorded['actual_math'], native_lifecycle=actual['lifecycle']))
        result['status'] = 'passed'
    except BaseException as error:
        result['error'] = str(error); raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(args.profile, 'two complete stock exits match the original Windows reference and unchanged budgets')


if __name__ == '__main__': main()
