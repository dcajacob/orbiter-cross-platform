"""Re-read actual native persistence captures without promoting their admission status."""
import hashlib
from functools import lru_cache
import importlib.util
import json
from pathlib import Path,PurePosixPath
import re
import subprocess
import sys


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


@lru_cache(maxsize=None)
def git(owner,producer,name):
    require(re.fullmatch('[0-9a-f]{40}',producer),'Immutable full source commit required')
    path=PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,'Unsafe repository input path')
    return subprocess.check_output(['git','-C',str(owner),'show',producer+':'+name])


def bind_owner(owner,producer):
    """Use the retained, hash-checked observation readers with their actual package root."""
    owner=Path(owner).resolve()
    for name in ('Tests/Production/RemainingStockPersistence/capture_native.py',
                 'Tests/Production/RemainingStockRepaired/capture.py','Tests/Production/RemainingVessels/native.py'):
        require(sha_lf(owner/name)==hashlib.sha256(git(owner,producer,name).replace(b'\r\n',b'\n')).hexdigest(),
                'Retained owning reader differs from immutable producer: '+name)
    sys.path[:0]=[str(owner/'Tests/Production/RemainingStockRepaired'),str(owner/'Tests/Production/RemainingStockPersistence')]
    spec=importlib.util.spec_from_file_location('retained_native_persistence_observer',owner/'Tests/Production/RemainingStockPersistence/capture_native.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.ROOT==owner and module.native.ROOT==owner,'Observation reader bound to another workspace')
    saved=sys.modules[module.parse_saved.__module__]
    require(Path(saved.__file__).resolve()==owner/'Tests/Production/RemainingStockPersistence/saved_state.py',
            'Complete saved-state reader bound to another workspace')
    module.content_differences=saved.content_differences
    return module


def check_files(root,values):
    for name,value in values.items():
        path=PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,'Unsafe captured relative path')
        require(sha(root/name)==value,'Actual captured bytes changed: '+str(root/name))


