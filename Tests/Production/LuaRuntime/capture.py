#!/usr/bin/env python3
"""Capture original Windows Lua scheduling and stock DG AAP behavior."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from reference import fixture, inspect, stage, git, mesa_files, require, rows, image_ssim
from frozen import metadata
from regression import mfd_images
from mesa_runtime import digest


def settings():
    config = json.loads((HERE/'cases.json').read_text())
    parent = metadata(HERE.parent/'Cockpit/Reference/provenance.json')
    require(config['application_source']==parent['application_source'], 'Original Lua runtime source differs')
    require(config['budgets']==parent['budgets'] and config['image_ssim_minimum']==.98, 'Frozen budgets differ')
    return config


def lua_fixture(case):
    scenario=fixture(case)
    if 'stock_atmosphere' not in case:
        return scenario
    path=case['stock_atmosphere']
    root=HERE.parents[2]
    original=subprocess.check_output(['git','-C',str(root),'show','f725194209634f7fd5d1d44d426cfa9b5e303e37:'+path]).decode().replace('\r\n','\n')
    marker=case['stock_ship']+':'+case['class']+'\n'
    body=original.split(marker,1)[1].split('\nEND\n',1)[0]
    start=scenario.index('DG:'+case['class']+'\n')
    end=scenario.index('\nEND\n',start)
    return scenario[:start]+'DG:'+case['class']+'\n'+body+scenario[end:]


def validate(directory,case):
    events=rows(directory/'lua-events.csv')
    expected=['sync_initial']
    if case['target']=='DG':expected+=['aap_loaded']
    expected+=['sync_override','async_one','async_two']+[f'yield_{i}' for i in range(1,5)]+['yield_done']
    if case['target']=='DG':
        expected+=['aap_started']
        if 'stock_atmosphere' in case:expected+=['aap_retargeted','aap_slowed']
        expected+=['aap_stopped']
    expected+=['complete']
    require([row['event'] for row in events]==expected,'Original Lua event sequence differs')
    require(all(float(row['step'])==.25 for row in events),'Original Lua step differs')
    yields=[float(row['seconds']) for row in events if row['event'].startswith('yield_')]
    require(all(b-a==.25 for a,b in zip(yields,yields[1:])),'Original proc.skip did not yield exactly one frame')
    require((directory/'lua-isolation.txt').read_text()=='isolated','Original Lua environments share globals')
    control=rows(directory/'lua-controls.csv')
    require([int(row['tick']) for row in control]==list(range(61)),'Incomplete original AAP controls')
    if case['target']=='DG':
        require(any(abs(float(row['elevator']))>0 or abs(float(row['aileron']))>0 for row in control if 31<=int(row['tick'])<=45),'Original AAP did not actuate stock control surfaces')
        # The post-step stop clears the demands. Actual stock surfaces slew
        # back from saturation by 0.25 per subsequent quarter-second frame.
        if 'stock_atmosphere' in case:
            air=rows(directory/'lua-air.csv')
            require(len(air)==61 and all(float(r['density'])>0 and float(r['dynamic_pressure'])>0 for r in air),
                    'Original stock AAP fixture is not in atmospheric flight')
            # Both original states reach idle at the low target. DG-S is already
            # at idle before AAP starts. Retarget twice to exercise both directions.
            require(all(float(r['main'])==0 for r in control[32:39]), 'Original low speed target did not idle main thrust')
            require(all(float(r['main'])==1 for r in control[40:43]), 'Original high speed target did not engage full main thrust')
            require(all(float(r['main'])==0 for r in control[44:46]), 'Original lower speed retarget did not return main thrust to idle')
        else:
            require(max(float(r['main']) for r in control[31:46]) > float(control[30]['main']), 'Original AAP did not apply main thrust')
        for key in ('elevator','aileron'):
            start=float(control[46][key])
            for row in control[46:]:
                remaining=max(0.,abs(start)-.25*(int(row['tick'])-46))
                require(float(row[key])==(remaining if start>=0 else -remaining),
                        'Original AAP surface rundown differs: '+key+' at '+row['tick'])
    return dict(events=len(events),environment_isolation=True,frame_yielding=True,aap_controls=case['target']=='DG')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args(); config=settings()
    require(sys.platform=='win32','Original Lua capture requires native Windows')
    runtime=json.loads((args.orbiter.parent/'control-reference-runtime.json').read_text())
    require(runtime['application_source']==config['application_source'],'Wrong original Lua application')
    require(not args.output.exists(),'Original Lua capture output exists')
    args.output.mkdir(parents=True)
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    report=dict(status='pending',source=git('rev-parse','HEAD').decode().strip(),runtime=runtime,configuration=args.configuration,cases={},failures={})
    for case in config['cases']:
        try:
            directories=[]; observations=[]
            for repeat in (1,2):
                directory=args.output.resolve()/(case['id']+'-'+str(repeat))
                def configure(directory):
                    cfg=directory/'Orbiter.cfg'
                    cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (directory/'Scenarios/Behavior.scn').write_text(lua_fixture(case))
                    profile='atmosphere' if 'stock_atmosphere' in case else 'orbit'
                    (directory/'cockpit-case.txt').write_text(f"{case['target']} 60 {case['cockpit']} 1 2 1 {profile}\n")
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):
                        (directory/name).write_text('Original Lua and AAP observation\n')
                    mesa_files(args.mesa.resolve(),directory)
                stage(args.orbiter.resolve(),args.data.resolve(),args.planets.resolve(),directory,{**case,'frames':60,'fixed_step':.25,'epoch':config['epoch']},configure)
                observed=inspect(directory,case,config);observed['lua']=validate(directory,case)
                modules=(directory/'lua-loaded.txt').read_text().splitlines()
                require(modules==['LuaInline.dll','LuaInterpreter.dll','lua.dll'],'Original loaded Lua module identities differ')
                observed['lua_modules']={name:digest(directory/name) for name in modules}
                for name,checksum in observed['lua_modules'].items():
                    require(checksum==digest(args.orbiter.parent/name),'Original loaded Lua bytes differ: '+name)
                if case['target']=='DG':
                    observed['aap_script_sha256']=digest(directory/'Script/DG/aap.lua')
                observations.append(observed);directories.append(directory)
            for name in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv','lua-events.csv','lua-controls.csv','lua-air.csv'):
                require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original Lua repeat differs: '+name)
            similarity={str(f):image_ssim((directories[0]/f'instrument-{f}.rgba').read_bytes(),(directories[1]/f'instrument-{f}.rgba').read_bytes(),1280,720) for f in (20,50)}
            require(min(similarity.values())>=.98,'Original Lua image repeat exceeds budget')
            report['cases'][case['id']]=dict(runs=observations,repeat_ssim=similarity)
        except Exception as error:
            failure=directory/'cockpit-failure.txt'
            report['failures'][case['id']]=str(error)+(': '+failure.read_text() if failure.exists() else '')
    report['status']='failed' if report['failures'] else 'passed'
    (args.output/'lua-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],failures=report['failures']),indent=2))
    require(report['status']=='passed','Original Lua/AAP reference failed')

if __name__=='__main__':main()
