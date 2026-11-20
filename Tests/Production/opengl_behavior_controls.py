"""Replay frozen flights on their original physics and compare OpenGL with its pinned parent."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import behavior_suite as suite
from PhysicsV2.transforms import BASELINE as ORIGINAL_PHYSICS
from mesa_runtime import require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OPENGL_PARENT = '361c4d1110338cadce9a00ccd2c37dcca333b0db'


def build_control(source, build, revision, configuration):
    subprocess.run(['git', '-C', source, 'checkout', '--quiet', '--detach', revision], check=True)
    head = subprocess.check_output(['git', '-C', source, 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', source, 'status', '--porcelain'])
    require(head == revision and not dirty, 'Expected a clean checkout of ' + revision)
    subprocess.run(['cmake', '-S', source, '-B', build, '-G', 'Ninja',
                    '-DCMAKE_BUILD_TYPE=' + configuration, '-DCMAKE_C_COMPILER=cl', '-DCMAKE_CXX_COMPILER=cl',
                    '-DORBITER_BUILD_D3D9CLIENT=ON', '-DORBITER_BUILD_XRSOUND=OFF', '-DORBITER_MAKE_DOC=OFF',
                    '-DORBITER_MAKE_TESTS=ON', '-DORBITER_PORTABLE_REFERENCE_CAPTURE=ON',
                    '-DORBITER_PRODUCTION_REFERENCE_CAPTURE=ON', '-DDXSDK_DIR:PATH=' + os.environ['DXSDK_DIR']],
                   check=True)
    subprocess.run(['cmake', '--build', build, '--parallel', '2'], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'data', 'planets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--configuration', choices=('Debug', 'Release'), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((HERE / 'behavior-cases.json').read_text())['cases']
    # Scenarios hard-link several gigabytes of stock and planetary data.
    # Windows defaults to a different temp volume and would copy every asset.
    with tempfile.TemporaryDirectory(dir=args.data.resolve().parent, prefix='orbctl-') as temporary:
        scratch = Path(temporary)
        source, build = scratch / 'src', scratch / 'build'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', ROOT, source], check=True)
        build_control(source, build, OPENGL_PARENT, args.configuration)
        with tempfile.TemporaryDirectory(dir=scratch) as flights:
            baseline = Path(flights) / 'flights'
            control = argparse.Namespace(orbiter=build / 'Orbiter.exe', data=args.data, planets=args.planets,
                                         output=baseline, configuration=args.configuration, source_profile='opengl-parent')
            suite.capture(control, cases, application_source=OPENGL_PARENT)
            shutil.copy2(baseline / 'behavior-report.json', args.output / 'opengl-parent-capture.json')
            results = {}
            candidate = json.loads((args.candidate / 'behavior-report.json').read_text())
            for case in cases:
                name = case['id']
                reference, actual = baseline / name, args.candidate / name
                results[name] = suite.compare(reference, actual, case)
                for filename in suite.FILES:
                    require((reference / filename).read_bytes() == (actual / filename).read_bytes(),
                            f'{name}/{filename} differs from the independent OpenGL parent')
            report = dict(reference_source=OPENGL_PARENT, candidate_source=candidate['application_source_commit'],
                          byte_identical_files=list(suite.FILES), cases=results)
            (args.output / 'opengl-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'{len(cases)} OpenGL flights match the pre-DelThruster build byte for byte', flush=True)

        build_control(source, build, ORIGINAL_PHYSICS, args.configuration)
        tests = source / 'Tests/Production'
        baseline = scratch / 'original-flights'
        subprocess.run([sys.executable, '-B', tests / 'behavior_suite.py', '--orbiter', build / 'Orbiter.exe',
                        '--data', args.data.resolve(), '--planets', args.planets.resolve(), '--output', baseline,
                        '--configuration', args.configuration], cwd=source, check=True)
        subprocess.run([sys.executable, '-B', tests / 'frozen_behavior.py', '--candidate', baseline,
                        '--configuration', args.configuration], cwd=source, check=True)
        for name in ('behavior-report.json', 'frozen-behavior-comparison.json'):
            shutil.copy2(baseline / name, args.output / ('original-' + name))


if __name__ == '__main__':
    main()
