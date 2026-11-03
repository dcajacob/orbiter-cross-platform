#!/usr/bin/env python3
"""Observe four complete unchanged legacy ISS scenes in preserved native Windows."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'StockVessels'),str(HERE.parent/'StockScenarios'),
              str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
# Load shared read-only helpers under a distinct name: this file is also named original.py.
import importlib.util
spec=importlib.util.spec_from_file_location('stock_station_observer',HERE.parent/'StockVessels/original.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
from inventory import ships
from stage import run as stage
from mesa_runtime import require,digest
from run_client import mesa_files,png
from compare_client import image_ssim

sha_lf=shared.source_digest
rows=shared.rows


def settings():
    config=json.loads((HERE/'cases.json').read_text())
    accepted=json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    for key in ('application_source','frames','fixed_step','epoch','image_ssim_minimum','budgets'):
        require(config[key]==accepted[key],'Original legacy station clock/source/budget differs: '+key)
    require(config['suite']=='legacy-stations' and len(config['cases'])==4 and
            len({c['id'] for c in config['cases']})==4,'Original legacy station matrix incomplete')
    files=dict(config['resources_sha256_lf'])
    files.update({'Scenarios/'+c['scenario']:c['sha256_lf'] for c in config['cases']})
    for name,expected in files.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',config['application_source']+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected==sha_lf(ROOT/name),
                'Original legacy station source differs: '+name)
    return config


def inspect_trace(out,case,config):
    scenario=out/'Scenarios/Behavior.scn'
    require(sha_lf(scenario)==case['sha256_lf'],'Executed legacy station scenario changed')
    invocation=json.loads((out/'invocation.json').read_text())
    require(digest(scenario)==invocation['input_sha256']['Scenarios/Behavior.scn'],
            'Executed legacy station scenario changed after staging')
    expected=ships((ROOT/'Scenarios'/case['scenario']).read_bytes().decode('cp1252'))
    state=rows(out/'stock-vessel-state.csv');groups={}
    for row in state:
        require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','class')),
                'Nonfinite original legacy station state')
        groups.setdefault(int(row['tick']),[]).append(row)
    require(set(groups)==set(range(config['frames']+1)),'Incomplete original legacy station ticks')
    initial_mjd=float(groups[0][0]['mjd'])
    for tick,group in groups.items():
        require(len(group)==len(expected) and {r['object']:r['class'].lower() for r in group}==
                {name:kind.lower() for name,kind in expected.items()},'Incomplete original legacy scene manifest')
        require(all(float(r['seconds'])==tick*config['fixed_step'] for r in group),'Original legacy scene clock differs')
        require(all(abs(float(r['mjd'])-(initial_mjd+tick*config['fixed_step']/86400))<=config['budgets']['mjd_days']
                    for r in group),'Original legacy scene MJD differs')
        require(all(float(r['mass'])>0 and float(r['empty_mass'])>0 and float(r['fuel'])>=0 for r in group),
                'Original legacy scene mass or fuel is invalid')
        require(sum(r['focus']=='1' for r in group)==1,'Original legacy scene focus manifest differs')
    ports=rows(out/'stock-vessel-docks.csv');keys=set()
    for row in ports:
        key=(int(row['tick']),row['object'],int(row['index']))
        require(key not in keys,'Duplicate original legacy docking port');keys.add(key)
        require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','docked')),
                'Nonfinite original legacy docking port')
    require(keys=={(int(r['tick']),r['object'],i) for r in state for i in range(int(r['docks']))},
            'Incomplete original legacy docking ports')
    observed=[r for r in state if r['class'].lower() in ('iss','module1')]
    require(any(r['class'].lower()=='iss' for r in observed),'Original legacy ISS missing')
    for row in observed:
        legacy_iss=row['class'].lower()=='iss'
        require(row['version']=='0' and row['meshes']=='1' and row['thrusters']=='0' and row['propellants']=='0' and
                int(row['docks'])==(3 if legacy_iss else 2),'Original configuration-defined legacy capabilities differ')
        require(float(row['empty_mass'])==float(row['mass'])==(450000 if legacy_iss else 8000) and
                float(row['fuel'])==0 and float(row['size'])==(55 if legacy_iss else 6),
                'Original legacy config mass, fuel or size differs')
        expected_pmi=(395,559,290) if legacy_iss else (7.7,7.7,2.3)
        require(tuple(float(row[k]) for k in ('pmix','pmiy','pmiz'))==expected_pmi,
                'Original legacy configuration inertia differs')
        if legacy_iss:
            require(row['enable_focus']=='0' and row['xpdr']=='1' and
                    tuple(float(row[k]) for k in ('csx','csy','csz'))==(897.2,3641.3,610.8),
                    'Original legacy ISS configuration capabilities differ')
    return dict(declared_vessels=len(expected),finalized_ticks=len(groups),all_vessel_rows=len(state),
                docking_rows=len(ports),legacy_initial_capabilities=[r for r in observed if r['tick']=='0'])


def inspect_artifacts(out,case,config):
    require(not (out/'stock-vessel-failure.txt').exists(),'Original SDK observer reported failure')
    require((out/'stock-vessel-complete.txt').read_text().strip()=='60','Original legacy normal session end incomplete')
    result=inspect_trace(out,case,config)
    require(json.loads((out/'graphics-lifecycle.json').read_text())==
            dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Original legacy graphics teardown incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Original legacy renderer or viewport differs')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Original legacy OpenGL errors')
    text=(out/'console.txt').read_text(errors='replace')+(out/'Orbiter.log').read_text(errors='replace')
    require(not any(x in text for x in ('Lua error:','LuaCall (','runtime error:','Could not find a module',
                                      'ERROR: AddressSanitizer','Assertion failed')),'Original legacy scene runtime failure')
    expected=ships((ROOT/'Scenarios'/case['scenario']).read_bytes().decode('cp1252'))
    scene=rows(out/'scene.csv')
    require(set(expected)<={r['object'] for r in scene if r['type']=='vessel'},'Original complete legacy mesh inventory missing')
    for name,kind in expected.items():
        if kind.lower() in ('iss','module1'):
            meshes=[r for r in scene if r['object']==name and r['type']=='vessel']
            require(len(meshes)==1 and meshes[0]['name'].lower()==kind.lower(),'Original legacy mesh identity differs')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Original legacy full framebuffer incomplete')
    actual_math=(out/'math-profile.txt').read_text().strip()
    require(actual_math in ('fma3','sse2'),'Unknown actual original CRT')
    names=['stock-vessel-state.csv','stock-vessel-docks.csv','stock-vessel-complete.txt',
        'scene.csv','scene.rgba','camera.csv','renderer-info.json','graphics-lifecycle.json','renderer-modules.txt',
        'invocation.json','mesa-bindings.json','math-profile.txt','console.txt','Orbiter.log','Scenarios/Behavior.scn','Orbiter.cfg']
    return dict(result,status='captured',process_returncode=0,actual_math=actual_math,renderer=renderer,
                files_sha256={name:digest(out/name) for name in names})


def inspect(out,case,config,expected_modules):
    result=inspect_artifacts(out,case,config)
    result['loaded_modules']=shared.loaded_modules(out,expected_modules)
    return result


def sources():
    files=[p for p in HERE.iterdir() if p.is_file()]
    files += [HERE.parent/'StockVessels'/name for name in ('Driver.cpp','Observation.h','original.py')]
    files += [HERE.parent/'ApplicationObservation.h',HERE.parent/'Cockpit/stage.py',
              HERE.parent/'behavior_suite.py',HERE.parent/'StockScenarios/inventory.py',
              HERE.parent/'Client/run_client.py',HERE.parent/'Client/compare_client.py',
              HERE.parent/'mesa_runtime.py',HERE.parent/'Cockpit/cases.json']
    return {p.relative_to(ROOT).as_posix():sha_lf(p) for p in files}


def capture(a):
    require(sys.platform=='win32','Preserved original observations require native Windows')
    config=settings();require(not a.output.exists(),'Original legacy capture replacement forbidden')
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2')=='1')==(a.math_profile=='sse2'),'Requested original CRT differs')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    runtime_root=a.executable.parent
    runtime=json.loads((runtime_root/'control-reference-runtime.json').read_text())
    preserved=json.loads((runtime_root/'test-runtime.json').read_text())
    require(runtime['application_source']==preserved['source_commit']==config['application_source'],'Wrong preserved original SDK/application')
    protected={name:value for name,value in {**preserved['files'],**runtime['client_files_sha256']}.items()
               if name!='Modules/Plugin/ProductionCockpitDriver.dll'}
    require(all(digest(runtime_root/name)==value for name,value in protected.items()),'Preserved original package differs')
    observer='Modules/Plugin/ProductionCockpitDriver.dll';observer_sha=digest(runtime_root/observer)
    expected={}
    for name,value in {**protected,observer:observer_sha}.items():expected.setdefault(Path(name).name.casefold(),set()).add(value)
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    source=sources()
    for name,value in source.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==value,'Original observer differs from producer commit')
    a.output.mkdir(parents=True)
    report=dict(status='running',phase6_complete=False,host='original-windows',producer_commit=producer,
        application_source=config['application_source'],configuration=a.configuration,math_profile=a.math_profile,
        source_sha256_lf=source,settings_sha256_lf=sha_lf(HERE/'cases.json'),runtime=runtime,
        preserved_files_sha256=protected,observer_sha256=observer_sha,cases={},failures={})
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for case in config['cases']:
        observed=[];runs=[]
        try:
            for repeat in (1,2):
                out=a.output/(case['id']+'-'+str(repeat));runs.append(out)
                original=(ROOT/'Scenarios'/case['scenario']).read_bytes()
                def configure(directory):
                    path=directory/'Orbiter.cfg'
                    path.write_text(path.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (directory/'Scenarios/Behavior.scn').write_bytes(original)
                    for name,checksum in config['resources_sha256_lf'].items():
                        require(sha_lf(directory/name)==checksum,'Staged original legacy config or mesh differs')
                    (directory/'ogl-evidence.enabled').touch();mesa_files(a.mesa,directory)
                stage(a.executable,a.data,a.planets,out,config,configure)
                require(digest(out/a.executable.name)==protected[a.executable.name] and
                        digest(out/observer)==observer_sha,'Executed original application or observer differs')
                value=inspect(out,case,config,expected)
                if a.math_profile=='sse2':require(value['actual_math']=='sse2','Original SSE2 was not selected')
                observed.append(value);png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
            for file in ('stock-vessel-state.csv','stock-vessel-docks.csv'):
                require((runs[0]/file).read_bytes()==(runs[1]/file).read_bytes(),'Original legacy repeat trace differs')
            similarity=image_ssim((runs[0]/'scene.rgba').read_bytes(),(runs[1]/'scene.rgba').read_bytes(),1280,720)
            require(similarity>=config['image_ssim_minimum'],'Original legacy repeated image exceeds unchanged budget')
            report['cases'][case['id']]=dict(scenario=case['scenario'],runs=observed,repeat_ssim=similarity)
            print(case['id'],'captured twice',flush=True)
        except Exception as error:
            report['failures'][case['id']]=str(error)
            print(case['id'],'failed:',error,flush=True)
        save()
    require(all(digest(runtime_root/name)==value for name,value in protected.items()) and
            digest(runtime_root/observer)==observer_sha,'Preserved original package changed during capture')
    require(source==sources(),'Original observer sources changed during capture')
    report['observer_sources_unchanged']=True
    report['preserved_runtime_unchanged']=True
    report['status']='captured-awaiting-four-profile-audit' if len(report['cases'])==4 and not report['failures'] else 'failed'
    save();require(report['status']=='captured-awaiting-four-profile-audit','Original legacy observations incomplete; no native admission')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-inputs',action='store_true')
    for name in ('executable','data','planets','mesa','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve())
    p.add_argument('--configuration',choices=('Debug','Release'))
    p.add_argument('--math-profile',choices=('automatic','sse2'))
    a=p.parse_args()
    if a.verify_inputs:
        value=settings();print('Verified four unchanged complete scenarios and ISS/Module1 resources against',value['application_source'])
    else:
        require(all(getattr(a,name) is not None for name in
                    ('executable','data','planets','mesa','output','configuration','math_profile')),'Missing original observation argument')
        capture(a)
