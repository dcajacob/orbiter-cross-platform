#!/usr/bin/env python3
"""Capture unchanged complete legacy station scenes with a retained native build."""
import argparse
from contextlib import nullcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('legacy_station_capture',HERE/'original.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
sys.path[:0]=[str(HERE.parent/'StockScenarios'),str(HERE.parent/'WaylandInput')]
from inventory import digest,require
from intentional_exit import build_identity
from compositor import Compositor
from recording_inputs import LOCK_FILE,entry_point,recordings,stage_recordings

PROTOCOL_SHARED=('Tests/Production/StockVessels/Observation.h','Tests/Production/StockVessels/original.py',
    'Tests/Production/StockVessels/verify_original.py','Tests/Production/StockScenarios/intentional_exit.py',
    'Tests/Production/StockScenarios/inventory.py','Tests/Production/NativeScene/Orbiter.cfg',
    'Tests/Production/WaylandInput/compositor.py','Tests/Production/Cockpit/stage.py',
    'Tests/Production/Cockpit/cases.json','Tests/Production/behavior_suite.py',
    'Tests/Production/Client/run_client.py','Tests/Production/Client/compare_client.py',
    'Tests/Production/mesa_runtime.py','Tests/Production/NativeLua/StockExit/contract.py',
    'Tests/Production/phase3-extraction.lock.json')


def sources():
    return [p for p in HERE.iterdir() if p.is_file()]+[ROOT/name for name in PROTOCOL_SHARED]


def inspect(out,case,config,identity,build,libraries):
    process=json.loads((out/'process-result.json').read_text())
    require(process['returncode']==0,'Native legacy scene did not return zero')
    result=legacy.inspect_trace(out,case,config)
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Native legacy graphics teardown incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Native legacy renderer or geometry differs')
    text=(out/'console.log').read_text(errors='replace')
    markers=('Lua error:','LuaCall (','Orbiter native production:','Production teardown:','runtime error:',
             'ERROR: AddressSanitizer','ERROR: LeakSanitizer','AddressSanitizer:DEADLYSIGNAL',
             'LeakSanitizer has encountered','Could not find a module')
    require(not any(marker in text for marker in markers),'Native legacy runtime or sanitizer error')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Native legacy OpenGL errors')
    declared=set(legacy.ships((ROOT/'Scenarios'/case['scenario']).read_text()))
    scene=legacy.rows(out/'scene.csv')
    require(declared<={row['object'] for row in scene if row['type']=='vessel'},'Native legacy complete mesh manifest missing')
    for name,kind in legacy.ships((ROOT/'Scenarios'/case['scenario']).read_text()).items():
        if kind.lower() in ('iss','module1'):
            meshes=[row for row in scene if row['type']=='vessel' and row['object']==name]
            require(len(meshes)==1 and meshes[0]['name'].lower()==kind.lower(),'Native legacy mesh identity differs')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Native legacy full framebuffer incomplete')
    actual_math=json.loads((out/'numerics.json').read_text())['math']
    if LOCK_FILE.exists():
        pins=json.loads(LOCK_FILE.read_text())
        require(actual_math=='amd-6121d02-'+pins['profiles'][identity['profile']]['actual_math'],'Native legacy actual CRT differs')
    else:
        require(actual_math=='amd-6121d02-'+('sse2' if identity['math_profile']=='sse2' else 'fma3'),'Native legacy actual CRT differs')
    loaded=(out/'renderer-modules.txt').read_text()
    for path in (build/'liborbiter_production_vessels.so',build/'liborbiter_production_boundary.so',
                 build/'NativeModules/Graphics/OGLClient.so',build/'NativeModules/Vessel/DeltaGlider.so',
                 build/'NativeModules/Vessel/ShuttleA.so'):
        require(str(path) in loaded,'Different native legacy module mapped: '+str(path))
    if identity['sanitizer_linked']:
        for path in libraries:require(str(path) in loaded,'Qualified private sanitizer library was not mapped: '+str(path))
    files={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file() and
           p.suffix in ('.csv','.txt','.log','.json','.scn','.rgba','.pos','.att','.atc','.dat')}
    return dict(result,status='captured',process_returncode=process['returncode'],actual_math=actual_math,
                renderer=renderer,lifecycle=life,files_sha256=files)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','build-record','assets','data','planets','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--runtime-source-commit',required=True)
    p.add_argument('--dependencies',type=lambda v:Path(v).resolve())
    p.add_argument('--backend',choices=('wayland','x11'),required=True)
    p.add_argument('--sanitize',action='store_true')
    p.add_argument('--library-directory',type=lambda v:Path(v).resolve(),action='append',default=[])
    p.add_argument('--case',action='append')
    a=p.parse_args();config=legacy.settings();require(not a.output.exists(),'Native legacy output replacement forbidden')
    require(not a.dependencies or a.backend=='wayland','Owned compositor requires Wayland')
    require(not a.case or set(a.case)<={case['id'] for case in config['cases']},'Unknown native legacy case')
    identity=build_identity(a.build/'orbiter-production',a.build/'NativeModules',a.build_record,a.runtime_source_commit)
    require(identity['sanitizer_linked']==a.sanitize,'Native legacy instrumentation is misidentified')
    require(not a.sanitize or len(a.library_directory)==3,'Instrumented legacy scenes require all three qualified private libraries')
    a.output.mkdir(parents=True)
    source_files=sources()
    source={str(path.relative_to(ROOT)):legacy.sha_lf(path) for path in source_files}
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,expected in source.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected,'Native legacy observer must match immutable producer: '+name)
    build_record=json.loads(a.build_record.read_text())
    owning=build_record.get('source_sha256_lf',build_record.get('source_sha256'))
    protected={str(ROOT/name):digest(ROOT/name) for name in owning}
    protected.update({str(ROOT/name):value for name,value in build_record['runtime_files_sha256'].items()})
    protected.update({str(path):digest(path) for path in [*source_files,a.build_record]})
    for name,expected in {**config['resources_sha256_lf'],**config['recording_files_sha256_lf']}.items():
        require(legacy.sha_lf(a.assets/name)==expected,'Staged native legacy resource differs: '+name)
        protected[str(a.assets/name)]=digest(a.assets/name)
    probe=a.output/'legacy-stations-probe.so'
    command=[identity['compiler'],'-std=c++17','-fPIC','-shared','-Wl,--no-undefined']
    if a.sanitize:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command+=['-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(HERE/'NativeProbe.cpp'),
              '-L'+str(a.build),'-Wl,-rpath,'+str(a.build),'-lorbiter_production_vessels',
              '-lorbiter_production_boundary','-ldl','-o',str(probe)]
    (a.output/'probe-command.json').write_text(json.dumps(command,indent=2)+'\n')
    with (a.output/'probe-build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    protected[str(probe)]=digest(probe)
    report=dict(status='running',phase6_complete=False,host='native-linux',producer_commit=producer,
        runtime_source_commit=a.runtime_source_commit,runtime_identity=identity,source_sha256_lf=source,
        build_record_path=str(a.build_record),protected_files_sha256=protected,probe_sha256=digest(probe),
        protocol=2,backend=a.backend,private_library_directories=list(map(str,a.library_directory)),cases={},attempts={},failures={})
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    display=Compositor(a.dependencies,a.output/'compositor') if a.dependencies else nullcontext(None)
    with display as compositor:
        environment=compositor.environment if compositor else os.environ
        for case in config['cases']:
            if a.case and case['id'] not in a.case:continue
            observed=[];paths=[];report['attempts'][case['id']]=[]
            try:
                for repeat in (1,2):
                    out=a.output/(case['id']+'-'+str(repeat));out.mkdir();paths.append(out)
                    original=(ROOT/'Scenarios'/case['scenario']).read_bytes()
                    require((a.assets/'Scenarios'/case['scenario']).read_bytes()==original,'Native legacy staged scenario differs')
                    scenario=entry_point(out,case);scenario.parent.mkdir(parents=True,exist_ok=True);scenario.write_bytes(original)
                    stage_recordings(a.assets,out,case,config)
                    (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (out/'replay.csv').write_text('tick,phase,action,value\n')
                    argv=[str(a.build/'orbiter-production'),'--assets',str(a.assets),'--data',str(a.data),
                        '--planets',str(a.planets),'--modules',str(a.build/'NativeModules'),
                        '--scenario',str(scenario),'--config',str(out/'Orbiter.cfg'),
                        '--evidence',str(out),'--save',str(out/'saved.scn'),'--replay',str(out/'replay.csv'),
                        '--frames','60','--fixed-step','.25','--capture-time','12.5','--run']
                    invocation=dict(argv=argv,scenario_entry_point=case['scenario_entry_point'],
                        input_sha256={name:digest(out/name) for name in [case['scenario_entry_point'],*recordings(case,config)]})
                    (out/'invocation.json').write_text(json.dumps(invocation,indent=2)+'\n')
                    env=dict(environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                             LD_LIBRARY_PATH=':'.join(map(str,[a.build,*a.library_directory])))
                    for key in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(key,None)
                    env['LD_PRELOAD']=str(probe)
                    if a.sanitize:
                        asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()
                        env.update(LD_PRELOAD=asan+':'+str(probe),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                                   LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    with (out/'console.log').open('w') as log:
                        process=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                    (out/'process-result.json').write_text(json.dumps(dict(returncode=process.returncode))+'\n')
                    report['attempts'][case['id']].append(dict(repeat=repeat,returncode=process.returncode,
                        console_sha256=digest(out/'console.log')));save()
                    require(process.returncode==0,'Native legacy process exit '+str(process.returncode))
                    recorded=inspect(out,case,config,identity,a.build,a.library_directory)
                    require(json.loads((out/'native-window.json').read_text())['backend']==a.backend,'Native legacy actual backend differs')
                    observed.append(recorded);legacy.png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
                for name in ('stock-vessel-state.csv','stock-vessel-docks.csv','stock-playback.csv','camera.csv'):
                    require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Native legacy repeat trace or camera differs')
                report['cases'][case['id']]=dict(scenario=case['scenario'],runs=observed)
                print(case['id'],'captured twice',flush=True)
            except Exception as error:
                report['failures'][case['id']]=str(error);print(case['id'],'failed:',error,flush=True)
            save()
    require(all(digest(Path(name))==value for name,value in protected.items()),'Native legacy source, resource or retained binary changed')
    report['sources_and_binaries_unchanged']=True
    report['status']='captured-awaiting-original-comparison' if len(report['cases'])==4 and not report['failures'] else 'incomplete'
    save();require(report['status']=='captured-awaiting-original-comparison','Native legacy capture incomplete; no parity qualification')


if __name__=='__main__':main()
