#!/usr/bin/env python3
"""Build and run the allocator contract test using an actual configured Mesa tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesa-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('The executable-code fixture requires native Linux x86-64')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    database = args.mesa_build.resolve() / 'compile_commands.json'
    selected = {'rtasm_execmem.c', 'u_mm.c', 'futex.c'}
    objects = []
    report = dict(status='building', sources={}, commands=[])
    try:
        with (output / 'build.log').open('w') as log:
            for item in json.loads(database.read_text()):
                name = Path(item['file']).name
                if name not in selected:
                    continue
                if name in report['sources']:
                    raise ValueError('Ambiguous Mesa source: ' + name)
                source = (Path(item['directory']) / item['file']).resolve()
                report['sources'][name] = dict(path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest())
                command = shlex.split(item['command'])
                obj = output / (name + '.o')
                command[command.index('-o') + 1] = str(obj)
                for flag in ('-MF', '-MQ'):
                    if flag in command:
                        i = command.index(flag)
                        del command[i:i + 2]
                command = [x for x in command if x != '-MD']
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-O1']
                report['commands'].append(command)
                subprocess.run(command, cwd=item['directory'], check=True, stdout=log, stderr=subprocess.STDOUT)
                objects.append(str(obj))
            if set(report['sources']) != selected:
                raise ValueError('The configured Mesa tree lacks required allocator sources')
            executable = output / 'allocator-test'
            command = ['c++', '-std=c++17', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                       '-pthread', str(HERE / 'Allocator.Test.cpp'), *objects, '-o', str(executable)]
            report['commands'].append(command)
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                   LSAN_OPTIONS='', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        result = subprocess.run([str(executable)], env=env, capture_output=True, text=True, timeout=60)
        (output / 'run.log').write_text(result.stdout + result.stderr)
        report.update(status='passed' if result.returncode == 0 else 'failed', exit_code=result.returncode,
                      fixture_sha256=hashlib.sha256((HERE / 'Allocator.Test.cpp').read_bytes()).hexdigest())
        print(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Mesa allocator contract test failed')
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
