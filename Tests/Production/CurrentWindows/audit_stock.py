#!/usr/bin/env python3
"""Audit a complete declared current/native stock matrix with unchanged comparators."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/GeneralApiCorrection')]
from contracts import require,sha,load,atomic_json
from receipts import inspect_launch,windows_path
from qualification import inspect as inspect_sdk_qualification
from stock import selection,inspect_run

RUNNER_SOURCES={
    'stock_runtime_worker_v3.py':'Closeout/LocalVM/stock_runtime_worker_v3.py',
    'current_stock.py':'CurrentWindows/stock.py',
    **{name:'Closeout/LocalVM/'+name for name in ('runtime_descriptor_v2.py','runtime_descriptor_v3.py')},
    'static_binary_link_staging_v1.py':'RemainingStockPersistence/LocalVM/static_binary_link_staging_v1.py',
    **{name:'CurrentWindows/LocalVM/'+name for name in ('win_local_process_v1.py','private_desktop_bootstrap_v1.py','system_user_launcher_v1.py')}}


def immutable(commit,name):
    return subprocess.check_output(['git','-C',str(ROOT),'show',commit+':Tests/Production/'+name])


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def retain_launch(capture,jobs,vm,configuration,output):
    target=output/configuration;shutil.copytree(capture,target)
    cfg=load(target/'request.json')
    for name in ('system-launch','bootstrap-started','bootstrap-result'):
        shutil.copy2(target/(cfg['name']+'-'+name+'.json'),target/(name+'.json'))
    for source,name in [(jobs/(configuration+'-capture-job.json'),'guest-job.json'),
                        (jobs/(configuration+'-capture-terminal.json'),'guest-result.json'),
                        (jobs/(configuration+'-capture-terminal.json.binding.json'),'guest-result.binding.json'),(vm,'vm.json')]:
        shutil.copy2(source,target/name)
    binding=load(target/'guest-result.binding.json');job=load(target/'guest-job.json')
    require(binding==dict(job_sha256=sha(target/'guest-job.json'),terminal_sha256=sha(target/'guest-result.json'),
                         actual_guest_pid=job['pid'],domain_uuid=job['domain_uuid']), 'Actual current-stock guest terminal binding differs')
    runners=load(target/'runners.json');trusted=runners['files_sha256']
    require(runners['commit']==cfg['roles']['runner']['commit'] and sha(target/'runners.json')==cfg['roles']['runner']['manifest_sha256'] and
            set(trusted)==set(RUNNER_SOURCES), 'Current stock runner role/file closure differs')
    for name,source in RUNNER_SOURCES.items():
        body=immutable(runners['commit'],source)
        require(hashlib.sha256(body).hexdigest()==trusted[name], 'Current stock runner differs from its immutable source: '+name)
    cfg,worker,actual_vm=inspect_launch(target,trusted)
    require(worker['status']=='captured-current-Windows-stock-and-paired-exact-save-reloads' and
            worker['owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged'] is True and
            worker['simulation_comparison_and_independent_audit_pending'] is True and cfg['configuration']==configuration,
            'Actual complete current-stock terminal result required')
    export=target/'export'
    require(worker['export_files_sha256']=={p.relative_to(export).as_posix():sha(p) for p in export.rglob('*') if p.is_file()},
            'Actual current stock raw export closure/hash differs')
    return target,cfg,worker


def inspect_observer(root,cfg,qualified,output):
    path=root/(root.name+'-status.json');record=load(path);observer=record['observer'];configuration=cfg['configuration']
    profile=configuration+'-automatic';roles=qualified['cohorts']['current-windows'][profile]['roles']
    require(all(cfg['roles'][name]==roles[name] for name in ('application','sdk')),
            'Current application/SDK identity differs from the independently restored retained package')
    require(sha(path)==cfg['roles']['observer']['manifest_sha256'] and record['status']=='prepared-passive-observer-only' and
            record['sdk']['manifest_sha256']==roles['sdk']['manifest_sha256'] and observer['kind']=='remaining-stock' and
            observer['source_commit']==cfg['roles']['observer']['commit'] and observer['sdk_source_commit']==cfg['source_commit'] and
            observer['configuration']==configuration and sha(root/'ProductionCockpitDriver.dll')==observer['sha256'],
            'Current-SDK stock observer build identity differs')
    source=immutable(observer['source_commit'],'RemainingStock/Driver.cpp');original=source.replace(b'\r\n',b'\n')
    old=b'require(frames==60,"Incomplete original stock observation")';require(original.count(old)==1,'Stock observer assertion anchor differs')
    compiled=original.replace(old,b'require(frames==960,"Incomplete repaired stock observation")')
    variant=record['observer_source_variant']
    require(hashlib.sha256(source).hexdigest()==observer['source_sha256']==variant['original_sha256'] and
            hashlib.sha256(compiled).hexdigest()==variant['compiled_sha256'] and
            variant['only_change']=='Validate 960 finalized ticks instead of 60; all observation calls and delays unchanged',
            'Stock observer changed beyond its existing finalized-frame assertion')
    snapshot=record['source_snapshot']
    for name,checksum in snapshot['files_sha256'].items():
        require(hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show',observer['source_commit']+':'+name])).hexdigest()==checksum,
                'Stock observer include/source snapshot differs')
    require(all(command['actual_returncode']==0 and type(command['actual_pid']) is int and command['actual_pid']>0 and
                sha(root/(command['label']+'.log'))==command['log_sha256'] for command in record['commands']), 'Actual stock observer compiler receipt differs')
    shutil.copytree(root,output/(configuration+'-observer'))
    return observer


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('debug-capture','release-capture','debug-observer','release-observer','jobs','vm','sdk-qualification',
                 'native-owner','original-reference','output'):p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh current stock independent audit directory required');a.output.mkdir()
    result=dict(status='running',profiles={},phase6_complete=False,normal_stock_admission_qualified=False)
    protected={str(a.sdk_qualification):sha(a.sdk_qualification)}
    try:
        qualified=inspect_sdk_qualification(a.sdk_qualification)
        protected.update(qualified['evidence_sha256'])
        sys.path.insert(0,str(a.native_owner/'Tests/Production/RemainingStockPersistence'))
        observations=module(a.native_owner/'Tests/Production/RemainingStockPersistence/observations.py','current_stock_native_observations')
        first=a.native_owner/'out/phase6-atan2-focused-Debug-automatic-writer-v1/capture.json'
        producer=load(first)['producer_commit'];reader=observations.bind_owner(a.native_owner,producer)
        pairs=module(a.native_owner/'Tests/Production/RemainingStockPersistence/audit.py','current_stock_persistence_pairs')
        config=reader.native.settings(reader.protocols.V2);all_ids=None;all_processes=0
        for configuration,capture,observer_root in [('Debug',a.debug_capture,a.debug_observer),('Release',a.release_capture,a.release_observer)]:
            target,cfg,worker=retain_launch(capture,a.jobs,a.vm,configuration,a.output)
            cases,diagnostic=selection(cfg,config);ids=[case['id'] for case in cases]
            require(worker['cases_requested']==ids and worker['diagnostic_only'] is diagnostic and
                    worker['repeats']==2 and worker['frames']==960, 'Current stock requested scope/repetition/frame count differs')
            if all_ids is None:all_ids=ids
            require(ids==all_ids,'Current Windows configurations use different scene scopes')
            observer=inspect_observer(observer_root,cfg,qualified,a.output)
            require(reader.windows.data_inputs.validate(worker['actual_simulation_data'])==57,'Actual current simulation-data closure incomplete')
            expected={(mode,phase,case['id'],repeat) for mode in ('automatic','sse2') for phase in ('stock','reload') for case in cases for repeat in (1,2)}
            receipts=worker['actual_process_receipts'];seen=set();export=target/'export'
            for item in receipts:
                key=(item['math_profile'],item['phase'],item['case'],item['repeat']);require(key in expected and key not in seen,'Missing/duplicate current process receipt')
                seen.add(key);folder=export/(key[0]+'-'+key[1])/(key[2]+'-'+str(key[3]));timing=load(folder/'process-timing.json')
                require(timing==item['timing'] and timing['actual_returncode']==0 and timing['timed_out'] is False and
                        timing['timeout_seconds']==900 and type(timing['actual_pid']) is int and timing['actual_pid']>0 and
                        type(timing['elapsed_wall_ns']) is int and timing['elapsed_wall_ns']>0 and
                        windows_path(item['folder'])==windows_path(cfg['output'])/(key[0]+'-'+key[1])/(key[2]+'-'+str(key[3])),
                        'Actual current simulator output/PID/exit/timeout receipt differs')
            require(seen==expected and worker['actual_processes']==len(expected) and worker['successful_presents']==960*len(expected),
                    'Every declared current simulator process required')
            all_processes+=len(expected)
            require(set(worker['cases'])=={mode+'-'+phase+'-'+case['id'] for mode in ('automatic','sse2') for phase in ('stock','reload') for case in cases},
                    'Current stock result case coverage incomplete')
            supplied={(item['math_profile'],item['case'],item['repeat']):item for item in cfg['windows_save_inputs']}
            for mode in ('automatic','sse2'):
                profile=configuration+'-'+mode;results={}
                for phase,native_phase,native_suffix,original_phase in [('stock','stock-writer','writer','remaining-stock-repaired'),
                         ('reload','windows-save-reload','reload','remaining-stock-persistence')]:
                    native=a.native_owner/'out'/('phase6-atan2-focused-'+profile+'-'+native_suffix+'-v1')
                    native_audit=observations.inspect_native(native,a.native_owner,reader,profile,native_phase,ids if diagnostic else None)
                    require(native_audit['actual_processes']==len(cases)*2,'Complete paired native phase required')
                    atomic_json(a.output/(profile+'-'+native_suffix+'-native-independent-audit.json'),native_audit)
                    native_report=load(native/'capture.json');protected[str(native/'capture.json')]=sha(native/'capture.json')
                    original_root=a.original_reference/profile/original_phase;original_report=load(original_root/'capture.json')
                    protected[str(original_root/'capture.json')]=sha(original_root/'capture.json')
                    for case in cases:
                        records=worker['cases'][mode+'-'+phase+'-'+case['id']]['runs'];require(len(records)==2,'Both current Windows repetitions required')
                        for repeat,record in enumerate(records,1):
                            name=case['id']+'-'+str(repeat);folder=export/(mode+'-'+phase)/name;native_folder=native/name;original=original_root/name
                            original_record=original_report['cases'][case['id']]['runs'][repeat-1]
                            for name,checksum in original_record['files_sha256'].items():
                                require(sha(original/name)==checksum,'Retained original Windows reference bytes changed');protected[str(original/name)]=checksum
                            native_record=native_report['cases'][case['id']]['runs'][repeat-1]
                            for name,checksum in native_record['files_sha256'].items():protected[str(native_folder/name)]=checksum
                            executed=record['executed_case'];actual=inspect_run(folder,executed,config,reader,cfg['source_commit'],ROOT)
                            require(all(actual[key]==value for key,value in record.items() if key in actual), 'Independent current stock trace/clock observation differs')
                            require(actual['actual_math']==('sse2' if mode=='sse2' else 'fma3'), 'Actual paired current math mode differs')
                            metadata=load(folder/'current-runtime-variant.json')
                            require(metadata==dict(cohort='current-windows',roles=cfg['roles'],configuration=configuration,math_profile=mode,
                                phase=phase,case=case['id'],repeat=repeat,paired_windows_input=supplied[(mode,case['id'],repeat)] if phase=='reload' else None),
                                'Actual current runtime roles/input dispatch metadata differs')
                            modules=record['loaded_modules'];mapped=[item for item in modules if windows_path(item['path']).name.casefold()=='productioncockpitdriver.dll']
                            require(len(mapped)==1 and mapped[0]['sha256']==observer['sha256'], 'Actual mapped current-SDK observer differs')
                            if phase=='reload':
                                saved=supplied[(mode,case['id'],repeat)];input_path=folder/executed['scenario_entry_point']
                                require(sha(input_path)==saved['sha256']==native_record['persistence_input']['saved_input_sha256'],
                                        'Current Windows and native did not consume the same exact hashed original Windows save')
                                derived,provenance=reader.derived_case(case,config,input_path,saved['sha256'])
                                require(derived==executed and record['persistence_input']==provenance, 'Actual complete saved-vessel/recording input differs')
                            else:require(executed==case and record['persistence_input'] is None,'Unchanged current writer scene was substituted')
                            comparison=pairs.compare_pair(folder,native_folder,reader,config)
                            original_state=reader.original_audit.compare_state(original,folder,config)
                            original_camera=reader.original_audit.camera_comparison(original,folder,config)
                            require(all((original/name).read_bytes().replace(b'\r\n',b'\n')==(folder/name).read_bytes().replace(b'\r\n',b'\n')
                                        for name in ('stock-clock.csv','stock-step-clock.csv')), 'Original/current Windows actual clocks differ')
                            differences=reader.content_differences(reader.parse_saved(original/pairs.CURRENT),reader.parse_saved(folder/pairs.CURRENT),
                                                                   reader.protocol()['operator_description_blocks'])
                            require(not differences,'Complete original/current Windows serialization differs')
                            ssim=reader.windows.image_ssim((original/'scene.rgba').read_bytes(),(folder/'scene.rgba').read_bytes(),1280,720)
                            require(ssim>=config['image_ssim_minimum'],'Original/current Windows framebuffer exceeds unchanged budget')
                            results[phase+'-'+case['id']+'-'+str(repeat)]=dict(current_native=comparison,original_current=dict(state=original_state,
                                camera=original_camera,ssim=ssim,complete_saved_content_identical=True,actual_clocks_identical_lf=True))
                result['profiles'][profile]=results
        protected.update({str(p):sha(p) for p in a.output.rglob('*') if p.is_file()})
        require(all(sha(path)==checksum for path,checksum in protected.items()), 'Current stock/reference/native inputs changed during independent audit')
        result.update(status='passed-current-Windows-native-stock-and-exact-save-matrix',diagnostic_only=diagnostic,cases_requested=all_ids,
            current_windows_processes=all_processes,native_processes=all_processes,original_reference_runs=all_processes,
            evidence_sha256=protected,unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum'],
            historical_original_launch_receipts_reconstructed=False,final_candidate_qualification=False,
            scope='Declared scenes, all four profiles, both repetitions and writer/reload phases only; no full38 or class-admission inference')
    except BaseException as error:
        result.update(status='failed',error=str(error));raise
    finally:atomic_json(a.output/'audit.json',result)
    print(json.dumps({key:result[key] for key in ('status','diagnostic_only','cases_requested','current_windows_processes','native_processes')}))


if __name__=='__main__':main()
