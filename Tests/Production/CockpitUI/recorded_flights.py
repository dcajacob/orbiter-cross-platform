#!/usr/bin/env python3
"""Fly unchanged stock recordings on native Linux or the preserved original Windows application."""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
from pathlib import Path, PureWindowsPath
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from reference import mesa_files,require,image_ssim
from behavior_suite import distance,quaternion,quaternion_angle,link_or_copy

PIN='f725194209634f7fd5d1d44d426cfa9b5e303e37'
# Cross a camera cut and an articulation event, end naturally in orbit 1, and
# explicitly leave the recording in orbit 2 while the original stream is live.
CASES=[
    ('dg-stunts','Tutorials/DG stunts',140,0),
    ('mojave','Playback/Mojave to Edwards',140,0),
    ('mojave-stock','Antelope Valley scenery/Mojave to Edwards',140,0),
    ('orbit-1','Playback/Glider in orbit 1',350,0),
    ('orbit-2','Playback/Glider in orbit 2',140,90),
]


def stock(relative):
    return subprocess.check_output(['git','-C',str(ROOT),'show',PIN+':'+relative]).replace(b'\r\n',b'\n')


def read_rows(directory):
    with (directory/'playback-state.csv').open() as stream:return list(csv.DictReader(stream))


def launch_original(args,directory,mission,frames,configure):
    directory.mkdir()
    runtime=args.executable.parent
    for p in runtime.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,directory/p.name)
    for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
        if (runtime/name).is_dir():shutil.copytree(runtime/name,directory/name,copy_function=link_or_copy)
    for body,modules in {'Earth':['EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'],
                         'Mars':['MarsAtm2006'],'Venus':['VenusAtm2006']}.items():
        target=directory/'Modules/Celbody'/body/'Atmosphere'
        target.mkdir(parents=True,exist_ok=True)
        for module in modules:shutil.copy2(directory/'Modules/Celbody/Atmosphere'/(module+'.dll'),target)
    for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
        shutil.copytree(args.data/name,directory/name,dirs_exist_ok=True,copy_function=link_or_copy)
    lock=json.loads((HERE.parent/'standard-planets.lock.json').read_text())
    for name in lock['data_files']:
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);link_or_copy(args.planets/name,target)
    cfg=(HERE.parent/'Fixtures/Orbiter.cfg').read_text().replace('ProductionReferenceDriver','ProductionBehaviorDriver')
    (directory/'Orbiter.cfg').write_text(cfg+'\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n')
    configure(directory)
    cmd=[str(directory/args.executable.name),'--scenariox='+str(PureWindowsPath(mission)),'--fixedstep=0.25',f'--maxframes={frames}']
    (directory/'invocation.json').write_text(json.dumps(cmd)+'\n')
    with (directory/'console.txt').open('w') as log:
        subprocess.run(cmd,cwd=directory,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    require('Could not find a module' not in (directory/'Orbiter.log').read_text(errors='replace'),'Stock module failed to load')


def execute(args,case):
    ident,mission,frames,stop=case
    directory=args.output/ident
    scenario='Scenarios/'+mission+'.scn'
    folder='Flights/'+Path(mission).name
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',PIN,'--',folder],text=True).splitlines()
    require(any(n.endswith('.pos') for n in names),'Stock position recording missing')
    inputs={n:stock(n) for n in [scenario,*names]}
    config='\nMenubarMode = 1\nInfobarMode = 0\nFPS = 0\nInstrumentUpdateInterval = 0.25\n'
    if args.original:
        def configure(d):
            cfg=d/'Orbiter.cfg'
            cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+config)
            for name,data in inputs.items():
                target=d/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            (d/'playback.enabled').write_text(f'{frames} {stop}\n')
            for marker in ('instrument-evidence.enabled','ogl-evidence.enabled'):(d/marker).touch()
            mesa_files(args.mesa,d)
        launch_original(args,directory,mission,frames,configure)
        require((directory/'cockpit-complete.txt').read_text().strip()==str(frames),'Incomplete original playback')
    else:
        directory.mkdir()
        for name,data in inputs.items():
            require((args.assets/name).read_bytes().replace(b'\r\n',b'\n')==data,'Recorded input differs: '+name)
        (directory/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+config)
        (directory/'playback.enabled').write_text(f'{frames} {stop}\n')
        (directory/'instrument-evidence.enabled').touch()
        schedule='tick,phase,action,value\n'
        if stop:schedule+=f'{stop},before,key,29\n{stop},before,key,46\n{stop+1},before,key,-46\n{stop+1},before,key,-29\n'
        (directory/'replay.csv').write_text(schedule)
        with (directory/'console.txt').open('w') as log:
            subprocess.run([args.executable,'--config',directory/'Orbiter.cfg','--scenario',args.assets/scenario,
                '--assets',args.assets,'--data',args.data,'--modules',args.modules,'--planets',args.planets,
                '--evidence',directory,'--save',directory/'save.scn','--replay',directory/'replay.csv',
                '--frames',str(frames),'--frame-delay-ms','120','--fixed-step','0.25','--run'],
                cwd=directory,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    life=json.loads((directory/'graphics-lifecycle.json').read_text())
    require(life['successful_presents']==frames and life['context_deleted'],'Incomplete rendering lifecycle')
    states=read_rows(directory)
    require([int(r['tick']) for r in states]==list(range(frames+1)),'Incomplete finalized playback states')
    require(all(math.isfinite(float(v)) for r in states for k,v in r.items() if k not in ('object','class','target')),
            'Nonfinite playback state')
    flags=[int(r['playback']) for r in states]
    require(flags[0]==1 and flags==sorted(flags,reverse=True),'Recording never started or restarted unexpectedly')
    finish=flags.index(0) if 0 in flags else None
    if stop:require(finish==stop+1,'Original stop-playback command did not release the vessel')
    elif ident=='orbit-1':
        end=float(next(data for n,data in inputs.items() if n.endswith('.pos')).splitlines()[-1].split()[0])
        require(finish is not None and float(states[finish-1]['seconds'])<=end<float(states[finish]['seconds']),
                'Vessel ended playback outside the final position sample')
    else:require(finish is None,'Stock playback ended early')
    cams=[int(r['internal']) for i,r in enumerate(states) if i==0 or r['internal']!=states[i-1]['internal']]
    if ident=='dg-stunts':
        require(cams==[1,0],'Recorded camera failed to leave the DG cockpit')
        with (directory/'instrument-text.csv').open() as stream:
            require(any(b'This tutorial demonstrates' in bytes.fromhex(row['text_hex']) for row in csv.DictReader(stream)),
                    'Tutorial annotation was not drawn')
    if ident in ('mojave','mojave-stock'):require(cams==[1,0],'Recorded ground camera did not engage')
    if ident=='orbit-1':
        require(cams==[0,1,0] and any(float(r['rcs'])>0 for r in states),'Recorded camera cuts or RCS actions missing')
    return dict(frames=frames,first_free_tick=finish,camera_internal=cams,
                source_sha256={n:hashlib.sha256(d).hexdigest() for n,d in inputs.items()})


def compare(original,native,budgets):
    left=read_rows(original);right=read_rows(native)
    require(len(left)==len(right),'Original/native recording lengths differ')
    maxima={}
    for a,b in zip(left,right):
        for k in ('tick','seconds','object','class','target','playback','internal','warp','main','hover','rcs'):
            require(a[k]==b[k],f'Recorded {k} differs at tick {a["tick"]}: {a[k]} / {b[k]}')
        def vector(row,keys):return [float(row[k]) for k in keys.split()]
        for key,error in [('position_m',distance(vector(a,'x y z'),vector(b,'x y z'))),
                          ('velocity_m_s',distance(vector(a,'vx vy vz'),vector(b,'vx vy vz'))),
                          ('angular_velocity_rad_s',distance(vector(a,'wx wy wz'),vector(b,'wx wy wz'))),
                          ('rotation_rad',quaternion_angle(quaternion(a),quaternion(b))),
                          ('mjd_days',abs(float(a['mjd'])-float(b['mjd'])))]:
            require(error<=budgets[key],f'Recorded {key} exceeds original budget at tick {a["tick"]}')
            maxima[key]=max(maxima.get(key,0.),error)
        for k in ('mass','fuel'):
            require(abs(float(a[k])-float(b[k]))<=max(budgets['propellant_absolute_kg'],abs(float(a[k]))*budgets['propellant_relative']),
                    'Original recording fuel or mass differs')
        require(abs(float(a['aperture'])-float(b['aperture']))<=budgets['rotation_rad'] and
                distance(vector(a,'cam_dx cam_dy cam_dz'),vector(b,'cam_dx cam_dy cam_dz'))<=budgets['rotation_rad'],
                'Original recorded camera orientation differs')
    scores={tick:image_ssim((original/f'instrument-{tick}.rgba').read_bytes(),(native/f'instrument-{tick}.rgba').read_bytes(),1280,720)
            for tick in (20,50)}
    require(min(scores.values())>=.98,'Recorded flight frame differs from original Windows')
    return dict(maxima=maxima,ssim=scores)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    if sys.argv[1:2]==['compare']:
        p.add_argument('--original',type=Path,required=True)
        p.add_argument('--native',type=Path,required=True)
        p.add_argument('--output',type=Path,required=True)
        a=p.parse_args(sys.argv[2:])
        budgets=json.loads((HERE.parent/'Cockpit/cases.json').read_text())['budgets']
        original=json.loads((a.original/'recorded-flights.json').read_text())
        native=json.loads((a.native/'recorded-flights.json').read_text())
        results={}
        for name,*_ in CASES:
            require(original[name]['source_sha256']==native[name]['source_sha256'],'Recording input hashes differ')
            results[name]=compare(a.original/name,a.native/name,budgets)
        a.output.write_text(json.dumps(results,indent=2)+'\n')
        return
    for name in ('executable','data','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('assets','modules','mesa','reference'):p.add_argument('--'+name,type=Path)
    p.add_argument('--original',action='store_true')
    args=p.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    if args.original:
        require(args.mesa and sys.platform=='win32','Original recording comparison requires Windows and Mesa')
        pin=json.loads((args.executable.parent/'control-reference-runtime.json').read_text())
        require(pin['application_source']==PIN,'Wrong original application')
        os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    else:require(args.assets and args.modules,'Native flight assets and modules required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={}
    for case in CASES:
        result=execute(args,case);report[case[0]]=result
        if args.reference:
            budgets=json.loads((HERE.parent/'Cockpit/cases.json').read_text())['budgets']
            result['windows']=compare(args.reference/case[0],args.output/case[0],budgets)
        print(case[0],result['frames'],result['first_free_tick'],flush=True)
    (args.output/'recorded-flights.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
