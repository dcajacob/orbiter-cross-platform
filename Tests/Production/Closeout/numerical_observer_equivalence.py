#!/usr/bin/env python3
"""Renew the missing native observer-equivalence witness, without changing old captures."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from contracts import ROOT,require,load,sha,atomic_json
from processes import OwnedProcess
from build_native_numerical_observers import COMPILED

PROFILE='Debug-automatic'
INPUT=ROOT/'Tests/Production/Closeout/NumericalRecovery/original-Windows-saved-input.scn'
INPUT_SHA='afc91115951ec44a81cffb6ffa34c00191f9b005aac3f14cf94b21de171b0538'
PRIMARY=('stock-vessel-state.csv','stock-vessel-docks.csv','stock-population.csv','stock-vessel-propellants.csv','stock-vessel-thrusters.csv','stock-vessel-attachments.csv','stock-playback.csv','stock-vessel-meshes.csv','stock-clock.csv','stock-step-clock.csv','camera.csv','scene.rgba','saved.scn','flight-state.csv')
SANITIZERS=dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
ORIGINAL=['Tests/Production/ReloadMath/'+n for n in ('capture_native.py','audit_native.py','NativeTouchdown.cpp','TouchdownObservation.h','InternalObservation.h','SurfaceObservation.h')]
ORIGINAL+=['Tests/Production/RemainingStockPersistence/'+n for n in ('capture_native.py','observations.py','saved_inputs.py','saved_state.py','protocol.json')]
ORIGINAL+=['Tests/Production/RemainingVessels/'+n for n in ('native.py','NativeProbe.cpp')]


def source_identity():
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();guards={}
    from hosted_native_general_api import source_identity as core_identity
    core=core_identity()
    require(core['collector_source']==source and core['actual_core_sources_identical'],'Actual original core/source roles must remain separate')
    for name in ORIGINAL:
        body=(ROOT/name).read_bytes()
        require(body==subprocess.check_output(['git','show',COMPILED+':'+name]),'Original collector/observer/auditor may not change: '+name)
        guards[name]=sha(ROOT/name)
    require(sha(INPUT)==INPUT_SHA and load(ROOT/'Tests/Production/Math/Reference/ReloadAtan2/provenance.json')['saved_input_sha256']==INPUT_SHA,'Exact original failed comparison saved input required; no refreshed oracle')
    for name in [*guards,INPUT.relative_to(ROOT).as_posix(),Path(__file__).relative_to(ROOT).as_posix()]:
        require((ROOT/name).read_bytes()==subprocess.check_output(['git','show',source+':'+name]),'Actual committed current source required: '+name)
    return dict(source=source,core=core,original_sources_sha256=guards,original_saved_input_sha256=INPUT_SHA)


def reader(source):
    sys.path.insert(0,str(ROOT/'Tests/Production/RemainingStockPersistence'))
    import observations
    return observations.bind_owner(ROOT,source)


def actual_process(receipt,argv):
    observed=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']]
    require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and len(observed)==1 and observed[0]['start_ticks']>0 and observed[0]['argv']==argv,'Actual successful simulator PID/start/argv/exit required')
    return dict(pid=observed[0]['pid'],start_ticks=observed[0]['start_ticks'],argv=argv,actual_returncode=0)


def validate_three_worlds(folder,report):
    baseline=folder/'baseline';pair=folder/'equivalence';capture=load(pair/'capture.json');audit=load(folder/'original-audit.json')
    require(capture['status']=='passed-native-observer-equivalence-diagnostic-only' and capture['observer_kind']=='additional-passive-module' and capture['on_off_equivalence'] is True and capture['passive_observer_baseline_equivalence'] is True and set(capture['cases'])=={'off','on'},'Both actual original observer modes must complete')
    require(audit['status']=='audited-native-observer-equivalence-diagnostic-only' and audit['software_gate_closed'] is False and audit['phase6_complete'] is False,'Unchanged original complete observer auditor must pass')
    require(set(capture['baseline_sha256'])==set(PRIMARY)==set(report['baseline_primary_sha256']) and capture['baseline_sha256']==report['baseline_primary_sha256'] and len(capture['baseline_sha256'])==14,'Every original full trace/frame/save byte witness required')
    worlds={};identities=set()
    for mode,path in [('baseline',baseline),('off',pair/'observer-off'),('on',pair/'observer-on')]:
        invocation=load(path/('invocation.json' if mode=='baseline' else 'diagnostic-invocation.json'))
        receipt=load(path/('process-receipt.json' if mode=='baseline' else 'process-result.json'))
        p=actual_process(receipt,invocation['argv']);identities.add((p['pid'],p['start_ticks']))
        require(invocation['sanitizer_environment']==SANITIZERS and invocation['argv'][0]==report['runtime_executable'],'Exact original diagnostic role and unsuppressed sanitizers required')
        require(load(path/'graphics-lifecycle.json')==dict(rendered_frames=960,successful_presents=960,context_deleted=True) and (path/'stock-vessel-complete.txt').read_text().strip()=='960','Every world must reach all960 actual finalizations and clean context teardown')
        with (path/'stock-vessel-state.csv').open() as stream:ticks={int(v['tick']) for v in csv.DictReader(stream)}
        require(ticks==set(range(961)),'Complete actual original all-vessel tick roster required')
        require(sha(path/report['derived_case']['scenario_entry_point'])==INPUT_SHA and all(sha(path/n)==v for n,v in capture['baseline_sha256'].items()),'Exact historical input and complete baseline bytes must remain unchanged')
        require((path/'internal-state.csv').is_file()==(mode=='on'),'Extra observer must actually map only for on world')
        require((report['extra_observer'] in (path/'observer-loaded-maps.txt').read_text())==(mode=='on') and str(folder/'remaining-vessels-probe.so') in (path/'observer-loaded-maps.txt').read_text(),'Actual SDK and extra observer mappings differ from mode')
        text=(path/'console.log').read_text(errors='replace')
        require(not any(v in text for v in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','LeakSanitizer has encountered','LuaCall (','Production teardown:','Could not find a module')),'Unsuppressed actual runtime diagnostic')
        worlds[mode]=dict(actual_process=p,lifecycle=load(path/'graphics-lifecycle.json'),process_sha256=sha(path/('process-receipt.json' if mode=='baseline' else 'process-result.json')),actual_saved_input_sha256=INPUT_SHA)
    require(len(identities)==3,'Three distinct actual worlds required; no reused or relabelled prior capture')
    require(all(sha(Path(n))==d for n,d in report['guarded_files_sha256'].items()),'Every original owning source/runtime/provider/input byte must remain unchanged')
    return dict(status='three-actual-worlds-original-observer-equivalence-only',actual_processes=3,actual_presentations=2880,worlds=worlds,all14_original_primary_files_byte_identical=True,original_saved_input_sha256=INPUT_SHA,all_original_sanitizers_unsuppressed=True,normal_admission_qualified=False,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False)


def collect(a):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and a.profile==PROFILE,'Actual standard hosted Linux only; no local simulator')
    source=source_identity();r=reader(source['source']);native=r.native;config=native.settings(r.protocols.V2);contract=r.protocol()
    folder=ROOT/'out/numerical-observer-renewal'/a.profile;require(folder.is_dir() and not (folder/'collection.json').exists(),'Fresh actual compiler output with no earlier capture required')
    compiler=load(folder/'proof.json');require(compiler['status']=='built-two-unchanged-readonly-numerical-observers-only' and compiler['source']==source['source'] and compiler['profile']==a.profile and compiler['actual_original_compiler_processes']==2,'Two fresh actual matching compiler processes required')
    build=ROOT/'out/phase6-hosted-native'/a.profile;engine=build/'engine';record=load(build/'build.json')
    identity=native.build_identity(engine/'orbiter-production',engine/'NativeModules',build/'build.json',COMPILED)
    require(record['source_base']==COMPILED and record['owning_sources_unchanged'] and record['instrumentation']=='address,undefined' and identity['sanitizer_linked'],'Actual unchanged original sanitized application required')
    candidate=engine/'production_remaining_stock_diagnostic';probe=folder/'remaining-vessels-probe.so';extra=folder/'native-internal-observer.so'
    guarded={str(ROOT/n):v for group in ('runtime_files_sha256','candidate_runtime_files_sha256','generated_source_files_sha256') for n,v in record[group].items()}
    for group in ('source_sha256_lf','dependency_sha256_lf'):
        for n,v in record[group].items():
            require(native.sha_lf(ROOT/n)==v==hashlib.sha256(subprocess.check_output(['git','show',COMPILED+':'+n]).replace(b'\r\n',b'\n')).hexdigest(),'Every original compiled source/dependency must remain exact: '+n);guarded[str(ROOT/n)]=sha(ROOT/n)
    guarded.update({str(ROOT/n):v for n,v in source['original_sources_sha256'].items()})
    for path in (build/'build.json',Path(__file__),INPUT,probe,extra,a.gtk_plugin,a.gtk_build_record,folder/'proof.json'):guarded[str(path)]=sha(path)
    for item in compiler['commands']:
        require(sha(Path(item['output']))==item['output_sha256'],'Fresh compiled actual observer output differs')
    gtk=load(a.gtk_build_record);require(gtk['status']=='built' and gtk['baseline'] is False and gtk['sanitizers'] is True and gtk['plugin_sha256']==sha(a.gtk_plugin),'Original instrumented GTK owner required')
    libraries=[d/n for d in a.library for n in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0') if (d/n).exists()]
    require({p.name for p in libraries}=={'libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0'},'Complete actual lifetime providers required')
    for path in libraries:guarded[str(path)]=sha(path)
    assets=load(a.assets/'remaining-vessels-resources.json')['staged_files_sha256'];require(all(sha(a.assets/n)==d for n,d in assets.items()),'All original asset inputs required')
    chosen={n.casefold():n for n in assets};require(len(chosen)==len(assets),'No ambiguous original asset paths')
    for n,d in assets.items():guarded[str(a.assets/n)]=d
    data=r.data_inputs.inspect(a.data,a.planets)
    planet_files=load(ROOT/'Tests/Production/standard-planets.lock.json')['data_files']
    for n,v in data['files'].items():guarded[str((a.planets if n in planet_files else a.data)/n)]=v['sha256']
    parent=next(c for c in config['cases'] if c['id']=='remaining_stock_003');case,provenance=r.derived_case(parent,config,INPUT,INPUT_SHA)
    report=dict(protocol='phase6-fresh-exact-original-save-native-observer-equivalence-v1',status='running-unqualified',source_identity=source,profile=a.profile,compiled_runtime_source=COMPILED,runtime_role='diagnostic',runtime_executable=str(candidate),runtime_identity=identity,derived_case=case,original_saved_input_sha256=INPUT_SHA,extra_observer=str(extra),guarded_files_sha256=guarded,baseline_primary_sha256={},original_data=data,normal_admission_qualified=False,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(folder/'collection.json',report)
    save()
    try:
        require(all(sha(Path(n))==d for n,d in guarded.items()),'Every original input/runtime/source must match before launch')
        baseline=folder/'baseline';r.stage_asset_tree(a.assets,baseline);target=baseline/case['scenario_entry_point'];r.stage_scenario_input(INPUT,target,'windows-save-reload')
        cfg=baseline/'Orbiter.cfg';cfg.unlink(missing_ok=True);cfg.write_text(r.configuration_input.expected(ROOT,source['source'],'native'))
        startup=r.configuration_input.stage(baseline);(baseline/r.protocols.MARKER).write_bytes(r.protocols.marker_bytes(config));(baseline/'persistence-replay.csv').write_bytes(r.replay_bytes(contract));atomic_json(baseline/'persistence-input.json',dict(provenance,historical_diagnostic_input_only=True,no_parent_capture_relabelled=True))
        argv=[str(candidate),'--assets',str(baseline),'--data',str(a.data),'--planets',str(a.planets),'--modules',str(engine/'NativeModules'),'--scenario',str(target),'--config',str(cfg),'--evidence',str(baseline),'--save',str(baseline/'saved.scn'),'--frames','960','--fixed-step',str(config['fixed_step']),'--fixed-system-step',str(config['system_elapsed_input']),'--replay',str(baseline/'persistence-replay.csv'),'--run']
        with native.Compositor(a.compositor_tools,folder/'baseline-compositor') as display:
            asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()
            env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[engine,*a.library])),LD_PRELOAD=asan+':'+str(probe),**SANITIZERS)
            env.pop('ORBITER_TEST_DISABLE_MATH_OBSERVER',None)
            invocation=dict(argv=argv,protocol=r.protocols.V2,persistence_phase='windows-save-reload',collector_producer_commit=source['source'],runtime_role='diagnostic',configuration_input=startup,scenario_entry_point=case['scenario_entry_point'],scenario_sha256_lf=native.sha_lf(target),class_inputs={kind:dict(path=chosen[config['classes'][kind]['target'].casefold()],sha256_lf=config['classes'][kind]['sha256_lf']) for kind in set(case['declared_vessels'].values())},recording_files_sha256={n:sha(baseline/n) for n in native.shared.recordings(case,config)},finalized_frame_descriptor_sha256=sha(baseline/r.protocols.MARKER),save_replay_sha256=sha(baseline/'persistence-replay.csv'),sanitizer_environment=SANITIZERS)
            atomic_json(baseline/'invocation.json',invocation)
            with (baseline/'console.log').open('wb') as stream:
                owned=OwnedProcess(argv,cwd=baseline,env=env,stdout=stream,stderr=subprocess.STDOUT)
                try:owned.process.wait(timeout=1200)
                finally:
                    receipt=owned.cancel();atomic_json(baseline/'process-receipt.json',receipt);atomic_json(baseline/'process-result.json',dict(returncode=owned.process.returncode))
            actual_process(receipt,argv)
        require(display.process.returncode==0,'Original baseline compositor must shut down cleanly')
        require(all(sha(baseline/n)==d for n,d in assets.items() if n!='Orbiter.cfg'),'No original staged assets may change')
        report['baseline_original_inspection']=native.inspect(baseline,case,config,identity,engine,probe,libraries,a.gtk_plugin,runtime_role='diagnostic');report['baseline_saved_state']=r.inspect_save(baseline,contract)
        report['baseline_primary_sha256']={n:sha(baseline/n) for n in [*native.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv','scene.rgba','saved.scn','flight-state.csv']};save()
        controls=folder/'configuration-input-controls.json'
        subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/RemainingStockRepaired/ConfigurationInput.Test.py'),'--capture',str(baseline),'--kind','native','--output',str(controls)],check=True,timeout=120)
        require(load(controls)['status']=='passed','Original actual startup configuration corruption controls required')
        pair=folder/'equivalence';command=[sys.executable,'-B',str(ROOT/'Tests/Production/ReloadMath/capture_native.py'),'--owner',str(ROOT),'--baseline',str(baseline),'--assets',str(a.assets),'--compositor-tools',str(a.compositor_tools),'--gtk-plugin',str(a.gtk_plugin),'--output',str(pair),'--retained-package',str(build),'--extra-observer',str(extra)]
        for lib in a.library:command+=['--library',str(lib)]
        with (folder/'original-capture.log').open('wb') as stream:subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=1500)
        with (folder/'original-audit.log').open('wb') as stream:subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/ReloadMath/audit_native.py'),'--capture',str(pair),'--baseline',str(baseline),'--output',str(folder/'original-audit.json')],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
        require(source_identity()==source and r.data_inputs.inspect(a.data,a.planets)==data,'Original source/core/data changed during capture')
        report['three_world_inspection']=validate_three_worlds(folder,report);report.update(status='captured-and-original-audited-three-world-observer-equivalence-only',published_raw_independent_audit_pending=True);save()
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=[PROFILE],required=True)
    for n in ('assets','data','planets','compositor-tools','gtk-plugin','gtk-build-record'):p.add_argument('--'+n,type=lambda s:Path(s).resolve(),required=True)
    p.add_argument('--library',type=lambda s:Path(s).resolve(),action='append',required=True);collect(p.parse_args())


if __name__=='__main__':main()
