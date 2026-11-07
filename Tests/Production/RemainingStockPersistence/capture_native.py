#!/usr/bin/env python3
"""Collect full native stock writers or exact-Windows-save reloads; qualify separately."""
import argparse
import concurrent.futures
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'RemainingStockRepaired'))
import capture as windows
import audit as original_audit
import protocols
import data_inputs
import configuration_input
from saved_inputs import derived_case,protocol
from saved_state import parse_saved,require

spec=importlib.util.spec_from_file_location('persistence_native_scene_reader',HERE.parent/'RemainingVessels/native.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
sha=native.sha;sha_lf=native.sha_lf
PHASES=('stock-writer','windows-save-reload')


def stage_asset_tree(source,target):
    """Retain asset file modes while permitting private configuration/evidence files."""
    shutil.copytree(source,target,copy_function=shutil.copy2)
    directories=[target,*(path for path in target.rglob('*') if path.is_dir())]
    for path in directories:
        path.chmod(stat.S_IMODE(path.stat().st_mode)|stat.S_IWUSR|stat.S_IXUSR)


def stage_scenario_input(source,target,phase):
    """Keep the copied stock input intact; write only a fresh derived save input."""
    require(phase in PHASES,'Unknown native persistence phase')
    if phase=='stock-writer':
        require(target.is_file() and target.read_bytes()==source.read_bytes(),
                'Copied original stock scenario differs or is missing')
    else:
        require(not target.exists() and not target.is_symlink(),
                'Derived Windows save input collides with staged assets')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
    require(sha(target)==sha(source),'Executed exact stock/Windows saved input differs')


def replay_bytes(contract):
    value=contract['native_save_command']
    require(value==dict(input_tick=959,phase='after',action='save',value=0,finalized_tick=960),
            'Native finalized Save boundary differs')
    preparation=contract['native_before_save_command']
    require(contract['native_save_boundary']=='windows-close-session-v2' and
            preparation==dict(input_tick=959,phase='after',action='endplayback',value=0,finalized_tick=960),
            'Native EndPlayback/Save ordering differs from Windows CloseSession')
    return ('tick,phase,action,value\n'+''.join(','.join(str(command[k]) for k in
            ('input_tick','phase','action','value'))+'\n' for command in (preparation,value))).encode('ascii')


def inspect_save_boundary(out,contract):
    """Require the real playback completion before Save at the original final tick."""
    replay_bytes(contract)
    with (out/'lifetime-events.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    names=('input.endplayback','input.save')
    inputs=[row for row in rows if row['phase'] in names]
    require([row['phase'] for row in inputs]==list(names),'Actual EndPlayback/Save input sequence differs')
    require(inputs[0]['detail'] in ('active','idle'),'Actual playback state witness differs')
    boundary=[row for row in rows if row['phase'] in (*names,'playback.ended') and
              row['frame']=='959' and row['tick']=='960']
    expected=['input.endplayback']+(['playback.ended'] if inputs[0]['detail']=='active' else [])+['input.save']
    require([row['phase'] for row in boundary]==expected and all(row in boundary for row in inputs),
            'Actual playback completion/Save boundary differs')
    require(all(math.isfinite(float(row[k])) for row in boundary for k in ('seconds','mjd')) and
            len({(row['seconds'],row['mjd']) for row in boundary})==1,
            'Actual EndPlayback/Save clocks differ')
    return dict(boundary=contract['native_save_boundary'],input_tick=959,finalized_tick=960,
                playback_was_active=inputs[0]['detail']=='active',events=expected)



def inspect_save(out,contract):
    """Check the actual command and complete saved output, without inferring tolerances."""
    invocation=json.loads((out/'invocation.json').read_text());args=invocation['argv']
    require(args.count('--replay')==args.count('--save')==1 and
            args[args.index('--replay')+1]==str(out/'persistence-replay.csv') and
            args[args.index('--save')+1]==str(out/'saved.scn') and
            (out/'persistence-replay.csv').read_bytes()==replay_bytes(contract) and
            invocation['save_replay_sha256']==sha(out/'persistence-replay.csv'),
            'Executed real Save command/path/hash differs')
    require(invocation['sanitizer_environment']==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
            LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),
            'Unsuppressed native sanitizer invocation differs')
    require((out/'stock-vessel-complete.txt').read_text().strip()==str(contract['frames']),
            'Native saved-state observation did not reach the finalized boundary')
    configuration_input.inspect(out,configuration_input.expected(ROOT,invocation['collector_producer_commit'],'native'))
    inspect_save_boundary(out,contract)
    return parse_saved(out/'saved.scn')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','build-record','assets','data','planets','compositor-tools','gtk-plugin','gtk-build-record','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    for name in ('windows-parent-capture','windows-build','preserved'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve())
    p.add_argument('--library',type=lambda v:Path(v).resolve(),action='append',default=[])
    p.add_argument('--phase',choices=PHASES,required=True)
    p.add_argument('--runtime-owner',type=lambda v:Path(v).resolve(),default=ROOT,
                   help='Immutable checkout owning the compiled package; collector identity remains separate')
    p.add_argument('--observer-delay-ms',type=int,choices=(0,120),default=120,
                   help='Explicit observer wall pacing; zero requires equivalence qualification before broad use')
    p.add_argument('--case',action='append');p.add_argument('--jobs',type=int,default=1)
    a=p.parse_args();contract=protocol();config=native.settings(protocols.V2)
    require(sys.platform=='linux' and not a.output.exists() and a.jobs>0,'Native Linux, fresh output and positive concurrency required')
    cases=windows.selected_cases(config,a.case);diagnostic=a.case is not None
    record=json.loads(a.build_record.read_text());require(record['status']=='built','Complete immutable native package required')
    identity=native.build_identity(a.build/'orbiter-production',a.build/'NativeModules',a.build_record,record['source_base'],a.runtime_owner)
    require(identity['sanitizer_linked'],'Persistence candidate requires actual ASan/UBSan linkage')
    candidate=a.build/'production_remaining_stock_diagnostic'
    require(record['candidate_runtime_files_sha256'][candidate.relative_to(a.runtime_owner).as_posix()]==sha(candidate),
            'Actual native diagnostic host differs from immutable package')
    guarded={str(a.runtime_owner/n):sha(a.runtime_owner/n) for n in {**record['source_sha256_lf'],**record['dependency_sha256_lf']}}
    for name,value in {**record['source_sha256_lf'],**record['dependency_sha256_lf']}.items():
        require(sha_lf(a.runtime_owner/name)==value,'Current owning source/dependency differs from native package: '+name)
        body=subprocess.check_output(['git','-C',str(a.runtime_owner),'show',record['source_base']+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value,'Native package dependency differs from immutable producer: '+name)
    guarded.update({str(a.runtime_owner/n):v for n,v in {**record['generated_source_files_sha256'],**record['runtime_files_sha256'],
        **record['candidate_runtime_files_sha256']}.items()})
    guarded[str(a.build_record)]=sha(a.build_record)
    gtk=json.loads(a.gtk_build_record.read_text())
    require(gtk['status']=='built' and gtk['baseline'] is False and gtk['sanitizers'] is True and
            gtk['plugin_sha256']==sha(a.gtk_plugin),'Pinned sanitizer-instrumented GTK owner differs')
    for path in (a.gtk_plugin,a.gtk_build_record,a.assets/'remaining-vessels-resources.json'):guarded[str(path)]=sha(path)
    libraries=[directory/name for directory in a.library for name in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0')
               if (directory/name).exists()]
    require({p.name for p in libraries}=={'libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0'},'Actual native lifetime libraries incomplete')
    for path in libraries:guarded[str(path)]=sha(path)
    assets=json.loads((a.assets/'remaining-vessels-resources.json').read_text())['staged_files_sha256']
    require(all(sha(a.assets/n)==v for n,v in assets.items()),'Complete native asset inputs changed')
    chosen={n.casefold():n for n in assets};require(len(chosen)==len(assets),'Ambiguous native asset paths')
    original_data=data_inputs.inspect(a.data,a.planets)
    parent=None;parent_runtime=None
    if a.phase=='windows-save-reload':
        require(all((a.windows_parent_capture,a.windows_build,a.preserved)),'Exact Windows reload requires parent observations, source/runtime build and preserved original package')
        parent_file=a.windows_parent_capture/'capture.json';parent=json.loads(parent_file.read_text())
        guarded[str(parent_file)]=sha(parent_file)
        require(parent['protocol']==protocols.V2 and parent['status'] in ('captured-diagnostic-only','captured-awaiting-independent-audit') and
                not parent['failures'] and parent['configuration']==identity['configuration'] and parent['math_profile']==identity['math_profile'] and
                {c['id'] for c in cases}<=set(parent['cases']) and parent['actual_original_simulation_data']==original_data,
                'Completed same-profile, same-data original Windows parent observations required')
        if not diagnostic:require(not parent['diagnostic_only'] and len(parent['cases'])==38,'Complete reload requires all 38 original Windows parent scenes')
        win_build,parent_runtime=original_audit.runtime_variant(a.windows_build,parent['producer_commit'],identity['configuration'],a.preserved,protocols.V2)
        source_protocol=json.loads((a.windows_build/'module-sources/source-variant.json').read_text())['protocol']
        require(source_protocol=='remaining-stock-repaired-sources-v4' or (diagnostic and source_protocol=='remaining-stock-repaired-sources-v3'),
                'Complete reload requires Windows gauge-storage repair v4; historical v3 is diagnostic-only')
        guarded[str(a.windows_build/'build.json')]=sha(a.windows_build/'build.json')
        for directory in (a.windows_build,a.preserved):
            guarded.update({str(path):sha(path) for path in directory.rglob('*') if path.is_file()})
        # Freeze every selected actual parent observation and exact derived input before launching native code.
        derived={}
        for case in cases:
            require(len(parent['cases'][case['id']]['runs'])==2,'Both actual Windows repetitions required')
            for repeat in (1,2):
                directory=a.windows_parent_capture/(case['id']+'-'+str(repeat));result=parent['cases'][case['id']]['runs'][repeat-1]
                for name,value in result['files_sha256'].items():
                    require(sha(directory/name)==value,'Actual original parent observation changed');guarded[str(directory/name)]=value
                checked=windows.inspect_artifacts(directory,case,config)
                if not diagnostic:require('configuration_input' in checked,'Complete native reload requires an actual Windows startup configuration witness')
                source=directory/'Scenarios/(Current state).scn';checksum=sha(source)
                saved_case,provenance=derived_case(case,config,source,checksum);guarded[str(source)]=checksum
                provenance.update(parent_capture_sha256=sha(parent_file),parent_run=case['id']+'-'+str(repeat),
                    parent_finalized_clock=checked['matched_clock_observation'],parent_producer_commit=parent['producer_commit'],
                    parent_startup_configuration=checked.get('configuration_input'),parent_source_variant_protocol=source_protocol)
                derived[(case['id'],repeat)]=(saved_case,source,provenance)
    else:
        require(not any((a.windows_parent_capture,a.windows_build,a.preserved)),'Stock-writer phase retains unchanged stock inputs; select windows-save-reload to supply Windows saves')
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    paths=set(windows.source_files())|{x for x in HERE.iterdir() if x.is_file()}|{x for x in native.HERE.iterdir() if x.is_file()}
    paths.update((Path(original_audit.__file__),HERE.parent/'StockScenarios/intentional_exit.py',HERE.parent/'WaylandInput/compositor.py',
                  HERE.parent/'NativeScene/Orbiter.cfg',Path(protocols.__file__),protocols.path(protocols.V2)))
    sources={path.relative_to(ROOT).as_posix():sha_lf(path) for path in paths}
    for name,value in sources.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value,'Native persistence collector differs from committed producer: '+name)
        guarded[str(ROOT/name)]=sha(ROOT/name)
    require(all(sha(Path(n))==v for n,v in guarded.items()),'Owning native/Windows inputs differ before collection')
    a.output.mkdir(parents=True);probe=a.output/'remaining-vessels-probe.so'
    command=[identity['compiler'],'-std=c++17','-fPIC','-shared','-Wl,--no-undefined','-fsanitize=address,undefined','-fno-omit-frame-pointer',
        '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),'-I'+str(a.build/'native-sdk'),str(native.HERE/'NativeProbe.cpp'),
        '-L'+str(a.build),'-Wl,-rpath,'+str(a.build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)]
    if a.observer_delay_ms==0:command.insert(1,'-DORBITER_NATIVE_FAST_CAPABILITY_DIAGNOSTIC')
    (a.output/'probe-command.json').write_text(json.dumps(command,indent=2)+'\n')
    with (a.output/'probe-build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    guarded[str(probe)]=sha(probe)
    generated=list(a.build.glob('native-dragonfly-*'));require(len(generated)==1,'Actual generated Dragonfly source directory missing or ambiguous')
    controls_path=a.output/'native-source-controls.json'
    with (a.output/'native-source-controls.log').open('w') as log:
        subprocess.run([sys.executable,'-B',str(HERE.parent/'Dragonfly/NativeSource.Test.py'),'--generated',str(generated[0]),
            '--output',str(controls_path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    controls=json.loads(controls_path.read_text())
    require(controls['status']=='passed' and len(controls['controls'])==15 and controls['original_and_generated_files_unchanged'],
            'Actual native generated-source mutation controls incomplete')
    guarded[str(controls_path)]=sha(controls_path)
    report=dict(status='running',protocol=contract['protocol'],phase=a.phase,host='native-linux',producer_commit=producer,
        runtime_owner=str(a.runtime_owner),observer_delay_ms=a.observer_delay_ms,
        runtime_source_commit=record['source_base'],runtime_identity=identity,source_sha256_lf=sources,guarded_files_sha256=guarded,
        asset_files_sha256=assets,actual_original_data=original_data,independently_checked_windows_runtime=parent_runtime,
        windows_parent_producer=parent['producer_commit'] if parent else None,diagnostic_only=diagnostic,cases_requested=[c['id'] for c in cases],
        repeats=2,frames=960,cases={},failures={},native_admission_qualified=False,phase6_complete=False)
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def run_case(parent_case,display):
        runs=[];folders=[]
        try:
            for repeat in (1,2):
                if parent:
                    case,source,provenance=derived[(parent_case['id'],repeat)]
                else:
                    case=parent_case;source=ROOT/case['scenario_entry_point']
                    provenance=dict(protocol=contract['protocol'],phase=a.phase,original_parent_case=case,stock_input_sha256=sha(source),
                        original_scenarios_and_scripts_unchanged=True,native_admission_qualified=False,phase6_complete=False)
                out=a.output/(case['id']+'-'+str(repeat));folders.append(out)
                stage_asset_tree(a.assets,out)
                target=out/case['scenario_entry_point']
                stage_scenario_input(source,target,a.phase)
                cfg=(HERE.parent/'NativeScene/Orbiter.cfg').read_text()
                for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                    require(cfg.count(line)==1,'Native propagator fixture differs');cfg=cfg.replace(line,'')
                path=out/'Orbiter.cfg';path.unlink(missing_ok=True)
                path.write_text(cfg+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n')
                startup_configuration=configuration_input.stage(out)
                (out/protocols.MARKER).write_bytes(protocols.marker_bytes(config));(out/'persistence-replay.csv').write_bytes(replay_bytes(contract))
                (out/'persistence-input.json').write_text(json.dumps(provenance,indent=2)+'\n')
                argv=[str(candidate),'--assets',str(out),'--data',str(a.data),'--planets',str(a.planets),'--modules',str(a.build/'NativeModules'),
                    '--scenario',str(target),'--config',str(path),'--evidence',str(out),'--save',str(out/'saved.scn'),
                    '--frames','960','--fixed-step',str(config['fixed_step']),'--fixed-system-step',str(config['system_elapsed_input']),
                    '--replay',str(out/'persistence-replay.csv'),'--run']
                env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                    LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[a.build,*a.library])))
                for key in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(key,None)
                asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()
                env.update(LD_PRELOAD=asan+':'+str(probe),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                invocation=dict(argv=argv,protocol=protocols.V2,persistence_phase=a.phase,collector_producer_commit=producer,
                    configuration_input=startup_configuration,scenario_entry_point=case['scenario_entry_point'],
                    scenario_sha256_lf=sha_lf(target),class_inputs={kind:dict(path=chosen[config['classes'][kind]['target'].casefold()],sha256_lf=config['classes'][kind]['sha256_lf']) for kind in set(case['declared_vessels'].values())},
                    recording_files_sha256={n:sha(out/n) for n in native.shared.recordings(case,config)},finalized_frame_descriptor_sha256=sha(out/protocols.MARKER),
                    save_replay_sha256=sha(out/'persistence-replay.csv'),sanitizer_environment={k:env[k] for k in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS')})
                (out/'invocation.json').write_text(json.dumps(invocation,indent=2)+'\n')
                with (out/'console.log').open('w') as log:process=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
                (out/'process-result.json').write_text(json.dumps(dict(returncode=process.returncode))+'\n')
                require(all(sha(out/n)==v for n,v in assets.items() if n!='Orbiter.cfg'),'An original native scene/script/recording/configuration/mesh/texture changed')
                if (out/'scene.rgba').is_file() and (out/'scene.rgba').stat().st_size==1280*720*4:native.png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
                result=native.inspect(out,case,config,identity,a.build,probe,libraries,a.gtk_plugin)
                result.update(saved_state=inspect_save(out,contract),persistence_input=provenance,executed_case=case)
                if parent_case['id']==cases[0]['id'] and repeat==1:
                    control_file=a.output/'configuration-input-controls.json'
                    with (a.output/'configuration-input-controls.log').open('w') as log:
                        subprocess.run([sys.executable,'-B',str(HERE.parent/'RemainingStockRepaired/ConfigurationInput.Test.py'),
                            '--capture',str(out),'--kind','native','--output',str(control_file)],stdout=log,stderr=subprocess.STDOUT,check=True)
                    result['configuration_input_control_sha256']=sha(control_file)
                runs.append(result)
            for name in (*native.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
                require((folders[0]/name).read_bytes()==(folders[1]/name).read_bytes(),'Native repeated persistence trace differs: '+name)
            from saved_state import content_differences
            require(not content_differences(runs[0]['saved_state'],runs[1]['saved_state']),'Native repeated complete saved content differs')
            similarity=native.shared.image_ssim((folders[0]/'scene.rgba').read_bytes(),(folders[1]/'scene.rgba').read_bytes(),1280,720)
            require(similarity>=config['image_ssim_minimum'],'Native repeated persistence image exceeds unchanged budget')
            return parent_case['id'],dict(runs=runs,repeat_ssim=similarity),None
        except Exception as error:return parent_case['id'],None,str(error)
    try:
        with native.Compositor(a.compositor_tools,a.output/'compositor') as display:
            with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
                futures=[pool.submit(run_case,case,display) for case in cases]
                for future in concurrent.futures.as_completed(futures):
                    name,result,error=future.result()
                    if error:report['failures'][name]=error
                    else:report['cases'][name]=result
                    save();print(json.dumps(dict(case=name,phase=a.phase,status='failed' if error else 'captured',reason=error)),flush=True)
        require(all(sha(Path(n))==v for n,v in guarded.items()),'Owning sources/runtime/probe/Windows observations changed')
        require(all(sha(a.assets/n)==v for n,v in assets.items()),'Retained native asset inputs changed')
        require(data_inputs.inspect(a.data,a.planets)==original_data,'Actual original simulation data changed')
        complete=len(report['cases'])==len(cases) and not report['failures']
        if complete:
            control_file=a.output/'configuration-input-controls.json';checked=json.loads(control_file.read_text())
            require(checked['status']=='passed' and checked['kind']=='native' and checked['producer_commit']==producer and
                    checked['line_ending_reader_positives']==2 and checked['owning_capture_unchanged'] and
                    len(checked['controls'])==9+int(checked['runtime_configuration_was_rewritten']) and
                    sha(control_file)==report['cases'][cases[0]['id']]['runs'][0]['configuration_input_control_sha256'],
                    'Actual native startup-configuration controls missing or changed')
            guarded[str(control_file)]=sha(control_file)
        report.update(status=('captured-diagnostic-only' if diagnostic else 'captured-awaiting-independent-persistence-audit') if complete else 'incomplete',
            owning_sources_runtime_probe_windows_inputs_assets_and_data_unchanged=True,
            scope='One explicit phase of all-scene native persistence collection. Both stock writers and exact-Windows-save reloads in all four profiles, independent Windows/native physical/camera/frame and complete save comparisons, original serialization round trips, controls, lifetime and Phase 6 acceptance remain required.')
        save();require(complete,'Native persistence failures retained; no admission')
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