def inspect_native(root,owner,reader,profile,phase,selected=None):
    root=Path(root).resolve();owner=Path(owner).resolve();manifest=root/'capture.json'
    report=json.loads(manifest.read_text());manifest_sha=sha(manifest)
    runtime_owner=Path(report.get('runtime_owner',owner)).resolve()
    role=report.get('runtime_role','diagnostic')
    require(role in ('diagnostic','normal'),'Unknown native application role')
    if role=='normal':require(report.get('process_receipts')=='owned-pid-start-argv-exit-v1','Normal captures require actual owned process receipts')
    delay=report.get('observer_delay_ms',120)
    command=json.loads((root/'probe-command.json').read_text())
    require(type(delay) is int and delay in (0,120) and
            command.count('-DORBITER_NATIVE_FAST_CAPABILITY_DIAGNOSTIC')==int(delay==0),
            'Declared observer pacing differs from actual compile command')
    contract=reader.protocol();config=reader.native.settings(reader.protocols.V2)
    cases=reader.windows.selected_cases(config,selected);ids=[c['id'] for c in cases]
    require(report['status'] in ('captured-diagnostic-only','captured-awaiting-independent-persistence-audit') and
            report['protocol']==contract['protocol'] and report['phase']==phase and report['host']=='native-linux' and
            report['cases_requested']==ids and set(report['cases'])==set(ids) and report['repeats']==2 and report['frames']==960 and
            not report['failures'] and report['owning_sources_runtime_probe_windows_inputs_assets_and_data_unchanged'] and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False,
            'Complete terminal native persistence capture required')
    require(report['diagnostic_only']==(selected is not None),'Native full/selected capture scope differs')
    if selected is None:require(len(cases)==38,'Full native persistence phase requires all 38 unchanged scenes')
    minimum={'Tests/Production/RemainingStockPersistence/capture_native.py','Tests/Production/RemainingStockPersistence/saved_inputs.py',
             'Tests/Production/RemainingStockPersistence/saved_state.py','Tests/Production/RemainingStockPersistence/protocol.json',
             'Tests/Production/RemainingVessels/NativeProbe.cpp','Tests/Production/RemainingVessels/native.py',
             'Tests/Production/RemainingStock/configuration_input.py','Tests/Production/RemainingStock/matched_clock.py'}
    require(minimum<=set(report['source_sha256_lf']),'Native observer/input/clock source closure incomplete')
    for name,value in report['source_sha256_lf'].items():
        require(sha_lf(owner/name)==value==hashlib.sha256(git(owner,report['producer_commit'],name).replace(b'\r\n',b'\n')).hexdigest(),
                'Actual native reader/input differs from immutable producer: '+name)
    first=root/(ids[0]+'-1');invocation=json.loads((first/'invocation.json').read_text())
    engine=Path(invocation['argv'][0]).parent;build_path=engine.parent/'build.json'
    executable=engine/('orbiter-production' if role=='normal' else 'production_remaining_stock_diagnostic')
    build=json.loads(build_path.read_text())
    require(build['source_base']==report['runtime_source_commit'],'Native package source identity differs')
    identity=reader.native.build_identity(engine/'orbiter-production',engine/'NativeModules',build_path,build['source_base'],runtime_owner) \
        if runtime_owner!=owner else reader.native.build_identity(engine/'orbiter-production',engine/'NativeModules',build_path,build['source_base'])
    require(identity==report['runtime_identity'] and identity['profile']==profile and identity['sanitizer_linked'],
            'Actual native build/profile/sanitizer identity differs')
    for name,value in build['dependency_sha256_lf'].items():
        require(sha_lf(runtime_owner/name)==value==hashlib.sha256(git(runtime_owner,build['source_base'],name).replace(b'\r\n',b'\n')).hexdigest(),
                'Native dependency source differs from immutable package producer')
    check_files(runtime_owner,{**build['generated_source_files_sha256'],**build['runtime_files_sha256'],**build['candidate_runtime_files_sha256']})
    generated=list(engine.glob('native-dragonfly-*'));require(len(generated)==1,'Actual generated module source closure ambiguous')
    generated_manifest=json.loads((generated[0]/'native-source.json').read_text())
    require(generated_manifest['bounds_repairs']==[dict(field='EGauge::unit',original_capacity=5,capacity=6,original_longest_label='PITCH')],
            'Fresh native complete gauge-storage repair missing')
    controls=json.loads((root/'native-source-controls.json').read_text())
    require(controls['status']=='passed' and len(controls['controls'])==15 and controls['original_and_generated_files_unchanged'] and
            controls['test_sha256']==sha(owner/'Tests/Production/Dragonfly/NativeSource.Test.py') and
            controls['independent_reader_sha256']==sha(owner/'Tests/Production/Dragonfly/native_source_audit.py'),
            'Actual native source mutation controls missing or changed')
    require(all(sha(Path(n))==v for n,v in report['guarded_files_sha256'].items()),'Actual guarded package/observer/library inputs changed')
    environment=invocation['sanitizer_environment']
    require(environment==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),
            'Native sanitizer configuration differs')
    mapped=(first/'observer-loaded-maps.txt').read_text().splitlines()
    def mapped_file(name):
        paths={Path(line.split()[-1]) for line in mapped if line.split() and
               (Path(line.split()[-1]).name==name or Path(line.split()[-1]).name.startswith(name+'.'))}
        require(len(paths)==1,'Actual native provider missing or ambiguous: '+name)
        actual=paths.pop();alias=actual.parent/name
        require(alias.is_file() and alias.resolve()==actual.resolve() and
                report['guarded_files_sha256'].get(str(alias))==sha(actual),
                'Mapped native provider does not resolve to its exact guarded library bytes')
        return alias
    libraries=[mapped_file(n) for n in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0')]
    gtk=mapped_file('libdecor-gtk.so')
    results={};all_files={};processes=0
    for case in cases:
        rows=report['cases'][case['id']]['runs'];require(len(rows)==2,'Both complete native repetitions required')
        folders=[];runs=[]
        for repeat,recorded in enumerate(rows,1):
            out=root/(case['id']+'-'+str(repeat));folders.append(out)
            executed=recorded['executed_case']
            invocation=json.loads((out/'invocation.json').read_text())
            require(invocation['collector_producer_commit']==report['producer_commit'] and
                    invocation['persistence_phase']==phase and invocation['argv'][0]==str(executable) and
                    invocation.get('runtime_role','diagnostic')==role,
                    'Executed native collector phase/producer/application differs')
            if report.get('process_receipts'):
                require(report['process_receipts']=='owned-pid-start-argv-exit-v1','Unknown native process receipt protocol')
                receipt=json.loads((out/'process-receipt.json').read_text())
                actual=[entry for entry in receipt['owned_process_identities'] if entry['pid']==receipt['actual_collector_pid']]
                require(receipt['terminal'] and not receipt['cancelled'] and receipt['actual_returncode']==0 and
                        len(actual)==1 and actual[0]['start_ticks']>0 and actual[0]['argv']==invocation['argv'],
                        'Actual native simulator PID/start/argv/exit differs')
            require(json.loads((out/'persistence-input.json').read_text())==recorded['persistence_input'],
                    'Actual native saved-input descriptor differs')
            if phase=='stock-writer':require(executed==case,'Unchanged stock-writer scene was substituted')
            else:
                provenance=recorded['persistence_input'];input_path=out/executed['scenario_entry_point']
                derived,derived_provenance=reader.derived_case(case,config,input_path,provenance['saved_input_sha256'])
                require(derived==executed and all(provenance[k]==v for k,v in derived_provenance.items()),
                        'Exact original Windows derived input or saved-vessel closure differs')
                if selected is None:require(provenance['parent_source_variant_protocol']=='remaining-stock-repaired-sources-v4' and
                    provenance['parent_startup_configuration'] is not None,'Full native reload lacks fresh original Windows source/input witnesses')
            check_files(out,recorded['files_sha256']);all_files.update({str(out/n):v for n,v in recorded['files_sha256'].items()})
            options={'runtime_role':role} if role=='normal' else {}
            actual=reader.native.inspect(out,executed,config,identity,engine,root/'remaining-vessels-probe.so',libraries,gtk,**options)
            require(all(recorded[k]==v for k,v in actual.items()),'Recomputed complete native runtime observation differs')
            saved=reader.inspect_save(out,contract);require(saved==recorded['saved_state'],'Complete actual native saved content differs')
            all_files[str(out/'saved.scn')]=saved['sha256']
            all_files[str(out/'persistence-input.json')]=sha(out/'persistence-input.json')
            runs.append(dict(directory=str(out),lifecycle=actual['lifecycle'],actual_math=actual['actual_math'],
                all_vessel_rows=actual['all_vessel_rows'],saved_state=saved,executed_case=executed,persistence_input=recorded['persistence_input']))
            processes+=1
        for name in (*reader.native.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
            require((folders[0]/name).read_bytes()==(folders[1]/name).read_bytes(),'Native repeated complete observation differs: '+name)
        from saved_state import content_differences
        require(not content_differences(runs[0]['saved_state'],runs[1]['saved_state']),'Native repeated full saved content differs')
        score=reader.native.shared.image_ssim((folders[0]/'scene.rgba').read_bytes(),(folders[1]/'scene.rgba').read_bytes(),1280,720)
        require(score>=config['image_ssim_minimum'] and score==report['cases'][case['id']]['repeat_ssim'],'Native repeated full-frame budget failed')
        results[case['id']]=dict(runs=runs,repeat_ssim=score)
    startup=json.loads((root/'configuration-input-controls.json').read_text())
    require(startup['status']=='passed' and startup['kind']=='native' and startup['producer_commit']==report['producer_commit'] and
            startup['owning_capture_unchanged'] and startup['line_ending_reader_positives']==2 and
            len(startup['controls'])==9+int(startup['runtime_configuration_was_rewritten']) and
            sha(root/'configuration-input-controls.json')==report['cases'][ids[0]]['runs'][0]['configuration_input_control_sha256'],
            'Actual native startup input controls missing or changed')
    reader.data_inputs.validate(report['actual_original_data'])
    require(sha(manifest)==manifest_sha and all(sha(Path(n))==v for n,v in all_files.items()) and
            all(sha(Path(n))==v for n,v in report['guarded_files_sha256'].items()),'Owning native capture or protected bytes changed during audit')
    result=dict(status='audited-native-phase-only',phase=phase,profile=profile,diagnostic_only=selected is not None,
        actual_processes=processes,actual_presentations=processes*960,cases=results,capture_sha256=manifest_sha,
        source_producer=report['producer_commit'],runtime_source=build['source_base'],runtime_owner=str(runtime_owner),observer_delay_ms=delay,actual_original_data=report['actual_original_data'],
        guarded_files=len(report['guarded_files_sha256']),process_files=len(all_files),owning_bytes_unchanged=True,
        native_admission_qualified=False,phase6_complete=False)
    if 'runtime_role' in report:result.update(runtime_role=role,process_receipts=report.get('process_receipts'))
    return result
