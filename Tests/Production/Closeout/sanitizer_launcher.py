#!/usr/bin/env python3
"""Check compiler dispatch and Python/native sanitizer controls before full builds."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

DISPATCH = r'''
#include <cstdlib>
struct Stepper {
    using Advance = void (Stepper::*)(double, int, int);
    struct Mode { Advance function; };
    static Mode modes[5];
    int level = 0;
    double result = 0;
    virtual ~Stepper() = default;
    __attribute__((noinline)) void advance(double dt, int count, int ordinal) {
        result += dt * count + ordinal;
    }
    __attribute__((noinline)) void run(int index) {
        level = index;
        DISPATCH_CALL
    }
};
Stepper::Mode Stepper::modes[5] = {{&Stepper::advance}, {&Stepper::advance},
    {&Stepper::advance}, {&Stepper::advance}, {&Stepper::advance}};
int main(int argc, char** argv) {
    Stepper body;
    const int index = argc == 2 ? std::strtol(argv[1], nullptr, 10) : 0;
    for (int repeat = 0; repeat < 32; ++repeat) body.run(index);
    return body.result == 16.0 ? 0 : 2;
}
'''
ORIGINAL = '((*this).*(modes[level].function)) (0.25, 2, 0);'
BOUND = 'const Advance selected = modes[level].function;\n        ((*this).*selected) (0.25, 2, 0);'
PROBE = r'''
#include <cstdlib>
extern "C" int native_value() { return 42; }
extern "C" __attribute__((noinline)) void native_leak() {
    volatile char* memory = static_cast<char*>(std::malloc(4096));
    memory[0] = 1;
}
'''


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args(); root = args.output
    require(not root.exists(), 'Fresh sanitizer control output required')
    root.mkdir(parents=True)
    report = dict(status='running', commands=[], dispatch={}, phase6_complete=False,
                  scope='Small compiler/launcher controls only; no simulation acceptance')

    def save():
        (root/'controls.json').write_text(json.dumps(report, indent=2)+'\n')

    def run(label, argv, env=None):
        path = root/(label+'.log')
        with path.open('w') as log:
            process = subprocess.Popen(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT, env=env)
            item = dict(label=label, argv=list(map(str, argv)), actual_pid=process.pid,
                        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            report['commands'].append(item); save()
            item['actual_returncode'] = process.wait(timeout=60)
        item.update(log_sha256=sha(path), finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        return item['actual_returncode'], path.read_text(errors='replace')

    try:
        compiler = os.environ.get('CXX', 'c++')
        code, text = run('compiler-version', [compiler, '--version'])
        require(code == 0, 'Actual compiler version unavailable'); report['compiler_version'] = text
        flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-sanitize-recover=all']
        for optimization in ('-O0', '-O3'):
            result = {}; report['dispatch'][optimization] = result
            for variant, call in (('original', ORIGINAL), ('bound', BOUND)):
                label = variant+'-'+optimization[1:]; source = root/(label+'.cpp'); binary = root/label
                source.write_text(DISPATCH.replace('DISPATCH_CALL', call))
                code, text = run(label+'-compile', [compiler, *flags, optimization, source, '-o', binary])
                require(code == 0, 'Dispatch control failed to compile: '+label)
                code, text = run(label+'-valid', [binary, '0'])
                result[variant] = dict(source_sha256=sha(source), binary_sha256=sha(binary), valid_returncode=code)
                if variant == 'original':
                    require(code == 0 or any(marker in text for marker in ('runtime error:', 'AddressSanitizer:')),
                            'Original dispatch failed for an unrelated reason')
                else:
                    require(code == 0, 'Bound member-pointer dispatch failed')
                    code, text = run(label+'-invalid', [binary, '9'])
                    require(code != 0 and ('runtime error:' in text or 'AddressSanitizer:' in text),
                            'Actual invalid array index was not rejected with sanitizers')
                    result[variant]['invalid_index_rejected'] = True
        source = root/'python-probe.cpp'; library = root/'python-probe.so'; source.write_text(PROBE)
        code, text = run('python-probe-compile', [compiler, *flags, '-shared', '-fPIC', source, '-o', library])
        require(code == 0, 'Native Python sanitizer probe failed to compile')
        asan = subprocess.check_output([compiler, '-print-file-name=libasan.so'], text=True).strip()
        require(Path(asan).is_file(), 'Actual compiler ASan runtime missing')
        environment = dict(os.environ, LD_PRELOAD=asan, PYTHONMALLOC='malloc')
        script = 'import ctypes,sys; p=ctypes.CDLL(sys.argv[1]); assert p.native_value()==42'
        code, text = run('python-clean', [sys.executable, '-B', '-c', script, library], environment)
        require(code == 0, 'Python/native launcher has an unsuppressed sanitizer diagnostic')
        code, text = run('python-native-leak', [sys.executable, '-B', '-c', script+'; p.native_leak()', library], environment)
        require(code != 0 and 'LeakSanitizer' in text and '4096' in text,
                'Actual native leak loaded through Python was not rejected')
        report.update(status='passed-compiler-and-unsuppressed-sanitizer-launcher-controls',
                      python=sys.executable, python_allocator='malloc', asan_path=asan, asan_sha256=sha(asan),
                      native_leak_rejected=True, native_probe_sha256=sha(library),
                      original_dispatch_failed=any(v['original']['valid_returncode'] != 0 for v in report['dispatch'].values()))
    except BaseException as error:
        report.update(status='failed', error=str(error)); raise
    finally:
        save()
    print(report['status'])


if __name__ == '__main__':
    main()
