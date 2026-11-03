#!/usr/bin/env python3
"""Observe seven unchanged station scenarios in the preserved Windows application."""
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
sys.path[:0]=[str(HERE.parent/'StockScenarios'),str(HERE.parent/'Cockpit'),
              str(HERE.parent),str(HERE.parent/'Client')]
from inventory import ships
from stage import run as stage
from mesa_runtime import require,digest
from run_client import mesa_files,png
from compare_client import image_ssim


def source_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def settings():
    value=json.loads((HERE/'cases.json').read_text())
    existing=json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    for key in ('application_source','frames','fixed_step','epoch','image_ssim_minimum','budgets'):
        require(value[key]==existing[key],'Original station source/clock/budget differs: '+key)
    require(len(value['cases'])==7 and len({c['id'] for c in value['cases']})==7,
            'Incomplete original station matrix')
    paths=dict(value['station_files_sha256_lf'])
    paths.update({'Scenarios/'+c['scenario']:c['sha256_lf'] for c in value['cases']})
    for path,checksum in paths.items():
        original=subprocess.check_output(['git','-C',str(ROOT),'show',value['application_source']+':'+path])
        require(hashlib.sha256(original.replace(b'\r\n',b'\n')).hexdigest()==checksum and
                source_digest(ROOT/path)==checksum,'Original station source bytes differ: '+path)
    return value


def rows(path):
    with path.open(newline='',encoding='ascii') as stream:
        reader=csv.DictReader(stream);result=list(reader)
        require(reader.fieldnames and all(None not in r and None not in r.values() for r in result),
                'Malformed original station CSV: '+str(path))
        return result


def inspect_trace(out,case,config):
    expected=ships((ROOT/'Scenarios'/case['scenario']).read_bytes().decode('cp1252'))
    state=rows(out/'stock-vessel-state.csv');groups={}
    for row in state:
        require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','class')),
                'Nonfinite original station state')
        groups.setdefault(int(row['tick']),[]).append(row)
    require(set(groups)==set(range(61)),'Missing finalized original station ticks')
    initial_mjd=float(groups[0][0]['mjd'])
    for tick,group in groups.items():
        require(len(group)==len(expected) and {r['object']:r['class'].lower() for r in group}==
                {name:kind.lower() for name,kind in expected.items()},'Original station vessel manifest differs')
        require(all(float(r['seconds'])==tick*config['fixed_step'] for r in group),'Original station clock differs')
        require(all(abs(float(r['mjd'])-(initial_mjd+tick*config['fixed_step']/86400))<=config['budgets']['mjd_days']
                    for r in group),'Original station MJD clock differs')
        require(all(float(r['mass'])>0 and float(r['empty_mass'])>0 and float(r['fuel'])>=0 for r in group),
                'Original station mass or propellant is invalid')
        require(sum(r['focus']=='1' for r in group)==1,'Original station focus manifest differs')
    docks=rows(out/'stock-vessel-docks.csv');dock_keys=set()
    for row in docks:
        key=(int(row['tick']),row['object'],int(row['index']))
        require(key not in dock_keys,'Duplicate original docking port');dock_keys.add(key)
        require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','docked')),
                'Nonfinite original docking port')
    require(dock_keys=={(int(r['tick']),r['object'],i) for r in state for i in range(int(r['docks']))},
            'Incomplete original docking-port observations')
    stations=[r for r in state if r['class'].lower() in ('mir','wheel')]
    require(stations and all(r['version']=='0' and r['enable_focus']=='0' and r['meshes']=='1' and
            r['thrusters']=='0' and r['propellants']=='0' and r['docks']==('3' if r['class'].lower()=='mir' else '2')
            for r in stations),'Original configuration-defined station capabilities differ')
    return state,stations,groups


