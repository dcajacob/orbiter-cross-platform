#!/usr/bin/env python3
"""Exercise the original spacecraft selector and info bars on native or preserved Windows Orbiter."""
import argparse
import csv
import json
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from reference import fixture, require, stage, mesa_files, image_ssim


def scenario():
    cases=json.loads((HERE.parent/'Cockpit/cases.json').read_text())['cases']
    dg=fixture(next(c for c in cases if c['id']=='dg_panel'))
    scram=fixture(next(c for c in cases if c['id']=='dgs_panel'))
    ship=scram.split('\nDG:DG-S\n',1)[1].split('\nEND\n',1)[0]
    ship=ship.replace('RPOS 6771100 0 0','RPOS 6771100 0 100')
    return dg.replace('END_SHIPS','DG2:DG-S\n'+ship+'\nEND\nEND_SHIPS')


# Use the original preferences file to display the same eight commands on
# both hosts. Windows also captures the stock configuration in the other cases.
MENU_ITEMS=('Ship','Camera','Speed','Pause','Function','Info','Options','Map','Record','Help','Save','Exit')
TESTED_MENU={'Ship','Camera','Speed','Pause','Info','Map','Save','Exit'}
CASES=[('hidden',1,0),('visible',0,0),('auto',2,0),('focus',0,0),
       ('menu-hidden',1,0),('menu',1,0),('menu-auto',1,0)]

