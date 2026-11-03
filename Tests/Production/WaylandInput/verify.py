#!/usr/bin/env python3
"""Audit complete software/GPU matrices and every finalized manual-thrust sample."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('software', 'hardware', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    require(not a.output.exists(), 'Matrix audit output exists')
    cases = {c['id'] for c in json.loads((HERE.parent/'CockpitControls/cases.json').read_text())['cases']
             if c['cockpit']!=1}
    report = dict(status='failed', phase6_complete=False, runs=[], source_sha256=digest(Path(__file__)))
    renderer_hashes = set()
    tools_hashes = set()
    try:
        for base, renderer in ((a.software, 'llvmpipe'), (a.hardware, 'default')):
            matrix = json.loads((base/'matrix.json').read_text())
            expected = {f'{case}-scale{scale}-{renderer}' for case in cases for scale in (1, 2)}
            require(matrix['status']=='passed' and len(matrix['runs'])==8 and
                    {r['name'] for r in matrix['runs']}==expected and
                    all(r['returncode']==0 for r in matrix['runs']), 'Incomplete input matrix: '+str(base))
            for name in sorted(expected):
                out = base/name
                result = json.loads((out/'wayland-input.json').read_text())
                require(result['status']=='passed' and result['case'] in cases and
                        result['case']+'-scale'+str(result['scale'])+'-'+renderer==name, 'Wrong run identity')
                for source, checksum in result['source_sha256'].items():
                    require(digest(ROOT/source)==checksum, 'Input source differs from qualified run: '+source)
                require(json.loads((out/'compositor/lifecycle.json').read_text())['returncode']==0,
                        'Private compositor failed normal shutdown')
                geometry = json.loads((out/'native-window.json').read_text())
                scale = result['scale']
                require(geometry==result['geometry'] and geometry['backend']=='wayland' and
                        geometry['logical_width']==1280//scale and geometry['logical_height']==720//scale and
                        geometry['framebuffer_width']==1280 and geometry['framebuffer_height']==720 and
                        geometry['content_scale_x']==scale and geometry['content_scale_y']==scale,
                        'Actual window/framebuffer scale differs')
                require(result['surface']['width']==1280//scale and result['surface']['height']==720//scale,
                        'Independent compositor content surface differs')
                if scale==2:
                    priming = json.loads((out/'engineering-window-priming.json').read_text())
                    require(priming['blank_presents_before_engine_scene']>=1, 'Missing pre-scene scale negotiation')
                actual_renderer = json.loads((out/'renderer-info.json').read_text())
                require(result['renderer']==actual_renderer and
                        ('llvmpipe' in actual_renderer['renderer'].lower())==(renderer=='llvmpipe'),
                        'Actual graphics driver differs')
                require({stage['check'] for stage in result['camera']['stages']}==
                        {'drag', 'external_drag', 'wheel', 'step', 'gui_capture'}, 'Incomplete camera assertions')
                require(result['camera']['shutdown']['held_button_shutdown_release'], 'Missing held-button shutdown')
                life = json.loads((out/'graphics-lifecycle.json').read_text())
                require(life==result['lifecycle'] and life['context_deleted'] and
                        life['rendered_frames']==life['successful_presents']>0, 'Invalid graphics lifecycle')
                keys = {int(r['tick']):bytes.fromhex(r['keys']) for r in rows(out/'input-state.csv')}
                counts = dict(released=0, bare=0, full=0, precision=0)
                for row in rows(out/'thrust-state.csv'):
                    sample = keys.get(int(row['input_tick']))
                    if not int(row['tick']) or sample is None:
                        continue
                    alt = bool(sample[0x38] or sample[0xb8])
                    held = bool(sample[0x11]) and alt
                    level, exhaust = float(row['rcs']), float(row['exhaust'])
                    if not held:
                        require(level==0 and exhaust==0, 'Finalized thrust persisted without manual input: '+name)
                        counts['released'] += 1
                        counts['bare'] += bool(sample[0x11]) and not alt
                    else:
                        precision = bool(sample[0x2a] or sample[0x36])
                        require(level==(.1 if precision else 1), 'Finalized manual thrust power differs: '+name)
                        counts['precision' if precision else 'full'] += 1
                require(counts['released']>=10 and counts['bare']>=3 and counts['full']>=2 and counts['precision']>=2,
                        'Insufficient finalized release/neutrality/power samples: '+name)
                renderer_hashes.add(result['renderer_sha256'])
                tools_hashes.add((result['test_tools_sha256'], result['test_module_sha256']))
                files = ('wayland-input.json', 'input-state.csv', 'thrust-state.csv', 'control-inputs.csv',
                         'cockpit-camera.csv', 'camera-capture.csv', 'native-window.json', 'renderer-info.json',
                         'graphics-lifecycle.json', 'compositor/control.jsonl', 'compositor/weston.log',
                         'compositor/lifecycle.json', 'loaded-maps.txt')
                report['runs'].append(dict(path=str(out), case=result['case'], scale=scale, driver=actual_renderer,
                    counts=counts, lifecycle=life, renderer_sha256=result['renderer_sha256'],
                    files_sha256={file:digest(out/file) for file in files}))
        require(len(renderer_hashes)==1, 'Matrices used different renderer binaries')
        require(len(tools_hashes)==1, 'Matrices used different compositor test tools')
        tools_manifest, test_module = next(iter(tools_hashes))
        report.update(status='passed', renderer_sha256=next(iter(renderer_hashes)), processes=len(report['runs']),
                      test_tools_sha256=tools_manifest, test_module_sha256=test_module,
                      successful_presents=sum(r['lifecycle']['successful_presents'] for r in report['runs']))
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f"All {report['processes']} Wayland input flows passed; {report['successful_presents']} scene presents")


if __name__=='__main__':
    main()
