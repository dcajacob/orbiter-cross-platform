#!/usr/bin/env python3
"""Observe all complete stock scenes in the explicitly repaired original Windows runtime."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('remaining_repaired_shared',HERE.parent/'RemainingStock/original.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
from stage_original import run as stage
from run_client import mesa_files,png
from compare_client import image_ssim
import data_inputs
import protocols
import configuration_input
require=shared.require;sha=shared.digest;sha_lf=shared.sha_lf
from execution import collect,worker_count
OBSERVER='Modules/Plugin/ProductionCockpitDriver.dll'


def settings(protocol=protocols.V1):
    return protocols.load(shared.settings(),protocol)


def selected_cases(config,requested):
    if requested is None:return config['cases']
    require(requested and len(requested)==len(set(requested)),'Unique nonempty diagnostic case selection required')
    selected=[case for case in config['cases'] if case['id'] in set(requested)]
    require({case['id'] for case in selected}==set(requested),'Unknown repaired diagnostic case')
    return selected


def inspect_artifacts(out,case,config):
    require(not (out/'stock-vessel-failure.txt').exists(),'Repaired SDK detail observer reported a failure')
    require((out/'stock-vessel-complete.txt').read_text().strip()==str(config['frames']),
            'Repaired stock session ended early')
    require(json.loads((out/'process-result.json').read_text())['returncode']==0,'Repaired process did not return zero')
    result=shared.inspect_trace(out,case,config)
    clock=shared.inspect_clock(out,config['frames'])
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=config['frames'],successful_presents=config['frames'],context_deleted=True),
            'Repaired graphics teardown incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Repaired renderer or viewport changed')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Repaired OpenGL diagnostics')
    text=(out/'console.txt').read_text(errors='replace')+(out/'Orbiter.log').read_text(errors='replace')
    require(not any(marker in text for marker in ('Lua error:','LuaCall (','runtime error:',
        'Could not find a module','ERROR: AddressSanitizer','Assertion failed')),'Repaired runtime diagnostic or module fallback')
    cfg=(out/'Orbiter.cfg').read_text()
    require(not re.search(r'^\s*(?:PropStages|PropStage\d+|PropSubsampling)\s*=',cfg,re.M|re.I),
            'Repaired reference overrides original production propagators')
    variant=json.loads((out/'reference-variant.json').read_text())
    initial_configuration=None
    if 'configuration_input' in json.loads((out/'invocation.json').read_text()):
        initial_configuration=configuration_input.inspect(out,configuration_input.expected(ROOT,variant['producer_commit'],'repaired-windows'))
    require(variant['protocol']==config['protocol'] and variant['protocol_sha256_lf']==sha_lf(protocols.path(config['protocol'])) and
            variant['original_application_and_sdk_source']==config['application_source'] and
            variant['frames']==config['frames'] and variant['fixed_step']==config['fixed_step'] and
            variant['capture_tick']==config['capture_tick'],'Executed reference variant differs')
    require(isinstance(variant['diagnostic_only'],bool) and case['id'] in variant['cases_requested'] and
            variant['cases_requested']==[item['id'] for item in selected_cases(config,variant['cases_requested'])] and
            (variant['diagnostic_only'] or variant['cases_requested']==[item['id'] for item in config['cases']]),
            'Executed complete-scene diagnostic/full-reference scope differs')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Repaired framebuffer incomplete')
    data_files=data_inputs.validate(json.loads((out/'actual-data-inputs.json').read_text()))
    summary=json.loads((out/'scene-summary.json').read_text())
    protocols.inspect_frame(summary,config,result.get('matched_clock_observation'))
    if config['protocol']==protocols.V2:
        require((out/protocols.MARKER).read_bytes()==protocols.marker_bytes(config),'Executed finalized-frame descriptor differs')
    scene=shared.rows(out/'scene.csv');tick=str(config['capture_tick'])
    expected={(row['object'],row['index']) for row in shared.rows(out/'stock-vessel-meshes.csv')
              if row['tick']==tick and row['present']=='1'}
    actual=[(row['object'],row['index']) for row in scene if row['type']=='vessel']
    require(set(actual)==expected and len(actual)==len(expected),'Repaired renderer omits or substitutes a physical mesh')
    frame={row['object']:row['class'] for row in shared.rows(out/'stock-vessel-state.csv') if row['tick']==tick}
    require(all(row['class'].lower()==frame[row['object']].lower() for row in scene if row['type']=='vessel'),
            'Repaired rendered class differs from physical object')
    actual_math=(out/'math-profile.txt').read_text().strip()
    require(actual_math in ('fma3','sse2'),'Unknown repaired reference CRT implementation')
    names=[*shared.TRACES,'stock-clock.csv','stock-vessel-complete.txt','scene.csv','scene.rgba','scene-summary.json','camera.csv',
        'renderer-info.json','graphics-lifecycle.json','renderer-modules.txt','invocation.json','mesa-bindings.json',
        'math-profile.txt','console.txt','Orbiter.log','Orbiter.cfg','process-result.json','reference-variant.json','actual-data-inputs.json',
        case['scenario_entry_point'],*shared.recordings(case,config)]
    names.extend(item['target'] for item in config['delivery_repairs'])
    if config['protocol']==protocols.V2:names.extend(('stock-step-clock.csv',protocols.MARKER))
    if initial_configuration is not None:names.append(configuration_input.SNAPSHOT)
    if (out/'process-timing.json').is_file():names.append('process-timing.json')
    observed=dict(result,status='captured',process_returncode=0,actual_math=actual_math,renderer=renderer,actual_simulation_data_files=data_files,clock_observation=clock,
                  files_sha256={name:sha(out/name) for name in names})
    if initial_configuration is not None:observed['configuration_input']=initial_configuration
    return observed


def source_files():
    paths={*shared.source_files(),*(p for p in HERE.iterdir() if p.is_file()),
           ROOT/'.github/workflows/repaired-remaining-stock.yml',
           ROOT/'.github/workflows/repaired-remaining-stock-diagnostics.yml',
           ROOT/'.github/workflows/matched-clock-remaining-stock.yml',
           ROOT/'.github/workflows/matched-clock-remaining-stock-full.yml'}
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if ROOT in path.parents and path.suffix=='.py':paths.add(path)
    return sorted(paths)


def capture(a):
    require(sys.platform=='win32','Repaired original observations require native Windows')
    config=settings(a.protocol);require(not a.output.exists(),'Fresh repaired capture required; replacement forbidden')
    cases=selected_cases(config,a.diagnostic_case);diagnostic=a.diagnostic_case is not None
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2')=='1')==(a.math_profile=='sse2'),'Requested CRT profile differs')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    root=a.executable.parent
    build=json.loads((root/'runtime-variant.json').read_text())
    require(build['status']=='built-awaiting-runtime-and-independent-audit' and build['protocol']==config['protocol'] and
            build['configuration']==a.configuration and build['original_application_and_sdk_source']==config['application_source'] and
            build['preserved_package_unchanged'],'Runtime variant is incomplete or misidentified')
    protected=build['runtime_files_sha256']
    require(all(sha(root/name)==value for name,value in protected.items()),'Runtime variant bytes changed')
    expected={}
    for name,value in protected.items():expected.setdefault(Path(name).name.casefold(),set()).add(value)
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(producer==build['producer_commit'],'Build and capture producers differ')
    paths=source_files();raw_sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    sources={p.relative_to(ROOT).as_posix():sha_lf(p) for p in paths}
    for name,value in {**build['source_sha256_lf'],**sources}.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value==sha_lf(ROOT/name),'Capture source differs from producer: '+name)
    original_data=data_inputs.inspect(a.data,a.planets)
    for name,value in original_data['lock_sha256_lf'].items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':Tests/Production/'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value,'Data lock differs from capture producer: '+name)
    a.output.mkdir(parents=True)
    variant=dict(protocol=config['protocol'],protocol_sha256_lf=sha_lf(protocols.path(config['protocol'])),
        original_application_and_sdk_source=config['application_source'],producer_commit=producer,
        runtime_variant_manifest_sha256=sha(root/'runtime-variant.json'),frames=config['frames'],
        fixed_step=config['fixed_step'],capture_tick=config['capture_tick'])
    variant.update(diagnostic_only=diagnostic,cases_requested=[case['id'] for case in cases])
    report=dict(status='running',host='repaired-original-windows',protocol=config['protocol'],producer_commit=producer,
        original_application_and_sdk_source=config['application_source'],configuration=a.configuration,math_profile=a.math_profile,
        protocol_sha256_lf=sha_lf(protocols.path(config['protocol'])),settings_sha256_lf=sha_lf(shared.CASE_FILE),
        source_sha256_lf=sources,source_raw_sha256=raw_sources,runtime_variant_manifest_sha256=sha(root/'runtime-variant.json'),
        actual_original_simulation_data=original_data,
        execution=dict(workers=a.workers,process_timeout_seconds=900,scene_repetitions='serial',aggregate_writes='main-thread'),
        diagnostic_only=diagnostic,cases_requested=[case['id'] for case in cases],
        runtime_files_sha256=protected,observer_sha256=protected[OBSERVER],cases={},failures={},
        native_admission_qualified=False,phase6_complete=False)
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        def observe(case):
            paths=[];runs=[]
            for repeat in (1,2):
                out=a.output/(case['id']+'-'+str(repeat));paths.append(out)
                def configure(directory):
                    path=directory/'Orbiter.cfg';text=path.read_text()
                    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                        require(text.count(line)==1,'Original fixture propagator override differs');text=text.replace(line,'')
                    path.write_text(text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    scenario=shared.entry_point(directory,case);scenario.parent.mkdir(parents=True,exist_ok=True)
                    scenario.write_bytes((ROOT/case['scenario_entry_point']).read_bytes())
                    for kind in set(case['declared_vessels'].values()):
                        item=config['classes'][kind]
                        require(sha_lf(directory/item['target'])==item['sha256_lf'],'Original staged class configuration differs')
                    (directory/'reference-variant.json').write_text(json.dumps(variant,indent=2)+'\n')
                    if config['protocol']==protocols.V2:
                        (directory/protocols.MARKER).write_bytes(protocols.marker_bytes(config))
                    (directory/'ogl-evidence.enabled').touch();mesa_files(a.mesa,directory)
                stage(a.executable,a.data,a.planets,out,config,case,configure,process_timeout=900)
                staged_data=data_inputs.inspect(out,out)
                require(staged_data==original_data,'Actual staged scene data differs from original source inputs')
                (out/'actual-data-inputs.json').write_text(json.dumps(staged_data,indent=2)+'\n')
                require(all(sha(out/name)==value for name,value in protected.items()
                            if name.lower().endswith(('.dll','.exe'))),'Executed runtime module bytes differ')
                result=inspect_artifacts(out,case,config)
                result['loaded_modules']=shared.shared.loaded_modules(out,expected)
                loaded={Path(item['path'].replace('\\','/')).name.casefold() for item in result['loaded_modules']}
                required={'orbiter.exe','oglclient.dll','productioncockpitdriver.dll'}
                required|={Path(config['classes'][kind]['original_module']).name.casefold()
                           for kind in set(case['declared_vessels'].values()) if config['classes'][kind]['module']}
                require(required<=loaded,'Actual declared vessel factory/application/client/observer was not loaded')
                require(a.math_profile!='sse2' or result['actual_math']=='sse2','Actual CRT profile differs')
                runs.append(result);png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
            for name in (*shared.TRACES,'camera.csv'):
                require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Repaired repeat trace differs: '+name)
            score=image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
            require(score>=config['image_ssim_minimum'],'Repaired repeat full-frame budget failed')
            return dict(scenario=case['scenario'],runs=runs,repeat_ssim=score)
        def record(case,result,error):
            if error is None:
                report['cases'][case['id']]=result
                print(case['id'],case['scenario'],'captured twice',flush=True)
            else:
                report['failures'][case['id']]=str(error);print(case['id'],'failed:',error,flush=True)
            save()
        collect(cases,a.workers,observe,record)
        require(all(sha(root/name)==value for name,value in protected.items()),'Runtime variant changed during capture')
        require(raw_sources=={p.relative_to(ROOT).as_posix():sha(p) for p in source_files()},'Raw observer source changed during capture')
        require(data_inputs.inspect(a.data,a.planets)==original_data,'Original simulation data changed during capture')
        complete=len(report['cases'])==len(cases) and not report['failures']
        report.update(runtime_variant_unchanged=True,observer_sources_unchanged=True,actual_original_simulation_data_unchanged=True,
            status=('captured-diagnostic-only' if diagnostic else 'captured-awaiting-independent-audit') if complete else 'incomplete')
        require(complete,'Repaired complete-scene capture incomplete; no native admission')
    finally:save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-inputs',action='store_true')
    for name in ('executable','data','planets','mesa','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve())
    p.add_argument('--configuration',choices=('Debug','Release'));p.add_argument('--math-profile',choices=('automatic','sse2'))
    p.add_argument('--protocol',choices=protocols.NAMES,default=protocols.V1)
    p.add_argument('--workers',type=worker_count,default=1,help='Independent scene processes (1-4); each scene retains both serial repetitions')
    p.add_argument('--diagnostic-case',action='append',help='Run selected complete scenes with an explicit diagnostic-only marker; never eligible for full-reference acceptance')
    a=p.parse_args()
    if a.verify_inputs:
        config=settings(a.protocol);chosen=selected_cases(config,a.diagnostic_case)
        print('Verified all 38 unchanged scene inputs and unchanged budgets for',config['protocol'])
        if a.diagnostic_case is not None:print('Diagnostic-only complete-scene selection:',','.join(case['id'] for case in chosen))
        return
    require(all(getattr(a,name) is not None for name in ('executable','data','planets','mesa','output','configuration','math_profile')),
            'All repaired capture arguments required')
    capture(a)


if __name__=='__main__':main()
