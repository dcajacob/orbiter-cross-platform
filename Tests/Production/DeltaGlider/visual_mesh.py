#!/usr/bin/env python3
"""Exercise the stock DG virtual cockpit mesh on a live native vessel visual."""
import argparse
import csv
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
                    '-I' + str(build / 'native-dg-include'), '-I' + str(ROOT / 'Src/Vessel/Common'),
                    str(HERE / 'VisualMeshProbe.cpp'), str(HERE.parent / 'Cockpit/CustomMFDProbe.cpp'),
                    '-Wl,--whole-archive', str(build / 'libnative_dg_instruments.a'),
                    '-Wl,--no-whole-archive', '-L' + str(build), '-lorbiter_production_vessels',
                    '-lorbiter_production_boundary', '-ldl', '-o', str(probe)], check=True)
    scene = HERE.parent / 'NativeScene'
    config = output / 'Orbiter.cfg'
    config.write_text((scene / 'Orbiter.cfg').read_text() + '\nMenubarMode = 1\nInfobarMode = 1\n')
    env = dict(os.environ, LD_PRELOAD=str(probe), LD_LIBRARY_PATH=str(build))
    scenario = output / 'cockpit.scn'
    scenario.write_text((scene / 'Sol-ISS-ShuttlePB.scn').read_text().replace('MODE Extern', 'MODE Cockpit'))
    (output / 'instrument-evidence.enabled').touch()
    replay = output / 'replay.csv'
    replay.write_text('tick,phase,action,value\n49,after,save,0\n')
    argv = [build / 'orbiter-production', '--config', config, '--scenario', scenario,
            '--save', output / 'saved.scn', '--replay', replay,
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
    events = (output / 'custom-mfd-events.txt').read_text().splitlines()
    dialogs = list(csv.reader((output / 'module-dialog.txt').read_text().splitlines()))
    if [r[0] for r in dialogs] != ['1','2'] or float(dialogs[1][1]) <= float(dialogs[0][1]):
        raise ValueError('Module dialog registration, drawing or close differs')
    if 'draw' not in events or [e for e in events if e!='draw'] != ['open_extended','open_packed','recall','button','key','save','store','close','destroy']:
        raise ValueError('Custom MFD lifecycle or input differs: '+str(events))
    if 'TYPE User\n  MODE SDK Probe\n  PROBE saved' not in (output / 'saved.scn').read_text():
        raise ValueError('Custom MFD scenario state missing')
    with (output / 'instrument-text.csv').open() as stream:
        left_text = {bytes.fromhex(r['text_hex']) for r in csv.DictReader(stream) if r['surface']=='0'}
    if not {b'Module SDK draw', b'MFD2'} <= left_text:
        raise ValueError('Missing custom Sketchpad text on the left MFD')
    if json.loads((output / 'mfd-0-20.json').read_text())['colored_pixels'] <= 0:
        raise ValueError('Custom MFD did not draw into its actual render texture')
    errors = output / 'graphics-errors.txt'
    if errors.exists() and errors.read_text().strip():
        raise ValueError('OpenGL errors while editing the stock VC mesh')
    print('Verified stock VC meshes and live MFD2 mode registration, inputs, drawing, scenario save and close')


if __name__ == '__main__':
    main()
