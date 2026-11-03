#!/usr/bin/env python3
"""Fly the stock atmospheric DG and DG-S with Lua AAP in the 2D and virtual cockpits."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess

from capture import lua_fixture, settings

HERE = Path(__file__).resolve().parent


def run_case(root, assets, case, mode, args):
    output = root / (case['id'] + ('-panel' if mode == 2 else '-vc'))
    output.mkdir()
    scenario = output / 'flight.scn'
    scenario.write_text(lua_fixture(dict(case,cockpit=mode)).replace(
        'BEGIN_ENVIRONMENT\n', 'BEGIN_ENVIRONMENT\n  Script phase6-flight\n'))
    config = output / 'Orbiter.cfg'
    config.write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+'\nMenubarMode = 1\nInfobarMode = 1\n')
    replay = output / 'replay.csv'
    replay.write_text('tick,phase,action,value\n45,after,save,0\n')
    command = [args.build/'orbiter-production', '--config', config, '--scenario', scenario,
               '--save', output/'saved.scn', '--assets', assets, '--data', args.data, '--planets', args.planets,
               '--modules', args.build/'NativeModules', '--replay', replay, '--evidence', output,
               '--frames', '48', '--fixed-step', '0.25', '--run']
    with (output/'console.txt').open('w') as log:
        subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
    with (output/'lua-flight.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows)!=40 or any(int(row['tick'])!=i+1 or row['class']!=case['class'] for i,row in enumerate(rows)):
        raise ValueError('Stock scenario interpreter did not finish the 40 AAP yields')
    for i,row in enumerate(rows):
        if not all(math.isfinite(float(row[k])) for k in ('altitude','airspeed','elevator','aileron','main')):
            raise ValueError('Nonfinite stock controller or flight state')
        if i and float(row['seconds'])-float(rows[i-1]['seconds'])!=0.25:
            raise ValueError('Lua worker did not yield once per step')
    if not all(any(abs(float(row[k]))>0 for row in rows[:30]) for k in ('elevator','aileron')):
        raise ValueError('Original autopilot did not drive both surfaces')
    if not (min(float(r['main']) for r in rows[:11])==0 and max(float(r['main']) for r in rows[12:23])==1 and
            min(float(r['main']) for r in rows[24:31])==0):
        raise ValueError('Original autopilot did not track the low/high/low airspeed targets')
    cockpit = list(csv.DictReader((output/'cockpit-state.csv').read_text().splitlines()))
    if not cockpit or any(int(r['cockpit'])!=mode for r in cockpit):
        raise ValueError('Actual requested stock cockpit did not initialize')
    saved=(output/'saved.scn').read_text()
    actions={parts[0]:tuple(map(float,parts[1:])) for line in saved.splitlines()
             if (parts:=line.split()) and parts[0] in ('GEAR','NOSECONE')}
    if (actions.get('GEAR')!=(1.,0.) or 'NOSECONE' not in actions or
            not (0.<actions['NOSECONE'][0]<1. and actions['NOSECONE'][1]>0.)):
        raise ValueError('DG Lua extensions failed to operate or persist the gear and nose cone')
    animations={}
    for row in csv.DictReader((output/'flight-animations.csv').read_text().splitlines()):
        animations.setdefault(row['index'],[]).append(float(row['state']))
    if not any(states[0]==0. and states[-1]==1. and any(0.<s<1. for s in states) for states in animations.values()):
        raise ValueError('Stock DG deployment did not complete a mesh animation')
    if 'Lua error:' in (output/'console.txt').read_text():
        raise ValueError('Lua error in stock autopilot flight')
    graphics=json.loads((output/'graphics-lifecycle.json').read_text())
    if graphics!=dict(rendered_frames=48, successful_presents=48, context_deleted=True):
        raise ValueError('Native renderer did not finish the stock flight')
    if (output/'graphics-errors.txt').exists() and (output/'graphics-errors.txt').read_text().strip():
        raise ValueError('Graphics errors during stock flight')
    return dict(vessel=case['class'],cockpit=mode,frames=48,lua_yields=len(rows))


def run_stock_scenario(args,name,focus):
    scenario=args.assets/'Scenarios'/name
    if scenario.read_bytes()!=(HERE.parents[2]/'Scenarios'/name).read_bytes():
        raise ValueError('The staged scenario differs from its stock file: '+name)
    output=args.output/scenario.stem
    output.mkdir()
    config=output/'Orbiter.cfg'
    config.write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+'\nMenubarMode = 1\nInfobarMode = 1\n')
    command=[args.build/'orbiter-production','--config',config,'--scenario',scenario,
             '--save',output/'saved.scn','--assets',args.assets,'--data',args.data,'--planets',args.planets,
             '--modules',args.build/'NativeModules','--evidence',output,'--frames','60','--fixed-step','0.25','--run']
    with (output/'console.txt').open('w') as log:
        subprocess.run(command,cwd=output,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    if 'Lua error:' in (output/'console.txt').read_text():
        raise ValueError('Lua error in '+name)
    states=[r for r in csv.DictReader((output/'flight-state.csv').read_text().splitlines()) if r['object']==focus]
    if ([int(r['tick']) for r in states]!=list(range(61)) or any(r['focus']!=focus for r in states) or
            json.loads((output/'graphics-lifecycle.json').read_text())!=dict(rendered_frames=60,successful_presents=60,context_deleted=True)):
        raise ValueError('Stock flight or renderer did not finish: '+name)
    if name.endswith('Earth views.scn') and float(states[2]['seconds'])!=2500.:
        raise ValueError('The original Earth views script did not engage time acceleration')
    return dict(scenario=name,focus=focus,frames=60)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('assets','data','planets','build','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    for key in vars(args): setattr(args,key,getattr(args,key).resolve())
    args.output.mkdir(parents=True,exist_ok=False)
    assets=args.output/'assets'
    shutil.copytree(args.assets,assets)
    shutil.copyfile(HERE/'flight.lua',assets/'Script/phase6-flight.lua')
    results=[]
    for case in settings()['cases']:
        if 'stock_atmosphere' in case:
            for mode in (2,3):
                results.append(run_case(args.output,assets,case,mode,args))
                print('Passed',results[-1],flush=True)
    for name,focus in (('Delta-glider/Venus descent.scn','GL-01'),('2024 Edition/Earth views.scn','GL-01S'),
                       ('2024 Edition/The Alps in 3D.scn','GL-01S'),('Demo/DG ISS Approach.scn','DG-01')):
        results.append(run_stock_scenario(args,name,focus))
        print('Passed',results[-1],flush=True)
    (args.output/'flight-report.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':
    main()