def loaded_modules(out,expected):
    bindings=json.loads((out/'mesa-bindings.json').read_text())
    mesa={name.casefold():entry for name,entry in bindings['runtime']['files'].items()}
    effective={name.casefold():entry for name,entry in bindings['bindings'].items()}
    system=Path(os.environ['SystemRoot']).resolve();result=[];names=set()
    for line in (out/'renderer-modules.txt').read_text().splitlines():
        path=Path(line).resolve();names.add(path.name.casefold())
        if path.suffix.lower() not in ('.dll','.exe'):continue
        require(out.resolve() in path.parents or system in path.parents,'Unrecorded external original DLL: '+str(path))
        checksum=digest(path);name=path.name.casefold()
        if out.resolve() in path.parents:
            if name in mesa:
                require(path.parent==out.resolve() and checksum==effective.get(name,{}).get('effective_sha256',mesa[name]['sha256']),
                        'Actual original Mesa DLL differs: '+name)
            else:
                require(checksum in expected.get(name,set()),'Actual original application/module bytes differ: '+str(path))
        result.append(dict(path=str(path),sha256=checksum))
    require({'opengl32.dll','oglclient.dll','productioncockpitdriver.dll'}<=names,
            'Required original graphics/observer modules were not loaded')
    return result


def inspect(out,case,config,expected_modules):
    failure=out/'stock-vessel-failure.txt'
    require(not failure.exists(),'Original station observer failed: '+(failure.read_text() if failure.exists() else ''))
    require((out/'stock-vessel-complete.txt').read_text().strip()=='60','Original station shutdown incomplete')
    state,stations,groups=inspect_trace(out,case,config)
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),
            'Original station graphics lifecycle incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Original station software-renderer identity or geometry differs')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Original station OpenGL error')
    console=(out/'console.txt').read_text(errors='replace')+(out/'Orbiter.log').read_text(errors='replace')
    for marker in ('Lua error:','LuaCall (','runtime error:','ERROR: AddressSanitizer','Could not find a module'):
        require(marker not in console,'Original station runtime failure: '+marker)
    expected=ships((ROOT/'Scenarios'/case['scenario']).read_bytes().decode('cp1252'))
    scene=rows(out/'scene.csv')
    require(set(expected)<={r['object'] for r in scene if r['type']=='vessel'},
            'Original complete stock mesh inventory missing')
    for name,kind in expected.items():
        if kind.lower() in ('mir','wheel'):
            meshes=[r for r in scene if r['object']==name and r['type']=='vessel']
            require(len(meshes)==1 and meshes[0]['name'].lower()==kind.lower(),
                    'Original station mesh identity differs')
    pixels=(out/'scene.rgba').read_bytes();require(len(pixels)==1280*720*4,'Incomplete original station framebuffer')
    profile=(out/'math-profile.txt').read_text().strip()
    require(profile in ('fma3','sse2'),'Unknown original station CRT implementation')
    files=('stock-vessel-state.csv','stock-vessel-docks.csv','stock-vessel-complete.txt',
           'scene.csv','scene.rgba','camera.csv','renderer-info.json','graphics-lifecycle.json',
           'renderer-modules.txt','invocation.json','mesa-bindings.json','math-profile.txt',
           'console.txt','Orbiter.log','Scenarios/Behavior.scn','Orbiter.cfg')
    return dict(status='passed',declared_vessels=len(expected),finalized_ticks=len(groups),
        initial_mjd=float(state[0]['mjd']),actual_math=profile,renderer=renderer,lifecycle=life,
        loaded_modules=loaded_modules(out,expected_modules),
        station_initial_capabilities=[r for r in stations if r['tick']=='0'],
        files_sha256={name:digest(out/name) for name in files})


