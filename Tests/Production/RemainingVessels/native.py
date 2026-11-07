#!/usr/bin/env python3
"""Capture complete unchanged remaining-stock scenes with original native modules; qualify separately."""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('remaining_native_reader',HERE.parent/'RemainingStock/original.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
sys.path[:0]=[str(HERE.parent/'StockScenarios'),str(HERE.parent/'WaylandInput')]
sys.path.insert(0,str(HERE.parent/'RemainingStockRepaired'))
import protocols
from intentional_exit import build_identity
from compositor import Compositor
from run_client import png
require=shared.require;sha=shared.digest;sha_lf=shared.sha_lf


def settings(protocol=protocols.V1):
    return protocols.load(shared.settings(),protocol)


def inspect_inputs(out,case,config):
    invocation=json.loads((out/'invocation.json').read_text())
    args=invocation['argv'];entry=case['scenario_entry_point']
    require(invocation['scenario_entry_point']==entry and args[args.index('--scenario')+1]==str(out/entry) and
            args[args.index('--assets')+1]==str(out),'Actual complete native scenario/asset root differs')
    require(sha_lf(out/entry)==case['sha256_lf']==invocation['scenario_sha256_lf'],'Original native scenario bytes differ')
    if config['protocol']==protocols.V2:
        require(args.count('--fixed-system-step')==1 and args[args.index('--fixed-system-step')+1]==str(config['system_elapsed_input']) and
                '--capture-time' not in args and args.count('--fixed-step')==1 and
                args[args.index('--fixed-step')+1]==str(config['fixed_step']) and
                args.count('--frames')==1 and args[args.index('--frames')+1]==str(config['frames']) and
                invocation['protocol']==protocols.V2 and
                (out/protocols.MARKER).read_bytes()==protocols.marker_bytes(config) and
                invocation['finalized_frame_descriptor_sha256']==sha(out/protocols.MARKER),
                'Executed matched-clock arguments or finalized-frame descriptor differ')
    for name,value in invocation['class_inputs'].items():
        require(name in case['declared_vessels'].values() and sha_lf(out/value['path'])==value['sha256_lf']==config['classes'][name]['sha256_lf'],
                'Actual native class input differs: '+name)
    require(set(invocation['class_inputs'])==set(case['declared_vessels'].values()),'Declared native class input closure incomplete')
    expected=shared.recordings(case,config)
    for name,value in expected.items():
        require(sha_lf(out/name)==value and sha(out/name)==invocation['recording_files_sha256'][name],
                'Actual original native playback input differs: '+name)
    for repair in config['delivery_repairs']:
        require(sha_lf(out/repair['target'])==repair['sha256_lf'],'Original installed native mesh differs')
    return len(expected)


# This private reader instance retains the complete unchanged trace/resource
# validator and binds its input check to actual native CLI and installation paths.
shared.inspect_inputs=inspect_inputs


def inspect(out,case,config,identity,build,probe,libraries,gtk_plugin,instrument_control=False):
    require(json.loads((out/'process-result.json').read_text())['returncode']==0,'Native process did not return zero')
    require((out/'stock-vessel-complete.txt').read_text().strip()==str(config['frames']),'Native observation ended early')
    result=shared.inspect_trace(out,case,config)
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=config['frames'],successful_presents=config['frames'],context_deleted=True),
            'Native actual presentations/context teardown incomplete')
    marker=json.loads((out/'unqualified-remaining-stock-diagnostic.json').read_text())
    require(marker['native_admission_qualified'] is False and marker['phase6_complete'] is False,'Diagnostic marker differs')
    text=(out/'console.log').read_text(errors='replace')
    require(not any(value in text for value in ('Lua error:','LuaCall (','Orbiter native production:','Production teardown:',
        'runtime error:','ERROR: AddressSanitizer','ERROR: LeakSanitizer','AddressSanitizer:DEADLYSIGNAL',
        'LeakSanitizer has encountered','Could not find a module')),'Native runtime/sanitizer diagnostic')
    errors=out/'graphics-errors.txt';require(not errors.exists() or not errors.read_text().strip(),'Native OpenGL diagnostic')
    cfg=(out/'Orbiter.cfg').read_text()
    require(not re.search(r'^\s*(?:PropStages|PropStage\d+|PropSubsampling)\s*=',cfg,re.I|re.M),'Native original propagator defaults overridden')
    summary=json.loads((out/'scene-summary.json').read_text())
    protocols.inspect_frame(summary,config,result.get('matched_clock_observation'))
    scene=shared.rows(out/'scene.csv');tick=str(config['capture_tick'])
    expected={(r['object'],r['index']) for r in shared.rows(out/'stock-vessel-meshes.csv') if r['tick']==tick and r['present']=='1'}
    actual=[(r['object'],r['index']) for r in scene if r['type']=='vessel']
    require(set(actual)==expected and len(actual)==len(expected),'Native renderer omits or substitutes a physical mesh')
    classes={r['object']:r['class'] for r in shared.rows(out/'stock-vessel-state.csv') if r['tick']==tick}
    require(all(r['class'].lower()==classes[r['object']].lower() for r in scene if r['type']=='vessel'),'Native rendered object class differs')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Native renderer/viewport differs')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Native framebuffer incomplete')
    mapped=(out/'observer-loaded-maps.txt').read_text()
    required=[build/'liborbiter_production_boundary.so',build/'liborbiter_production_vessels.so',
              build/'production_remaining_stock_diagnostic',probe,*libraries,gtk_plugin]
    for kind in set(case['declared_vessels'].values()):
        module=config['classes'][kind]['module']
        if module:required.append(build/'NativeModules/Vessel'/(module+'.so'))
    require(all(str(path) in mapped for path in required),'Actual required native application/module/probe/library was not mapped')
    require(not any('/usr/lib/' in line and '/libdecor-gtk.so' in line for line in mapped.splitlines()),'Unpinned GTK decoration plugin mapped')
    actual_math=json.loads((out/'numerics.json').read_text())['math']
    require(actual_math=='amd-6121d02-'+('sse2' if identity['math_profile']=='sse2' else 'fma3'),'Actual native CPU math differs')
    control=None
    if instrument_control:
        control=json.loads((out/'native-instrument-control.json').read_text())
        require(control==dict(status='passed',contexts=3,context_restorations=7,display_lists=2,pixel_uploads=1,
                checked_pixels=25781,texture_name_1_collision_reproduced=True,
                legacy_blt_copies=1,obsolete_blt_color_key_ignored=True,
                native_admission_qualified=False,phase6_complete=False),'Actual native compatibility-target control incomplete')
    files={p.relative_to(out).as_posix():sha(p) for p in out.iterdir() if p.is_file()}
    result=dict(result,status='captured',lifecycle=life,renderer=renderer,actual_math=actual_math,files_sha256=files,
                input_sha256=sha(out/'invocation.json'))
    if instrument_control:result['instrument_control']=control
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','build-record','assets','data','planets','compositor-tools','gtk-plugin','gtk-build-record','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--library',type=lambda v:Path(v).resolve(),action='append',default=[])
    p.add_argument('--case',action='append');p.add_argument('--repeats',type=int,choices=(1,2),default=2)
    p.add_argument('--instrument-control',action='store_true',help='Exercise real native compatibility contexts and surface uploads in the complete unchanged scene')
    p.add_argument('--jobs',type=int,default=1)
    p.add_argument('--protocol',choices=protocols.NAMES,default=protocols.V1)
    p.add_argument('--owner',type=lambda v:Path(v).resolve(),default=ROOT,
                   help='Immutable package owner for the separate repeated-lifetime diagnostic')
    p.add_argument('--lifetime-sessions',type=int,choices=(20,),
                   help='Run twenty bounded whole-world lifetimes; cannot satisfy stock parity')
    p.add_argument('--capability-control',action='store_true',
                   help='Compare short actual SDK capability snapshots and observer-off/on controls; diagnostic only')
    p.add_argument('--rejection-control',action='store_true',
                   help='Exercise actual loader and class-policy failures before presentation; diagnostic only')
    p.add_argument('--interaction-plan',type=lambda v:Path(v).resolve(),
                   help='Run an explicit original-input interaction plan; diagnostic only')
    p.add_argument('--rejection-windows-dll',type=lambda v:Path(v).resolve(),
                   help='Preserved original Windows HST DLL for the foreign-format rejection')
    p.add_argument('--windows-reference',type=lambda v:Path(v).resolve(),
                   help='Matching retained original-Windows stock capture for capability diagnostics')
    p.add_argument('--windows-build',type=lambda v:Path(v).resolve())
    p.add_argument('--preserved',type=lambda v:Path(v).resolve())
    a=p.parse_args()
    if a.interaction_plan:
        require(not a.capability_control and not a.lifetime_sessions and not a.rejection_control,
                'Separate interaction scope required')
        from interactions import capture
        capture(a)
        return
    if a.rejection_control:
        require(not a.capability_control and not a.lifetime_sessions and a.rejection_windows_dll,
                'Separate rejection controls and preserved Windows DLL required')
        from rejections import capture
        capture(a)
        return
    if a.capability_control:
        require(not a.lifetime_sessions and all((a.windows_reference,a.windows_build,a.preserved)),
                'Separate capability control and its original-Windows references required')
        from capabilities import capture
        capture(a)
        return
    if a.lifetime_sessions:
        from lifetimes import capture
        capture(a)
        return
    require(a.owner==ROOT,'Separate package owner is supported only for lifetime diagnostics')
    config=settings(a.protocol);require(not a.output.exists() and a.jobs>0,'Fresh diagnostic output and positive concurrency required')
    cases=[case for case in config['cases'] if not a.case or case['id'] in a.case]
    require(cases and (not a.case or {c['id'] for c in cases}==set(a.case)),'Unknown native complete-scene case')
    record=json.loads(a.build_record.read_text());require(record['status']=='built','Complete immutable build required')
    require(record.get('generated_source_files_sha256'),'Actual generated module source closure missing')
    candidate=a.build/'production_remaining_stock_diagnostic'
    require(record['candidate_runtime_files_sha256'][candidate.relative_to(ROOT).as_posix()]==sha(candidate),'Actual diagnostic host differs')
    identity=build_identity(a.build/'orbiter-production',a.build/'NativeModules',a.build_record,record['source_base'])
    for name,value in record['dependency_sha256_lf'].items():
        require(sha_lf(ROOT/name)==value,'Retained build dependency input changed: '+name)
    gtk=json.loads(a.gtk_build_record.read_text())
    require(gtk['status']=='built' and gtk['baseline'] is False and gtk['plugin_sha256']==sha(a.gtk_plugin) and
            gtk['sanitizers']==identity['sanitizer_linked'],'Actual source-pinned GTK owner candidate differs')
    guarded={str(ROOT/name):sha(ROOT/name) for name in {**record['source_sha256_lf'],**record['dependency_sha256_lf']}}
    guarded.update({str(ROOT/name):value for name,value in record['generated_source_files_sha256'].items()})
    guarded.update({str(ROOT/name):value for name,value in {**record['runtime_files_sha256'],**record['candidate_runtime_files_sha256']}.items()})
    guarded[str(a.build_record)]=sha(a.build_record);guarded[str(a.gtk_plugin)]=sha(a.gtk_plugin)
    guarded[str(a.gtk_build_record)]=sha(a.gtk_build_record)
    guarded[str(a.assets/'remaining-vessels-resources.json')]=sha(a.assets/'remaining-vessels-resources.json')
    require(all(sha(Path(name))==value for name,value in guarded.items()),'Native source/runtime changed before capture')
    assets=json.loads((a.assets/'remaining-vessels-resources.json').read_text())['staged_files_sha256']
    require(assets=={name:sha(a.assets/name) for name in assets},'Full immutable native resource tree changed')
    chosen={name.casefold():name for name in assets};require(len(chosen)==len(assets),'Ambiguous native asset paths')
    paths={p for p in HERE.iterdir() if p.is_file()}
    paths.update(shared.source_files());paths.update((Path(protocols.__file__),protocols.path(protocols.V1),protocols.path(protocols.V2)))
    paths.update(HERE.parent/name for name in ('StockScenarios/intentional_exit.py','WaylandInput/compositor.py'))
    if a.instrument_control:paths.add(HERE.parent/'NativeInstrumentTarget/Control.h')
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    sources={p.relative_to(ROOT).as_posix():sha_lf(p) for p in paths}
    for name,value in sources.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value,'Native observer differs from immutable producer: '+name)
        guarded[str(ROOT/name)]=sha(ROOT/name)
    a.output.mkdir(parents=True)
    probe=a.output/'remaining-vessels-probe.so'
    command=[identity['compiler'],'-std=c++17','-fPIC','-shared','-Wl,--no-undefined']
    if identity['sanitizer_linked']:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    if a.instrument_control:command+=['-DORBITER_NATIVE_INSTRUMENT_CONTROL']
    command+=['-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),'-I'+str(a.build/'native-sdk'),
        str(HERE/'NativeProbe.cpp'),'-L'+str(a.build),'-Wl,-rpath,'+str(a.build),
        '-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)]
    if a.instrument_control:command.insert(-2,'-lGL')
    (a.output/'probe-command.json').write_text(json.dumps(command,indent=2)+'\n')
    with (a.output/'probe-build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    guarded[str(probe)]=sha(probe)
    report=dict(status='running',protocol=config['protocol'],host='native-linux-diagnostic',producer_commit=producer,
        runtime_source_commit=record['source_base'],runtime_identity=identity,build_record_sha256=sha(a.build_record),
        source_sha256_lf=sources,guarded_files_sha256=guarded,asset_files_sha256=assets,
        cases_requested=[c['id'] for c in cases],repeats=a.repeats,frames=config['frames'],fixed_step=config['fixed_step'],
        instrument_control=a.instrument_control,
        native_admission_qualified=False,phase6_complete=False,cases={},failures={})
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def run_case(case,display):
        runs=[];folders=[]
        try:
            for repeat in range(1,a.repeats+1):
                out=a.output/(case['id']+'-'+str(repeat));folders.append(out)
                shutil.copytree(a.assets,out,copy_function=shutil.copy2)
                require((out/case['scenario_entry_point']).read_bytes()==(ROOT/case['scenario_entry_point']).read_bytes(),'Complete native stock scene changed')
                cfg=(HERE.parent/'NativeScene/Orbiter.cfg').read_text()
                for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                    require(cfg.count(line)==1,'Native fixture propagator line differs');cfg=cfg.replace(line,'')
                path=out/'Orbiter.cfg';path.unlink(missing_ok=True)
                path.write_text(cfg+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'
                    'VesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n')
                argv=[str(candidate),'--assets',str(out),'--data',str(a.data),'--planets',str(a.planets),
                    '--modules',str(a.build/'NativeModules'),'--scenario',str(out/case['scenario_entry_point']),
                    '--config',str(path),'--evidence',str(out),'--save',str(out/'saved.scn'),
                    '--frames',str(config['frames']),'--fixed-step',str(config['fixed_step']),'--run']
                if config['protocol']==protocols.V2:
                    argv+=['--fixed-system-step',str(config['system_elapsed_input'])]
                    (out/protocols.MARKER).write_bytes(protocols.marker_bytes(config))
                else:argv+=['--capture-time','12.5']
                invocation=dict(argv=argv,scenario_entry_point=case['scenario_entry_point'],scenario_sha256_lf=sha_lf(out/case['scenario_entry_point']),
                    class_inputs={kind:dict(path=chosen[config['classes'][kind]['target'].casefold()],sha256_lf=config['classes'][kind]['sha256_lf'])
                                  for kind in set(case['declared_vessels'].values())},
                    recording_files_sha256={name:sha(out/name) for name in shared.recordings(case,config)})
                if config['protocol']==protocols.V2:
                    invocation.update(protocol=config['protocol'],finalized_frame_descriptor_sha256=sha(out/protocols.MARKER))
                (out/'invocation.json').write_text(json.dumps(invocation,indent=2)+'\n')
                env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                    LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[a.build,*a.library])))
                for key in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(key,None)
                env['LD_PRELOAD']=str(probe)
                if identity['sanitizer_linked']:
                    asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()
                    env.update(LD_PRELOAD=asan+':'+str(probe),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                        LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                with (out/'console.log').open('w') as log:process=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
                (out/'process-result.json').write_text(json.dumps(dict(returncode=process.returncode))+'\n')
                require(all(sha(out/name)==value for name,value in assets.items() if name!='Orbiter.cfg'),
                        'An original native scene, script, playback, configuration, mesh or texture input changed')
                if (out/'scene.rgba').is_file() and (out/'scene.rgba').stat().st_size==1280*720*4:
                    png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
                libraries=[directory/name for directory in a.library for name in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0') if (directory/name).exists()]
                runs.append(inspect(out,case,config,identity,a.build,probe,libraries,a.gtk_plugin,a.instrument_control))
            if len(folders)==2:
                for name in (*shared.TRACES,'camera.csv'):
                    require((folders[0]/name).read_bytes()==(folders[1]/name).read_bytes(),'Native deterministic repeat differs: '+name)
                similarity=shared.image_ssim((folders[0]/'scene.rgba').read_bytes(),(folders[1]/'scene.rgba').read_bytes(),1280,720)
                require(similarity>=config['image_ssim_minimum'],'Native full-frame repeat exceeds unchanged budget')
            else:similarity=None
            return case['id'],dict(scenario=case['scenario'],runs=runs,repeat_ssim=similarity),None
        except Exception as error:return case['id'],None,str(error)
    with Compositor(a.compositor_tools,a.output/'compositor') as display:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
            futures=[pool.submit(run_case,case,display) for case in cases]
            for future in concurrent.futures.as_completed(futures):
                name,result,error=future.result()
                if error:report['failures'][name]=error
                else:report['cases'][name]=result
                save();print(json.dumps(dict(case=name,status='failed' if error else 'captured',reason=error)),flush=True)
    require(guarded=={name:sha(Path(name)) for name in guarded},'Source/runtime/probe changed during native capture')
    require(assets=={name:sha(a.assets/name) for name in assets},'Retained native asset tree changed during capture')
    report.update(status='completed-with-failures' if report['failures'] else 'captured-awaiting-original-comparison',
        source_runtime_probe_and_assets_unchanged=True,
        scope='Actual unchanged complete scenes and all vessels/resources/attachments/meshes. Case selections are diagnostics; '
              'all 38 scenes twice in every required profile, Windows/native comparisons, controls, persistence, '
              'lifetime and full production admission remain required.')
    save();require(not report['failures'],'Native diagnostic failures retained; no admission')


if __name__=='__main__':main()
