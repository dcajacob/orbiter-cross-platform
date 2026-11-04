#!/usr/bin/env python3
"""Recheck a real failed/fixed titlebar drag with an unchanged simulator package."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def require(value,message):
    if not value:raise ValueError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def options(root):
    with (root/'menu-windows.csv').open() as stream:
        return [r for r in csv.DictReader(stream) if 'Orbiter: Options' in r['name']]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('failed','fixed','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh actual GUI-drag regression output required')
    bad=json.loads((a.failed/'wayland-input.json').read_text());good=json.loads((a.fixed/'wayland-input.json').read_text())
    require(bad['status']=='failed' and 'point outside owned surface' in bad['error'] and good['status']=='passed',
            'Actual original failed/current passed drag captures required')
    before=json.loads(a.failed.with_name(a.failed.name+'-wrapper.json').read_text())
    after=json.loads(a.fixed.with_name(a.fixed.name+'-wrapper.json').read_text())
    identity=('profile','renderer','case','scale','source_producer','gtk_plugin_sha256','sanitizer_environment')
    require(all(before[k]==after[k] for k in identity) and after['scale']==2 and after['driver_returncode']==0,
            'Actual failure/fix simulator, input identity, decoration or sanitizer configuration differs')
    for name,value in before['guarded_files_sha256'].items():
        if '/out/phase6-gauge-storage-matrix-' in name:
            require(after['guarded_files_sha256'].get(name)==value and sha(Path(name))==value,
                    'Actual simulator/generated source package changed between failure/fix')
    geometry=json.loads((a.fixed/'native-window.json').read_text());old=options(a.failed);new=options(a.fixed)
    require(old and new and len({(r['x'],r['y']) for r in old})==1 and
            all(float(r['x'])+float(r['width'])>geometry['logical_width'] for r in old),
            'Failed actual Options geometry does not reproduce the uncompleted drag')
    visible=[r for r in new if float(r['x'])+float(r['width'])<=geometry['logical_width']]
    require(visible and any(r['x']!=new[0]['x'] for r in visible),
            'Original Options titlebar did not actually move its close control into view')
    stage=next(r for r in good['camera']['stages'] if r['check']=='gui_capture')
    require(stage['actual_options_dialog'] and stage['camera_input_blocked'] and good['camera']['shutdown']['held_button_shutdown_release'],
            'Actual GUI capture and shutdown camera checks were omitted')
    require(sha(a.fixed/'camera-driver.py')==sha(HERE.parent/'DeltaGlider/window_camera.py') and
            sha(a.failed/'camera-driver.py')!=sha(a.fixed/'camera-driver.py'),
            'Actual executed GUI driver source identities differ from the expected old/fixed versions')
    files={str(root/name):sha(root/name) for root in (a.failed,a.fixed) for name in
           ('wayland-input.json','menu-windows.csv','control-inputs.csv','camera-actions.json','camera-driver.py','native-window.json')}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(status='passed-actual-gui-drag-regression',same_simulator_package=True,
        old_dialog_positions=sorted({(r['x'],r['y']) for r in old}),fixed_dialog_positions=sorted({(r['x'],r['y']) for r in new}),
        actual_original_dialog_dragged=True,actual_gui_and_camera_checks_preserved=True,protected_files_sha256=files,
        source_sha256=sha(HERE.parent/'DeltaGlider/window_camera.py'),test_sha256=sha(Path(__file__)),phase6_complete=False),indent=2)+'\n')
    print('Actual unchanged simulator: old drag remained outside view; fixed real titlebar drag and camera checks passed')

if __name__=='__main__':main()
