#!/usr/bin/env python3
"""Exercise the stock DG virtual cockpit mesh on a live native vessel visual."""
import argparse
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'assets', 'data', 'planets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    probe = output / 'visual-mesh-probe.so'
    compiler = next(line.split('=', 1)[1] for line in (build / 'CMakeCache.txt').read_text().splitlines()
                    if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    subprocess.run([compiler, '-std=c++17', '-fPIC', '-shared', '-Wl,--no-undefined',
                    '-I' + str(ROOT / 'Orbitersdk/include'), '-I' + str(ROOT / 'Src/Orbiter'),
                    '-I' + str(build / 'native-dg-include'), str(HERE / 'VisualMeshProbe.cpp'),
                    '-L' + str(build), '-lorbiter_production_vessels', '-ldl', '-o', str(probe)], check=True)
    scene = HERE.parent / 'NativeScene'
    config = output / 'Orbiter.cfg'
    config.write_text((scene / 'Orbiter.cfg').read_text() + '\nMenubarMode = 1\nInfobarMode = 1\n')
    env = dict(os.environ, LD_PRELOAD=str(probe), LD_LIBRARY_PATH=str(build))
    argv = [build / 'orbiter-production', '--config', config, '--scenario', scene / 'Sol-ISS-ShuttlePB.scn',
            '--assets', args.assets.resolve(), '--data', args.data.resolve(), '--modules', build / 'NativeModules',
            '--planets', args.planets.resolve(), '--evidence', output, '--frames', '60', '--fixed-step', '0.25', '--run']
    with (output / 'console.txt').open('w') as log:
        subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
    mesh = json.loads((output / 'stock-vc-mesh.json').read_text())
    life = json.loads((output / 'graphics-lifecycle.json').read_text())
    if mesh != dict(stock_groups=133, horizon_group=86, instance_edit=True, template_isolated=True, slot_reused=True):
        raise ValueError('Incomplete stock VC mesh operations')
    if life != dict(rendered_frames=60, successful_presents=60, context_deleted=True):
        raise ValueError('Incomplete renderer lifecycle after stock VC mesh deletion')
    errors = output / 'graphics-errors.txt'
    if errors.exists() and errors.read_text().strip():
        raise ValueError('OpenGL errors while editing the stock VC mesh')
    print('Verified stock DG horizon vertex edits, template isolation, material and texture selection, deletion and slot reuse')


if __name__ == '__main__':
    main()
