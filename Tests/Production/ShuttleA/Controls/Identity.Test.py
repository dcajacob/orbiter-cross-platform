#!/usr/bin/env python3
"""Reject mislabeled real builds and altered copied binaries before comparison."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import capture as controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('debug-build', 'release-build', 'assets', 'data', 'planets', 'output'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    watched = [b/name for b in (args.debug_build, args.release_build)
               for name in ('orbiter-production', 'liborbiter_production_vessels.so', 'CMakeCache.txt')]
    before = {str(p): controls.digest(p) for p in watched}
    result = dict(status='failed', checks={}, protected_sha256=before)
    try:
        controls.native_build_identity(args.debug_build, 'Debug', 'automatic')
        controls.native_build_identity(args.release_build, 'Release', 'automatic')
        for label, build, configuration, profile, message in (
            ('debug_labeled_release', args.debug_build, 'Release', 'automatic', 'actual build: Debug'),
            ('automatic_labeled_sse2', args.release_build, 'Release', 'sse2', 'math profile differs')):
            try:
                controls.native_build_identity(build, configuration, profile)
            except ValueError as error:
                controls.require(message in str(error), 'Identity rejected for another reason')
                result['checks'][label] = str(error)
            else:
                raise ValueError('Mislabeled actual build was accepted')
        rejected = args.output/'rejected-capture'
        argv = [sys.executable, '-B', str(controls.HERE/'capture.py'), '--executable', str(args.debug_build/'orbiter-production'),
                '--configuration', 'Release', '--math-profile', 'automatic', '--runtime-source-commit',
                '09eeed2091b36b18681cd10616b608248008ddaa', '--output', str(rejected)]
        for name in ('assets', 'data', 'planets'):
            argv += ['--'+name, str(getattr(args, name))]
        completed = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.output/'mislabeled-capture.log').write_text(completed.stdout)
        controls.require(completed.returncode != 0 and 'actual build: Debug' in completed.stdout and not rejected.exists(),
                         'Mislabeled capture created output or started a session')
        result['checks']['capture_rejected_before_session'] = True
        binary = args.release_build/'liborbiter_production_vessels.so'
        copied = args.output/binary.name
        shutil.copyfile(binary, copied)
        hashes = {binary.name: controls.digest(binary)}
        controls.verify_runtime(args.output, hashes)
        with copied.open('r+b') as stream:
            value = stream.read(1)
            stream.seek(0)
            stream.write(bytes([value[0] ^ 1]))
        try:
            controls.verify_runtime(args.output, hashes)
        except ValueError as error:
            controls.require('runtime binary changed' in str(error), 'Modified binary rejected for another reason')
            result['checks']['altered_engine_rejected'] = True
        else:
            raise ValueError('Altered runtime engine was accepted')
        controls.require(before == {str(p): controls.digest(p) for p in watched}, 'Identity tests changed retained builds')
        result.update(status='passed', retained_binaries_and_caches_unchanged=True)
    finally:
        (args.output/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Rejected wrong configuration, wrong math profile and altered copied engine; retained builds unchanged')


if __name__ == '__main__':
    main()
