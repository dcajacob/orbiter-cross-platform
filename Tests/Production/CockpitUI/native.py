#!/usr/bin/env python3
"""Compare native original dialogs with preserved Windows selection/input cases."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from frozen_ui import metadata, digest, require
from capture import settings, fixture, mfd_images
from compare import compare
from run_client import png
from compare_client import image_ssim
from additional_references import metadata as timing_metadata


def read_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def compare_ui(original, candidate, *, compare_popup_pixels=True):
    inputs=read_rows(candidate/'ui-inputs.csv')
    require(inputs[0] == dict(tick='0',event='move',x='640',y='360',text_hex=''), 'Initial UI cursor differs')
    require(inputs[1:] == read_rows(original/'ui-inputs.csv'), 'Native UI input schedule differs')
    expected=read_rows(original/'ui-state.csv')
    actual=read_rows(candidate/'ui-state.csv')
    require(len(expected)==len(actual), 'Native UI observation count differs')
    for a,b in zip(expected,actual):
        for key in ('tick','popup_hex','capture_mouse','capture_keyboard'):
            require(a[key]==b[key], 'Native UI state differs at tick '+a['tick']+': '+key)
        for key in ('x','y','width','height'):
            require(abs(float(a[key])-float(b[key]))<=1, 'Native popup geometry exceeds one pixel: '+key)
    if not compare_popup_pixels:
        return dict(exact_inputs=True,exact_popup_state=True)
    popup=next(row for row in expected if row['tick']=='20' and row['popup_hex'])
    x,y,w,h=[int(float(popup[key])) for key in ('x','y','width','height')]
    def crop(path):
        pixels=path.read_bytes()
        return b''.join(pixels[(row*1280+x)*4:(row*1280+x+w)*4] for row in range(720-y-h,720-y))
    similarity=image_ssim(crop(original/'instrument-20.rgba'),crop(candidate/'instrument-20.rgba'),w,h)
    require(similarity>=.98, 'Native popup pixels exceed the frozen SSIM budget')
    return dict(exact_inputs=True,exact_popup_state=True,popup_ssim=similarity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','frozen','timing-frozen','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args = parser.parse_args()
    pins = metadata()
    require(json.loads((args.frozen/'provenance.json').read_text()) == pins,'Frozen UI provenance differs')
    for name, checksum in pins['reference_files_sha256'][args.configuration].items():
        require(digest(args.frozen/args.configuration/name) == checksum,'Frozen UI file differs: '+name)
    timing = timing_metadata('ui-timing')
    require(json.loads((args.timing_frozen/'provenance.json').read_text()) == timing, 'Fixed-clock UI provenance differs')
    for name, checksum in timing['reference_files_sha256'][args.configuration].items():
        require(digest(args.timing_frozen/args.configuration/name) == checksum, 'Fixed-clock UI file differs: '+name)
    config = settings()
    require(not args.output.exists(),'Native UI output exists')
    args.output.mkdir(parents=True)
    report = dict(status='pending',reference_run=pins['run_id'],timing_reference_run=timing['run_id'],configuration=args.configuration,cases={})
    try:
        for case in config['cases']:
            runs = []
            original = args.frozen/args.configuration/(case['id']+'-1')
            timed = args.timing_frozen/args.configuration/(case['id']+'-1')
            require(read_rows(timed/'ui-inputs.csv') == read_rows(original/'ui-inputs.csv'), 'Original UI clock changed the discrete input schedule')
            with (original/'ui-inputs.csv').open() as stream:
                inputs = list(csv.DictReader(stream))
            for repeat in (1,2):
                directory = args.output.resolve()/(case['id']+'-'+str(repeat))
                directory.mkdir()
                runs.append(directory)
                scenario = fixture(case)
                if case['left'] == 8:
                    scenario = scenario.replace('BEGIN_SHIPS','BEGIN_MFD Left\n  TYPE OSync\n  TARGET ISS\n  LISTLEN 5\nEND_MFD\nBEGIN_SHIPS')
                (directory/'cockpit.scn').write_text(scenario)
                master = (HERE.parent/'NativeScene/Orbiter.cfg').read_text()
                master += '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'
                (directory/'Orbiter.cfg').write_text(master)
                for marker in ('instrument-evidence.enabled','ui-evidence.enabled'):
                    (directory/marker).write_text('Native original UI comparison\n')
                commands = ['tick,phase,action,value',f"0,pre,mfd,0 {case['left']}",'0,pre,mfd,1 2','0,pre,hud,1','0,pre,ui,move 640 360 -']
                for entry in inputs:
                    text = bytes.fromhex(entry['text_hex']).decode() or '-'
                    commands.append(f"{entry['tick']},pre,ui,{entry['event']} {entry['x']} {entry['y']} {text}")
                commands.append('49,after,save,0')
                (directory/'replay.csv').write_text('\n'.join(commands)+'\n')
                argv = [str(args.executable.resolve())]
                for name in ('assets','data','modules','planets'):
                    argv += ['--'+name,str(getattr(args,name).resolve())]
                argv += ['--config',str(directory/'Orbiter.cfg'),'--scenario',str(directory/'cockpit.scn'),'--evidence',str(directory),'--save',str(directory/'saved.scn'),'--replay',str(directory/'replay.csv'),'--frames','60','--frame-delay-ms','120','--fixed-ui-clock','--fixed-step','0.25','--run']
                (directory/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
                with (directory/'console.txt').open('w') as stream:
                    subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=240)
                if case['expected'] == 'cancel':
                    require((directory/'ui-cancel.txt').read_text().strip() == 'draft','Native cancellation callback differs')
                else:
                    left = (directory/'saved.scn').read_text().split('BEGIN_MFD Left',1)[1].split('END_MFD',1)[0]
                    require(case['expected'] in left,'Native target/parameter differs')
                life = json.loads((directory/'graphics-lifecycle.json').read_text())
                require(life['context_deleted'] and life['successful_presents'] == 60,'Native GUI lifecycle incomplete')
                errors = directory/'graphics-errors.txt'
                require(not errors.exists() or not errors.read_text().strip(),'Native GUI OpenGL errors')
                for frame in (20,50):
                    image = directory/f'instrument-{frame}.rgba'
                    png(image.with_suffix('.png'),image.read_bytes(),1280,720)
            for name in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((runs[0]/name).read_bytes() == (runs[1]/name).read_bytes(),'Native UI repeat differs: '+name)
            for frame in (20,50):
                for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                    require((runs[0]/(stem+'.rgba')).read_bytes() == (runs[1]/(stem+'.rgba')).read_bytes(),
                            'Native UI image repeat differs: '+stem)
            selected = {**config,'cases':[case]}
            for directory in runs:
                require(json.loads((directory/'ui-clock.json').read_text()) == json.loads((timed/'ui-clock.json').read_text()), 'UI clock fixture differs')
                require(read_rows(directory/'ui-clock-trace.csv') == read_rows(timed/'ui-clock-trace.csv'), 'Effective ImGui frame deltas differ')
                compare_ui(original,directory,compare_popup_pixels=False)
            ui=compare_ui(timed,runs[0])
            compare_ui(timed,runs[1])
            report['cases'][case['id']] = dict(ui=ui,timing_comparison=compare(args.timing_frozen/args.configuration,args.output,selected)[case['id']],comparison=compare(args.frozen/args.configuration,args.output,selected)[case['id']],mfd_images=mfd_images(args.frozen/args.configuration,args.output,selected)[case['id']])
            print(case['id']+': native UI outcome and frozen comparison passed',flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed',error=str(error))
        raise
    finally:
        (args.output/'native-ui-report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__ == '__main__':
    main()