def capture(a):
    config=settings()
    require(sys.platform=='win32','Original station capture requires native Windows')
    for name in ('executable','data','planets','mesa','output'):setattr(a,name,getattr(a,name).resolve())
    require(not a.output.exists(),'Original station output exists; replacement is forbidden')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2')=='1')==(a.math_profile=='sse2'),
            'Original station CRT selection differs from requested profile')
    runtime=json.loads((a.executable.parent/'control-reference-runtime.json').read_text())
    preserved=json.loads((a.executable.parent/'test-runtime.json').read_text())
    require(runtime['application_source']==preserved['source_commit']==config['application_source'],
            'Wrong preserved original station application/SDK')
    for name,checksum in {**preserved['files'],**runtime['client_files_sha256']}.items():
        if name!='Modules/Plugin/ProductionCockpitDriver.dll':
            require(digest(a.executable.parent/name)==checksum,'Preserved application/SDK/client bytes differ: '+name)
    producer=a.executable.parent/'Modules/Plugin/ProductionCockpitDriver.dll'
    binary_hashes=dict(application=digest(a.executable),observer=digest(producer))
    expected_modules={}
    for name,checksum in {**preserved['files'],**runtime['client_files_sha256'],
                          'Modules/Plugin/ProductionCockpitDriver.dll':binary_hashes['observer']}.items():
        expected_modules.setdefault(Path(name).name.casefold(),set()).add(checksum)
    a.output.mkdir(parents=True)
    report=dict(status='running',phase6_complete=False,host='original-windows',configuration=a.configuration,
        math_profile=a.math_profile,application_source=config['application_source'],runtime=runtime,
        binary_sha256=binary_hashes,settings_sha256_lf=source_digest(HERE/'cases.json'),
        source_sha256_lf={p.name:source_digest(p) for p in HERE.iterdir() if p.is_file()},cases={},failures={})
    manifest=a.output/'stock-vessels.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for case in config['cases']:
        out=None
        try:
            runs=[];observed=[]
            for repeat in (1,2):
                out=a.output/(case['id']+'-'+str(repeat));runs.append(out)
                source=(ROOT/'Scenarios'/case['scenario']).read_bytes()
                def configure(directory):
                    cfg=directory/'Orbiter.cfg'
                    cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (directory/'Scenarios/Behavior.scn').write_bytes(source)
                    for name,checksum in config['station_files_sha256_lf'].items():
                        require(source_digest(directory/name)==checksum,'Staged original station resource differs: '+name)
                    (directory/'ogl-evidence.enabled').touch();mesa_files(a.mesa,directory)
                stage(a.executable,a.data,a.planets,out,config,configure)
                require((out/'Scenarios/Behavior.scn').read_bytes()==source,'Original stock scenario bytes changed')
                require(digest(out/a.executable.name)==binary_hashes['application'] and
                        digest(out/'Modules/Plugin/ProductionCockpitDriver.dll')==binary_hashes['observer'],
                        'Executed original station application/observer differs')
                observed.append(inspect(out,case,config,expected_modules))
                png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
                if a.math_profile=='sse2':require(observed[-1]['actual_math']=='sse2','Original station SSE2 was not selected')
            for name in ('stock-vessel-state.csv','stock-vessel-docks.csv'):
                require((runs[0]/name).read_bytes()==(runs[1]/name).read_bytes(),'Original station repeat differs: '+name)
            similarity=image_ssim((runs[0]/'scene.rgba').read_bytes(),(runs[1]/'scene.rgba').read_bytes(),1280,720)
            require(similarity>=config['image_ssim_minimum'],'Original station image repeat exceeds unchanged budget')
            report['cases'][case['id']]=dict(scenario=case['scenario'],runs=observed,repeat_ssim=similarity)
            print(case['id'],'passed',flush=True)
        except Exception as error:
            failure=out/'stock-vessel-failure.txt' if out else None
            report['failures'][case['id']]=str(error)+(': '+failure.read_text().strip() if failure and failure.exists() else '')
            print(case['id'],report['failures'][case['id']],flush=True)
        save()
    require(binary_hashes==dict(application=digest(a.executable),observer=digest(producer)),
            'Original station application/observer changed during capture')
    report['status']='passed' if not report['failures'] and len(report['cases'])==7 else 'failed';save()
    require(report['status']=='passed','Original station observation failed; native qualification remains forbidden')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-inputs',action='store_true')
    for name in ('executable','data','planets','mesa','output'):p.add_argument('--'+name,type=Path)
    p.add_argument('--configuration',choices=('Debug','Release'))
    p.add_argument('--math-profile',choices=('automatic','sse2'))
    a=p.parse_args()
    if a.verify_inputs:
        value=settings();print('Verified seven scenarios and four station resources against '+value['application_source'])
    else:
        require(all(getattr(a,name) is not None for name in
                    ('executable','data','planets','mesa','output','configuration','math_profile')),'Missing original capture arguments')
        capture(a)
