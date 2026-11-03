#!/usr/bin/env python3
"""Capture original Windows selection/input behavior with the preserved runtime."""
import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent/'Cockpit'), str(HERE.parent), str(HERE.parent/'Client')]
from reference import fixture, inspect, stage, git, mesa_files, require, rows, image_ssim, digest
from frozen import metadata
from regression import mfd_images


def settings():
    config = json.loads((HERE/'cases.json').read_text())
    pins = metadata(HERE.parent/'Cockpit/Reference/provenance.json')
    require(config['application_source'] == pins['application_source'], 'Original application pin differs')
    require(config['budgets'] == pins['budgets'] and config['image_ssim_minimum'] == .98, 'Original budgets differ')
    return config


def validate(directory, case):
    require(json.loads((directory/'ui-clock.json').read_text())['seconds_per_frame'] == .25, 'Original UI clock fixture differs')
    frames = rows(directory/'ui-clock-trace.csv')
    require(len(frames)==60 and all(float(row['delta'])==.25 for row in frames), 'Original GUI did not run sixty fixed-clock frames')
    numbers=[int(row['frame']) for row in frames]
    require(numbers==list(range(numbers[0],numbers[0]+60)), 'Original GUI frame sequence differs')
    ui = rows(directory/'ui-state.csv')
    require({int(row['tick']) for row in ui} == set(range(61)), 'Incomplete UI observations')
    require(any(row['popup_hex'] for row in ui if int(row['tick']) == 20), 'No original popup at capture 20')
    require(all(not row['popup_hex'] for row in ui if int(row['tick']) >= 40), 'Original popup did not close')
    inputs = rows(directory/'ui-inputs.csv')
    require(len(inputs) == len(case['actions']), 'Incomplete original input schedule')
    for actual, expected in zip(inputs, case['actions']):
        require(int(actual['tick']) == expected['tick'] and actual['event'] == expected['event'], 'Original input timing differs')
        expected_text = '' if expected['text'] == '-' else expected['text'].encode().hex()
        require(actual['text_hex'] == expected_text, 'Original input text differs')
        if expected['event'] in ('left_down', 'move', 'key_down', 'key_up'):
            require((int(actual['x']), int(actual['y'])) == (expected['x'], expected['y']), 'Original input coordinates/key differ')
    callbacks = rows(directory/'ui-callbacks.csv')
    if case['expected'] == 'cancel':
        require(len(callbacks) == 1 and callbacks[0]['event'] == 'cancel' and callbacks[0]['text_hex'] == b'draft'.hex(), 'Original cancellation callback differs')
    else:
        require(not callbacks, 'Unexpected SDK callback')
        saved = (directory/'Scenarios/UIResult.scn').read_text()
        left = saved.split('BEGIN_MFD Left', 1)[1].split('END_MFD', 1)[0]
        require(case['expected'] in left, 'Original MFD did not retain requested target/parameter')
    return dict(actual_inputs=len(inputs), popup_open_and_closed=True, outcome=case['expected'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter', 'data', 'planets', 'mesa', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--configuration', choices=('Debug','Release'), required=True)
    args = parser.parse_args()
    config = settings()
    require(sys.platform == 'win32', 'Original UI capture requires native Windows')
    runtime = json.loads((args.orbiter.parent/'control-reference-runtime.json').read_text())
    require(runtime['application_source'] == config['application_source'], 'Wrong original runtime')
    require(not args.output.exists(), 'Capture output exists')
    args.output.mkdir(parents=True)
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true', GALLIUM_DRIVER='llvmpipe')
    report = dict(status='pending', source=git('rev-parse','HEAD').decode().strip(), runtime=runtime, configuration=args.configuration, cases={}, failures={})
    for case in config['cases']:
        try:
            directories = []
            observations = []
            for repeat in (1, 2):
                directory = args.output.resolve()/(case['id']+'-'+str(repeat))
                def configure(directory):
                    cfg = directory/'Orbiter.cfg'
                    cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    scenario = fixture(case)
                    if case['left'] == 8:
                        scenario = scenario.replace('BEGIN_SHIPS', 'BEGIN_MFD Left\n  TYPE OSync\n  TARGET ISS\n  LISTLEN 5\nEND_MFD\nBEGIN_SHIPS')
                    (directory/'Scenarios/Behavior.scn').write_text(scenario)
                    commands = [f"{case['left']} {len(case['actions'])}"]
                    commands += [f"{a['tick']} {a['event']} {a['x']} {a['y']} {a['text']}" for a in case['actions']]
                    (directory/'ui-case.txt').write_text('\n'.join(commands)+'\n')
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):
                        (directory/name).write_text('Original selection/input reference observation\n')
                    mesa_files(args.mesa.resolve(), directory)
                stage(args.orbiter.resolve(), args.data.resolve(), args.planets.resolve(), directory, {**case,'frames':60,'fixed_step':.25,'epoch':config['epoch']}, configure)
                observed = inspect(directory, case, config)
                observed['ui'] = validate(directory, case)
                observed['font_sha256'] = {p.name:digest(p) for p in (directory/'Fonts').glob('*.ttf')}
                observations.append(observed)
                directories.append(directory)
            for name in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv','ui-inputs.csv','ui-state.csv','ui-callbacks.csv'):
                require((directories[0]/name).read_bytes() == (directories[1]/name).read_bytes(), 'Original repeat differs: '+name)
            similarity = {str(f):image_ssim((directories[0]/f'instrument-{f}.rgba').read_bytes(), (directories[1]/f'instrument-{f}.rgba').read_bytes(), 1280,720) for f in (20,50)}
            require(min(similarity.values()) >= .98, 'Original image repeat exceeds budget')
            report['cases'][case['id']] = dict(runs=observations, repeat_ssim=similarity)
        except Exception as error:
            failure = directory/'cockpit-failure.txt'
            report['failures'][case['id']] = str(error) + (': '+failure.read_text() if failure.exists() else '')
    report['status'] = 'failed' if report['failures'] else 'passed'
    (args.output/'ui-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],failures=report['failures']),indent=2))
    require(report['status'] == 'passed', 'Original UI reference failed')

if __name__ == '__main__':
    main()