def menu_preferences(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    # The staged stock configuration can be a hard link to the original data.
    if path.exists():path.unlink()
    path.write_text(''.join(f'MenuItem{i} = {label}\nMenuItemEnabled{i} = {"TRUE" if label in TESTED_MENU else "FALSE"}\n'
                            for i,label in enumerate(MENU_ITEMS,1)))


def inputs(name):
    if name=='menu-auto':
        return [(0,'move',640,5),(23,'move',400,350)]
    if name=='menu':
        actions=[(0,'move',400,350)]
        for tick,x,y in [(24,463,25),(32,102,175),(40,288,159)]:
            actions.extend([(tick,'move',x,y),(tick+1,'left_down',x,y),(tick+2,'left_up',x,y)])
        return actions
    if name!='focus':
        return [(0,'move',400,5),(23,'move',400,350)]
    # Both hosts render the original 300x320 dialog at 1280x720.
    actions=[(3,'focus_dialog',0,0)]
    for tick,x,y in [(8,102,175),(14,288,159),(26,288,184),(31,120,95),(35,176,95),(39,227,95),(44,347,71)]:
        actions.extend([(tick,'move',x,y),(tick+1,'left_down',x,y),(tick+2,'left_up',x,y)])
    return actions


def execute(args,name,mode,fps):
    out=args.output/name
    menu_mode={'menu':0,'menu-auto':2}.get(name,1)
    config=f'\nFPS = {fps}\nMenubarMode = {menu_mode}\nInfobarMode = {mode}\nInstrumentUpdateInterval = 0.25\n'
    actions=inputs(name)
    if args.original:
        def configure(directory):
            if name.startswith('menu'):menu_preferences(directory/'Config/MenuInfoBar.cfg')
            master=directory/'Orbiter.cfg'
            master.write_text(master.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+config)
            (directory/'Scenarios/Behavior.scn').write_text(scenario())
            (directory/'ui-case.txt').write_text(f'1 {len(actions)}\n'+''.join(f'{t} {event} {x} {y} -\n' for t,event,x,y in actions))
            for marker in ('focus-bars.enabled','instrument-evidence.enabled','ogl-evidence.enabled'):
                (directory/marker).touch()
            mesa_files(args.mesa,directory)
        stage(args.executable,args.data,args.planets,out,dict(frames=60,fixed_step=.25),configure)
        require((out/'cockpit-complete.txt').read_text().strip()=='60','Incomplete original focus/info run')
    else:
        out.mkdir()
        if name.startswith('menu'):menu_preferences(out/'ScriptFiles/config/menuinfobar.cfg')
        (out/'flight.scn').write_text(scenario())
        (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+config)
        (out/'instrument-evidence.enabled').touch()
        commands=['tick,phase,action,value','0,pre,mfd,0 1','0,pre,mfd,1 2','0,pre,hud,1']
        for t,event,x,y in actions:
            if event=='focus_dialog':
                commands.extend([f'{t},pre,key,61',f'{t+1},pre,key,-61'])
            else:
                commands.append(f'{t},pre,ui,{event} {x} {y} -')
        (out/'replay.csv').write_text('\n'.join(commands)+'\n')
        with (out/'console.txt').open('w') as log:
            subprocess.run([args.executable,'--config',out/'Orbiter.cfg','--scenario',out/'flight.scn',
                '--assets',args.assets,'--data',args.data,'--planets',args.planets,'--modules',args.modules,
                '--save',out/'saved.scn','--evidence',out,'--replay',out/'replay.csv','--frames','60',
                '--frame-delay-ms','120','--fixed-step','0.25','--fixed-ui-clock','--run'],
                cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life['successful_presents']==60 and life['context_deleted'],'Incomplete cockpit renderer lifecycle')
    with (out/'cockpit-state.csv').open() as f: states=list(csv.DictReader(f))
    require([int(r['tick']) for r in states]==list(range(61)),'Missing finalized cockpit sample')
    changes=[r['object'] for i,r in enumerate(states) if i==0 or r['object']!=states[i-1]['object']]
    require(changes=={'focus':['DG','DG2','DG'],'menu':['DG','DG2']}.get(name,['DG']),'Incorrect spacecraft selection: '+str(changes))
    require(all(r['cockpit']=='2' and r['class']==('DG-S' if r['object']=='DG2' else 'DeltaGlider') for r in states),
            'Missing real focused spacecraft or 2D panel')
    if name=='focus':
        require(states[20]['object']=='DG2' and states[50]['object']=='DG','Select or Previous failed')
    if name=='menu':require(states[50]['object']=='DG2','Visible menu failed to select DG-S')
    return changes


def original_general_api(args,pin):
    root=HERE.parents[2]
    def original(name):
        return subprocess.check_output(['git','-C',str(root),'show',pin+':'+name]).replace(b'\r\n',b'\n')
    test_script=original('Script/Tests/GeneralApiTest.lua')
    out=args.output/'general-api'
    def configure(directory):
        # Run the unchanged mission and its own script to completion or the
        # bounded frame limit. The focus observer is not active in this run.
        cfg=directory/'Orbiter.cfg'
        cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  OGLClient'))
        (directory/'Scenarios/Behavior.scn').write_bytes(original('Scenarios/Tests/GeneralApiTest.scn'))
        folder=directory/'Scenarios/Tests'
        folder.mkdir()
        (folder/'Description.txt').write_bytes(original('Scenarios/Tests/Description.txt'))
        require((directory/'Script/Tests/GeneralApiTest.lua').read_bytes().replace(b'\r\n',b'\n')==test_script,
                'Preserved Windows runtime contains a different stock test script')
        mesa_files(args.mesa,directory)
    stage(args.executable,args.data,args.planets,out,dict(frames=60,fixed_step=.25),configure)
    log=(out/'Orbiter.log').read_text(errors='replace')
    groups=[line[line.index('Test: '):] for line in log.splitlines() if 'Test: ' in line]
    require(groups,'Stock Windows general API script did not run')
    value=float((args.output/'visible/earth-obliquity.txt').read_text())
    result=dict(tests_seen=groups,all_passed='=== All tests passed ===' in log,
                failed_assertion=' - FAILED!' in log,earth_obliquity_degrees=math.degrees(value),
                script_sha256=hashlib.sha256(test_script).hexdigest())
    require(result['all_passed'] or result['failed_assertion'],'Missing terminal result from stock Windows API test')
    (out/'general-api-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Stock Windows general API result',json.dumps(result),flush=True)


def pixels(root,name,frame):
    raw=(root/name/f'instrument-{frame}.rgba').read_bytes()
    require(len(raw)==1280*720*4,'Invalid framebuffer capture')
    return raw


def compare_case(original,native,name):
    with (original/name/'cockpit-state.csv').open() as source,(native/name/'cockpit-state.csv').open() as actual:
        expected=list(csv.DictReader(source));observed=list(csv.DictReader(actual))
        require(len(expected)==len(observed),name+' cockpit sample count differs')
        for left,right in zip(expected,observed):
            for key,value in left.items():
                require(value==right[key],f'{name} tick {left["tick"]} {key}: Windows {value}, native {right[key]}')
    scores={f:image_ssim(pixels(original,name,f),pixels(native,name,f),1280,720) for f in (20,50)}
    require(min(scores.values())>=.98,name+' differs from original rendered instruments')
    return scores


def main():
    p=argparse.ArgumentParser(description=__doc__)
    if sys.argv[1:2]==['compare']:
        for key in ('original','native','output'):p.add_argument('--'+key,type=Path,required=True)
        a=p.parse_args(sys.argv[2:])
        from recorded_flights import require_matching_math
        results={}
        for name,*_ in CASES:
            require_matching_math(a.original/name,a.native/name)
            results[name]=compare_case(a.original,a.native,name)
        a.output.write_text(json.dumps(results,indent=2)+'\n')
        return
    for name in ('executable','data','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('assets','modules','mesa','reference'):p.add_argument('--'+name,type=Path)
    p.add_argument('--original',action='store_true')
    a=p.parse_args()
    for key,value in vars(a).items():
        if isinstance(value,Path):setattr(a,key,value.resolve())
    if a.original:
        require(a.mesa and sys.platform=='win32','Original captures require the preserved Windows application and Mesa')
        pin=json.loads((a.executable.parent/'control-reference-runtime.json').read_text())
        require(pin['application_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37','Wrong reference application')
        os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    else:require(a.modules and a.assets,'Native runs require the real modules and resources')
    a.output.mkdir(parents=True,exist_ok=False)
    report={}
    for name,mode,fps in CASES:
        report[name]=dict(focus=execute(a,name,mode,fps))
        if a.reference:
            report[name]['original_frame_ssim']=compare_case(a.reference,a.output,name)
    # RGBA is bottom-up. Only the top strip may change when the bars are enabled.
    for frame in (20,50):
        hidden=pixels(a.output,'hidden',frame);visible=pixels(a.output,'visible',frame)
        require(hidden[:1280*4*600]==visible[:1280*4*600],'Info bars changed the lower 600 rows')
        for x1,x2 in [(0,180),(1080,1280)]:
            require(any(hidden[(y*1280+x1)*4:(y*1280+x2)*4]!=visible[(y*1280+x1)*4:(y*1280+x2)*4]
                        for y in range(660,720)),'Missing time or target readout')
        auto=pixels(a.output,'auto',frame)
        require(auto==(visible if frame==20 else hidden),'Info bars failed to reveal or hide on pointer movement')
    # The stock menu is drawn at the top of the bottom-up RGBA buffer.
    def menu_strip(name,frame):
        image=pixels(a.output,name,frame)
        return b''.join(image[(y*1280+400)*4:(y*1280+900)*4] for y in range(665,720))
    # Compare the same menu item configuration. The original Windows renderer
    # leaves a few edge pixels on the top row even when the menu is hidden;
    # their locations depend on the width of the configured menu. Keep the
    # stock twelve-item hidden case above, and use a separate eight-item hidden
    # case for the exact reveal/retract check. No pixels are excluded.
    require(menu_strip('menu',20)!=menu_strip('menu-hidden',20),'Missing visible stock menu')
    require(menu_strip('menu-auto',20)!=menu_strip('menu-hidden',20),'Stock menu did not reveal on hover')
    require(menu_strip('menu-auto',50)==menu_strip('menu-hidden',50),'Stock menu did not retract')
    if a.original:original_general_api(a,pin['application_source'])
    (a.output/'focus-bars-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
