#!/usr/bin/env python3
"""Measure every vessel in all 38 complete remaining-module scenes on native Windows."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'StockVessels'),str(HERE.parent),str(HERE.parent/'Client')]
from inputs import ROOT,CASE_FILE,settings,require,digest,sha_lf,entry_point,recordings,inspect_inputs
from stage_original import run as stage
from run_client import mesa_files,png
from compare_client import image_ssim
from clock_observation import inspect_clock

spec=importlib.util.spec_from_file_location('remaining_shared_stock',HERE.parent/'StockVessels/original.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
sys.path.insert(0,str(HERE.parent/'StockVessels'))

TRACES=('stock-vessel-state.csv','stock-vessel-docks.csv','stock-population.csv',
        'stock-vessel-propellants.csv','stock-vessel-thrusters.csv','stock-vessel-attachments.csv','stock-playback.csv',
        'stock-vessel-meshes.csv')


def rows(path):
    with path.open(newline='',encoding='ascii') as source:
        reader=csv.DictReader(source);result=list(reader)
    require(reader.fieldnames and all(None not in row and None not in row.values() for row in result),
            'Malformed original remaining-stock trace: '+path.name)
    return result


def finite(row,strings):
    require(all(math.isfinite(float(value)) for key,value in row.items() if key not in strings),
            'Nonfinite original remaining-stock value')


def indexed(out,name,keys,strings):
    result={}
    for row in rows(out/name):
        finite(row,strings);key=tuple(row[key] for key in keys)
        require(key not in result,'Duplicate '+name+' observation');result[key]=row
    return result


def inspect_resources(propellants,thrusters):
    for row in propellants.values():
        require(float(row['mass'])>=0 and float(row['max_mass'])>=0 and float(row['efficiency'])>=0,
                'Invalid public propellant resource')
    histories={}
    for (tick,name,index),row in propellants.items():
        identity=row['resource_id']
        require(str(int(identity))==identity and int(identity)>0,'Invalid sampled public resource ID')
        history=histories.setdefault(identity,dict(owner=(name,index),ticks=set()))
        require(history['owner']==(name,index) and int(tick) not in history['ticks'],
                'Sampled public resource ownership changed or duplicated')
        history['ticks'].add(int(tick))
    for history in histories.values():
        seen=history['ticks']
        require(seen==set(range(min(seen),max(seen)+1)),'A retired resource sample ID was resurrected')
    external=0;retired=0;retired_nonzero=0
    for row in thrusters.values():
        owner=row['resource_object'];index=row['resource_index'];identity=row['resource_id']
        kind=row['resource_state'];tick=int(row['tick']);seen=int(row['resource_seen_tick'])
        if kind=='none':
            require(not owner and index=='-1' and identity=='0' and seen==-1,'Absent thruster resource has an identity')
        else:
            require(kind in ('live','retired') and identity in histories,'Thruster tank has no public ownership witness')
            history=histories[identity]
            require(history['owner']==(owner,index),'Thruster resource ownership witness differs')
            if kind=='live':
                current=propellants.get((row['tick'],owner,index))
                require(current is not None and current['resource_id']==identity and seen==tick,
                        'Live thruster resource absent from the complete actual population')
                external+=owner!=row['object']
            else:
                require(tick not in history['ticks'] and seen<tick and
                        seen==max((t for t in history['ticks'] if t<tick),default=-1) and seen>=0,
                        'Retired thruster resource lacks its last prior ownership witness')
                retired+=1;retired_nonzero+=float(row['level'])!=0
    return dict(external_tank_bindings=external,retired_resource_bindings=retired,
                retired_resource_nonzero_levels=retired_nonzero)


def inspect_trace(out,case,config):
    recording_count=inspect_inputs(out,case,config)
    state=indexed(out,'stock-vessel-state.csv',('tick','object'),('object','class'))
    population=indexed(out,'stock-population.csv',('tick',),())
    ticks={str(tick) for tick in range(config['frames']+1)}
    require({key[0] for key in state}==ticks and set(population)=={(tick,) for tick in ticks},
            'Incomplete finalized population ticks')
    initial={row['object']:row['class'] for (tick,_),row in state.items() if tick=='0'}
    require(all(initial.get(name,'').lower()==kind.lower() for name,kind in case['declared_vessels'].items()),
            'An original declared vessel or class is absent at initialization')
    initial_mjd=float(next(row['mjd'] for (tick,_),row in state.items() if tick=='0'))
    matched_clock=None;simulation_times=None
    if config.get('protocol')=='remaining-stock-matched-clock-v2':
        from matched_clock import inspect_matched_clock
        matched_clock,simulation_times=inspect_matched_clock(out,config)
    for tick in ticks:
        group=[row for (number,_),row in state.items() if number==tick]
        require(len(group)==int(population[(tick,)]['count']) and len(group)>0,
                'Complete actual vessel population differs')
        require(sum(row['focus']=='1' for row in group)==1,'Actual population focus differs')
        expected_time=simulation_times[tick] if simulation_times is not None else int(tick)*config['fixed_step']
        require(all(float(row['seconds'])==expected_time and
                    abs(float(row['mjd'])-(initial_mjd+expected_time/86400))<=config['budgets']['mjd_days']
                    for row in group),'Original remaining-stock clock changed')
        require(all(float(row['mass'])>0 and float(row['empty_mass'])>0 and float(row['fuel'])>=0 for row in group),
                'Original vessel mass or fuel is invalid')
    docks=indexed(out,'stock-vessel-docks.csv',('tick','object','index'),('object','docked'))
    propellants=indexed(out,'stock-vessel-propellants.csv',('tick','object','index'),('object',))
    thrusters=indexed(out,'stock-vessel-thrusters.csv',('tick','object','index'),('object','resource_object','resource_state'))
    attachments=indexed(out,'stock-vessel-attachments.csv',('tick','object','to_parent','index'),('object','id','attached'))
    playback=indexed(out,'stock-playback.csv',('tick','object'),('object',))
    meshes=indexed(out,'stock-vessel-meshes.csv',('tick','object','index'),('object','name'))
    for collection,count,label in ((docks,'docks','docking ports'),(propellants,'propellants','propellant resources'),
                                   (thrusters,'thrusters','thrusters'),(meshes,'meshes','mesh slots')):
        expected={(tick,name,str(i)) for (tick,name),row in state.items() for i in range(int(row[count]))}
        require(set(collection)==expected,'Incomplete actual '+label)
    expected={(tick,name,str(parent),str(i)) for (tick,name),row in state.items()
              for parent in (0,1) for i in range(int(row['parents' if parent else 'children']))}
    require(set(attachments)==expected,'Incomplete actual parent/child attachment ports')
    require(set(playback)==set(state),'Incomplete actual per-vessel playback flags')
    require(all(row['present'] in ('0','1') and row['template'] in ('0','1') for row in meshes.values()),
            'Invalid actual mesh-slot observation')
    for key,row in playback.items():
        require(row['playback'] in ('0','1'),'Invalid actual playback flag')
        if key[0]=='0':require(row['playback']==('1' if key[1] in case['playback_vessels'] else '0'),
                               'Original requested playback silently fell back or substituted a vessel')
    resources=inspect_resources(propellants,thrusters)
    for row in [*docks.values(),*attachments.values()]:
        peer=row.get('docked',row.get('attached'))
        require(not peer or (row['tick'],peer) in state,'Attached/docked peer absent from actual population')
    result=dict(initial_declared_vessels=len(case['declared_vessels']),initial_actual_vessels=len(initial),
        initial_generated_vessels={name:kind for name,kind in initial.items() if name not in case['declared_vessels']},
        observed_classes=sorted({row['class'] for row in state.values()}),finalized_ticks=len(ticks),
        all_vessel_rows=len(state),docking_rows=len(docks),propellant_rows=len(propellants),thruster_rows=len(thrusters),
        attachment_rows=len(attachments),playback_rows=len(playback),mesh_rows=len(meshes),
        **resources,recording_files=recording_count)
    if matched_clock is not None:result['matched_clock_observation']=matched_clock
    return result


def inspect_artifacts(out,case,config):
    require(not (out/'stock-vessel-failure.txt').exists(),'Original SDK detail observer reported a failure')
    require((out/'stock-vessel-complete.txt').read_text().strip()=='60','Original stock session ended early')
    require(json.loads((out/'process-result.json').read_text())['returncode']==0,'Original process did not return zero')
    result=inspect_trace(out,case,config)
    require(json.loads((out/'graphics-lifecycle.json').read_text())==
            dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Original graphics teardown incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Original renderer or viewport changed')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Original OpenGL diagnostics')
    text=(out/'console.txt').read_text(errors='replace')+(out/'Orbiter.log').read_text(errors='replace')
    require(not any(marker in text for marker in ('Lua error:','LuaCall (','runtime error:',
        'Could not find a module','ERROR: AddressSanitizer','Assertion failed')),'Original scene runtime diagnostic or module fallback')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Original framebuffer incomplete')
    scene=rows(out/'scene.csv')
    expected={(row['object'],row['index']) for row in rows(out/'stock-vessel-meshes.csv')
              if row['tick']=='50' and row['present']=='1'}
    actual=[(row['object'],row['index']) for row in scene if row['type']=='vessel']
    require(set(actual)==expected and len(actual)==len(expected),
            'Original renderer omits/duplicates a present mesh or substitutes a nonphysical object')
    frame={row['object']:row['class'] for row in rows(out/'stock-vessel-state.csv') if row['tick']=='50'}
    require(all(row['class'].lower()==frame[row['object']].lower() for row in scene if row['type']=='vessel'),
            'Original renderer vessel class differs from the actual physics object')
    actual_math=(out/'math-profile.txt').read_text().strip()
    require(actual_math in ('fma3','sse2'),'Unknown actual original math implementation')
    names=[*TRACES,'stock-vessel-complete.txt','scene.csv','scene.rgba','camera.csv','renderer-info.json',
        'graphics-lifecycle.json','renderer-modules.txt','invocation.json','mesa-bindings.json','math-profile.txt',
        'console.txt','Orbiter.log','Orbiter.cfg','process-result.json',case['scenario_entry_point'],*recordings(case,config)]
    names.extend(item['target'] for item in config['delivery_repairs'])
    return dict(result,status='captured',process_returncode=0,actual_math=actual_math,renderer=renderer,
                files_sha256={name:digest(out/name) for name in names})


def source_files():
    shared_files=('.github/workflows/original-remaining-stock.yml',
        'Tests/Production/StockVessels/Observation.h','Tests/Production/StockVessels/original.py',
        'Tests/Production/StockScenarios/inventory.py','Tests/Production/behavior_suite.py','Tests/Production/mesa_runtime.py',
        'Tests/Production/Client/run_client.py','Tests/Production/Client/compare_client.py',
        'Tests/Production/Fixtures/Orbiter.cfg','Tests/Production/Cockpit/cases.json','Tests/Production/Cockpit/stage.py',
        'Tests/Production/ApplicationObservation.h','Tests/Production/production-source.lock.json')
    return [path for path in HERE.iterdir() if path.is_file()]+[ROOT/name for name in shared_files]


def capture(a):
    require(sys.platform=='win32','Original remaining-stock observations require native Windows')
    config=settings();require(not a.output.exists(),'Original measurement output replacement forbidden')
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2')=='1')==(a.math_profile=='sse2'),'Requested original math differs')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    root=a.executable.parent;metadata=json.loads((root/'test-runtime.json').read_text())
    runtime=json.loads((root/'control-reference-runtime.json').read_text())
    require(metadata['source_commit']==runtime['application_source']==config['application_source'],'Preserved source identity differs')
    observer='Modules/Plugin/ProductionCockpitDriver.dll'
    protected={name:value for name,value in {**metadata['files'],**runtime['client_files_sha256']}.items() if name!=observer}
    require(all(digest(root/name)==value for name,value in protected.items()),'Preserved SDK/application/client changed')
    observer_sha=digest(root/observer);expected={}
    for name,checksum in {**protected,observer:observer_sha}.items():expected.setdefault(Path(name).name.casefold(),set()).add(checksum)
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    sources={path.relative_to(ROOT).as_posix():sha_lf(path) for path in source_files()}
    for name,checksum in sources.items():
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(hashlib.sha256(frozen.replace(b'\r\n',b'\n')).hexdigest()==checksum,'Observer differs from immutable producer')
    a.output.mkdir(parents=True)
    report=dict(status='running',phase6_complete=False,native_admission_qualified=False,host='original-windows',
        protocol=config['protocol'],producer_commit=producer,application_source=config['application_source'],
        configuration=a.configuration,math_profile=a.math_profile,settings_sha256_lf=sha_lf(CASE_FILE),
        source_sha256_lf=sources,preserved_files_sha256=protected,observer_sha256=observer_sha,cases={},failures={})
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for case in config['cases']:
            paths=[];runs=[]
            try:
                for repeat in (1,2):
                    out=a.output/(case['id']+'-'+str(repeat));paths.append(out)
                    def configure(directory):
                        path=directory/'Orbiter.cfg'
                        path.write_text(path.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                            '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                        scenario=entry_point(directory,case);scenario.parent.mkdir(parents=True,exist_ok=True)
                        scenario.write_bytes((ROOT/case['scenario_entry_point']).read_bytes())
                        for kind in set(case['declared_vessels'].values()):
                            item=config['classes'][kind]
                            require(sha_lf(directory/item['target'])==item['sha256_lf'],'Original staged class configuration differs')
                        (directory/'ogl-evidence.enabled').touch();mesa_files(a.mesa,directory)
                    stage(a.executable,a.data,a.planets,out,config,case,configure)
                    require(digest(out/a.executable.name)==protected[a.executable.name] and digest(out/observer)==observer_sha,
                            'Staged application or observer differs')
                    result=inspect_artifacts(out,case,config)
                    result['loaded_modules']=shared.loaded_modules(out,expected)
                    loaded={Path(item['path'].replace('\\','/')).name.casefold() for item in result['loaded_modules']}
                    for kind in set(case['declared_vessels'].values()):
                        item=config['classes'][kind]
                        if item['module']:require(Path(item['original_module']).name.casefold() in loaded,
                                                  'Original declared vessel DLL was not loaded: '+kind)
                    runs.append(result);png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
                for name in (*TRACES,'camera.csv'):
                    require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Original remaining-stock repeat trace differs: '+name)
                score=image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(score>=config['image_ssim_minimum'],'Original remaining-stock repeat full-frame budget failed')
                report['cases'][case['id']]=dict(scenario=case['scenario'],runs=runs,repeat_ssim=score)
                print(case['id'],case['scenario'],'captured twice',flush=True)
            except Exception as error:
                report['failures'][case['id']]=str(error);print(case['id'],'failed:',error,flush=True)
            save()
        require(all(digest(root/name)==value for name,value in protected.items()) and digest(root/observer)==observer_sha,
                'Preserved package or observer changed during measurements')
        require(sources=={path.relative_to(ROOT).as_posix():sha_lf(path) for path in source_files()},'Observer sources changed during measurements')
        report.update(preserved_runtime_unchanged=True,observer_sources_unchanged=True,
            status='captured-awaiting-independent-audit' if len(report['cases'])==38 and not report['failures'] else 'incomplete')
        require(report['status']=='captured-awaiting-independent-audit','Original remaining-stock capture incomplete; no native admission')
    finally:save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-inputs',action='store_true')
    for name in ('executable','data','planets','mesa','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve())
    p.add_argument('--configuration',choices=('Debug','Release'));p.add_argument('--math-profile',choices=('automatic','sse2'))
    a=p.parse_args()
    if a.verify_inputs:
        value=settings();print('Verified 38 complete unchanged scenes,',len(value['classes']),'classes and',len(value['recording_files_sha256_lf']),'recording files');return
    require(all(getattr(a,name) is not None for name in ('executable','data','planets','mesa','output','configuration','math_profile')),
            'All preserved capture arguments required')
    capture(a)


if __name__=='__main__':main()
