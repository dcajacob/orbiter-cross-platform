#!/usr/bin/env python3
"""Require genuine Xlib unload and clean, unsuppressed resource/locale lifetimes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument('--output', type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument('--display', action='store_true', help='Also test local input methods and heap/mapped compose caches')
    args = parser.parse_args()
    if not args.library.is_file() or args.output.exists():
        raise ValueError('A real Xlib library and a new output directory are required')
    args.output.mkdir(parents=True)
    report = dict(status='pending', library=str(args.library), library_sha256=digest(args.library),
                  fixture_sha256=digest(HERE/'Probe.cpp'), cases={}, failures={})
    command = ['c++', '-std=c++17', '-g', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-gnu-unique',
               '-pthread', str(HERE/'Probe.cpp'), '-ldl', '-o', str(args.output/'xlib-probe')]
    report['build_command'] = command
    try:
        with (args.output/'build.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                           LSAN_OPTIONS='', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        cache = args.output/'compose-cache'
        cache.mkdir(mode=0o700)
        compose = args.output/'Compose'
        compose.write_text('<Multi_key> <a> <e> : "æ" U00E6\n', encoding='utf8')
        # Xlib requires a cache mtime strictly newer than its input file.
        timestamp = time.time()-60
        os.utime(compose, (timestamp, timestamp))
        environment.update(XCOMPOSECACHE=str(cache)+'/', XCOMPOSEFILE=str(compose))
        cases = [(name, name) for name in ('load-only', 'initialize', 'resources-C', 'resources-UTF8',
                                          'pool', 'threads', 'owners', 'reload')]
        if args.display:
            if os.geteuid() == 0:
                raise ValueError('Compose-cache qualification requires an unprivileged user')
            cases.extend([('compose-write', 'display-heap'), ('compose-mapped', 'display-mapped'),
                          ('compose-invalidations', 'display-heap'), ('compose-mixed', 'display-mixed')])
        for name, mode in cases:
            if name == 'compose-invalidations':
                # Keep every generated cache stale, forcing three overlapping
                # IMs to retain separate heap generations until library unload.
                timestamp = time.time()+60
                os.utime(compose, (timestamp, timestamp))
            elif name == 'compose-mixed':
                timestamp = time.time()-60
                os.utime(compose, (timestamp, timestamp))
            command = [str(args.output/'xlib-probe'), str(args.library), mode]
            log = args.output/(name+'.log')
            with log.open('w') as stream:
                process = subprocess.run(command, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=60)
            text = log.read_text()
            leaks = re.search(r'SUMMARY: AddressSanitizer: (\d+) byte\(s\) leaked in (\d+) allocation\(s\)', text)
            result = dict(exit_code=process.returncode, log_sha256=digest(log),
                          library_unloaded='final_owner_released=true library_unloaded=true' in text,
                          leaked_bytes=int(leaks[1]) if leaks else 0,
                          leaked_allocations=int(leaks[2]) if leaks else 0)
            report['cases'][name] = result
            if process.returncode != 0 or not result['library_unloaded'] or any(
                    marker in text for marker in ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:')):
                report['failures'][name] = 'Xlib lifetime test failed; inspect '+log.name
            if name.startswith('compose-') and not any(p.is_file() for p in cache.iterdir()):
                report['failures'][name] = 'Compose cache was not written; mapped/heap paths are unproven'
            print(name, result, flush=True)
        report['compose_files'] = {p.name: digest(p) for p in cache.iterdir() if p.is_file()}
        report['status'] = 'failed' if report['failures'] else 'passed'
        if report['failures']:
            raise ValueError('Unsuppressed Xlib lifetime gate failed')
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (args.output/'xlib-verification.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
