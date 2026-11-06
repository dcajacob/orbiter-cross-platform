#!/usr/bin/env python3
"""Compile the actual tracking-preset writer and check its exact Windows format."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

PREFIX = r'''
#include <cstdio>
#include <cstring>
#include <iostream>
using std::sprintf;
using std::strcat;
struct Body { const char *name; const char *Name() const { return name; } };
struct CameraMode_Track {
    enum TrackMode { TM_CURRENT, TM_RELATIVE, TM_ABSDIR, TM_GLOBAL, TM_TARGETTOREF, TM_TARGETFROMREF };
    Body *target, *ref;
    double fov, reldist, phi, theta;
    TrackMode tmode;
    void Store(char *str);
};
'''
SUFFIX = r'''
int main() {
    const char *modes[] = {"CURRENT", "RELATIVE", "ABSDIR", "GLOBAL", "TARGETTOREF", "TARGETFROMREF"};
    Body vessel{"STS-101"}, percent{"Survey%25"}, earth{"Earth"};
    Body *targets[] = {nullptr, &vessel, &percent};
    for (auto target : targets) for (int mode = 0; mode != 6; ++mode) {
        CameraMode_Track camera{target, &earth, 50.0, 2.890, -0.009, -1.229,
                              static_cast<CameraMode_Track::TrackMode>(mode)};
        char actual[256] = {}, expected[256] = {};
        camera.Store(actual);
        std::snprintf(expected, sizeof expected, "Track:%s:50.00:%s 2.890 -0.009 -1.229%s",
                      target ? target->Name() : "-", modes[mode], mode >= 4 ? " Earth" : "");
        if (std::strcmp(actual, expected)) {
            std::cerr << "expected: " << expected << "\nactual: " << actual << '\n';
            return 1;
        }
        std::cout << actual << '\n';
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler')
    parser.add_argument('--msvc', action='store_true')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    source_path = args.source or Path(__file__).resolve().parents[3] / 'Src/Orbiter/Camera.cpp'
    source = source_path.read_bytes().replace(b'\r\n', b'\n').decode('cp1252')
    start = source.index('void CameraMode_Track::Store (char *str)')
    end = source.index('void CameraMode_Track::GetDescr', start)
    method = source[start:end]
    assert method.count('"Track:%s:%0.2f:%s %0.3f %0.3f %0.3f"') == 1
    assert not args.output.exists(), 'Fresh output required'
    args.output.mkdir(parents=True)
    compiler = args.compiler or shutil.which('cl' if args.msvc else 'c++')
    assert compiler, 'C++ compiler required'
    report = dict(status='running', source_sha256_lf=hashlib.sha256(source.encode('cp1252')).hexdigest(),
                  compiler=compiler, positive_presets=18, controls={}, commands=[])

    def execute(name, body, strict=True):
        path = args.output / (name + '.cpp')
        executable = args.output / (name + ('.exe' if args.msvc else ''))
        path.write_text(PREFIX + body + SUFFIX)
        if args.msvc:
            command = [compiler, '/nologo', '/std:c++17', '/EHsc', '/D_CRT_SECURE_NO_WARNINGS', '/W4', *(['/WX'] if strict else []), str(path.resolve()), '/Fe:' + str(executable.resolve())]
        else:
            command = [compiler, '-std=c++17', '-Wall', '-Wextra', *(['-Werror'] if strict else []), str(path.resolve()), '-o', str(executable.resolve())]
        built = subprocess.run(command, cwd=args.output, capture_output=True, text=True)
        (args.output / (name + '-build.log')).write_text(built.stdout + built.stderr)
        record = dict(name=name, argv=command, compiler_returncode=built.returncode)
        report['commands'].append(record)
        if built.returncode:
            return False
        run = subprocess.run([str(executable.resolve())], capture_output=True, text=True)
        (args.output / (name + '-run.log')).write_text(run.stdout + run.stderr)
        record['actual_returncode'] = run.returncode
        if run.returncode == 0:
            assert len(run.stdout.splitlines()) == 18
        return run.returncode == 0

    assert execute('actual-store', method), 'Actual tracking-preset writer differs from original Windows output'
    changes = {
        'invalid-percent-colon': ('Track:%s:%0.2f', 'Track:%s%:%0.2f'),
        'changed-fov-precision': ('%0.2f:%s', '%0.3f:%s'),
        'changed-mode': ('"RELATIVE"', '"GLOBAL"'),
        'missing-reference': ('strcat (str, ((Body*)ref)->Name());', '/* omitted reference */'),
    }
    for name, (before, after) in changes.items():
        assert method.count(before) == 1
        assert not execute(name, method.replace(before, after, 1)), 'Damaged writer accepted: ' + name
        report['controls'][name] = 'rejected'
    if args.baseline:
        original = args.baseline.read_bytes()
        text = original.replace(b'\r\n', b'\n').decode('cp1252')
        a = text.index('void CameraMode_Track::Store (char *str)')
        b = text.index('void CameraMode_Track::GetDescr', a)
        legacy = text[a:b]
        assert legacy == method.replace('Track:%s:', 'Track:%s%:', 1)
        matches = execute('inherited-store-baseline', legacy, strict=False)
        assert matches == (sys.platform == 'win32'), 'Inherited CRT behavior differs from the observed failure'
        assert args.baseline.read_bytes() == original
        report['baseline'] = dict(source_sha256=hashlib.sha256(original).hexdigest(),
                                  matches_established_Windows_output=matches, source_unchanged=True)
    assert source_path.read_bytes().replace(b'\r\n', b'\n').decode('cp1252') == source
    report.update(status='passed', source_unchanged=True,
                  scope='Actual Store method, all six modes, null/named/percent-bearing targets, exact Windows-format tokens and four damaged-source controls. Full mission reload and frame/state parity remain separate gates.')
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'positive_presets', 'controls', 'source_unchanged')}, indent=2))


if __name__ == '__main__':
    main()
