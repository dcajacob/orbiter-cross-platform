#!/usr/bin/env python3
"""Aggregate four independently replayed original rejection profiles without new simulators."""
import argparse
import os
from pathlib import Path
import stat
import zipfile
from contracts import ROOT,PROFILES,require,load,sha,atomic_json
from checklist import requirements
from hosted_native_general_api import source_identity
import hosted_class_rejections as original
import inspect_published_class_rejections as replay
import restore_rejection_input_bundle as inputs

CI=Path('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')
LOCK=ROOT/'Tests/Production/Closeout/class-rejection-profile-proofs-v1.lock.json'
CAPTURE_LOCK=ROOT/'Tests/Production/Closeout/class-rejection-published-inputs-v1.lock.json'
FLAGS=('complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')


def decode(archive,destination):
    require(not destination.exists(),'Fresh separate published rejection witness destination required')
    destination.mkdir(parents=True);members={};seen=set()
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist()
        require(len(entries)<2000 and sum(i.file_size for i in entries)<128*1024**2,'Bounded complete rejection metadata and tiny compiler witnesses required')
        for item in entries:
            name=item.filename.rstrip('/') if item.is_dir() else item.filename;inputs.original.safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,'Unique safe unprivileged published witness member required')
            seen.add(name.casefold())
            if item.is_dir():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(incoming.read(item));members[name]=dict(bytes=item.file_size,sha256=sha(target))
    return members


def final_api(record,source,run_id,branch,workflow,jobs):
    run=record['run'];actual=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['id']==run_id and run['head_sha']==source and run['head_branch']==branch and run['path']==workflow and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','Exact completed successful public source-bound producer required')
    require(len(actual)==len(jobs)==5 and len({j['id'] for j in actual})==5 and all(jobs.get(str(j['id']))==j['name'] and j['head_sha']==source and j['run_id']==run_id and j['status']=='completed' and j['conclusion']=='success' and j['labels']==['ubuntu-24.04'] for j in actual),'All five exact completed standard-runner jobs required')


def original_coverage(profile,capture,audit,scope,index,frozen,producer):
    expected=requirements()['class-eligibility'];files=index['files'];prefix='out/native-class-rejections/'+profile+'/'
    require(capture['producer_commit']==producer and capture['runtime_owner']==str(CI) and capture['status']=='passed-negative-loader-and-class-controls-only' and capture['failures']=={} and capture['controls_requested']==frozen['exact_original_controls'] and capture['cases_requested']==original.CASES and set(capture['controls'])=={v['id'] for v in frozen['exact_original_controls']},'One exact original producer and all45 original controls required')
    require(capture['runtime_role']==audit['runtime_role']=='normal' and Path(capture['runtime_executable'])==CI/'out/phase6-hosted-native'/profile/'engine/orbiter-production' and audit['runtime_identity']==capture['runtime_identity'] and audit['runtime_identity']['profile']==profile and audit['runtime_identity']['runtime_source_commit']==original.COMPILED and audit['runtime_identity']['sanitizer_linked'] is True,'Actual unchanged normal-host configuration and sanitizer-linked runtime required')
    require(audit['status']=='audited-negative-loader-and-class-controls-only' and audit['families']==expected['families'] and audit['actual_processes']==len(audit['controls'])==45 and audit['owning_bytes_unchanged'] is True and audit['sanitizer_suppressions'] is False and audit['controls']==capture['controls'] and all(v['diagnostic_only'] is True and v['native_admission_qualified'] is False and v['phase6_complete'] is False for v in (capture,audit)),'Every unchanged original audit field and original unqualified capture flag required')
    require(scope['status']=='captured-and-audited-original-normal-host-rejection-controls-only' and scope['profile']==profile and scope['compiled_runtime_source']==original.COMPILED and scope['exact_original_controls']==frozen['exact_original_controls'] and scope['actual_original_processes']==45 and all(scope[k] is True for k in ('no_frames_presented','all_contexts_clean','no_rejected_world_saved','no_invalid_fixture_initialized','unsuppressed_original_sanitizers')) and all(scope[k] is False for k in FLAGS),'Complete original separately scoped process verification required')
    identities=scope['actual_original_process_identities'];require(len(identities)==45 and [v['control'] for v in identities]==[v['id'] for v in frozen['exact_original_controls']],'Every exact original process identity in original control order required')
    seen=set()
    for identity in identities:
        name=identity['control'];value=audit['controls'][name];token=(identity['pid'],identity['start_ticks']);folder=prefix+name+'/'
        require(identity['pid']==value['actual_pid']>0 and identity['start_ticks']>0 and token not in seen and identity['argv'] and identity['argv'][0]==capture['runtime_executable'],'One distinct actual original OS process/start/argv per control required');seen.add(token)
        require(value['actual_exitcode']==1 and value['lifecycle']==dict(rendered_frames=0,successful_presents=0,context_deleted=True) and value['expected_error'],'All original deliberate nonzero exits, zero frames and clean contexts required')
        require(value['files_sha256'] and all(files[folder+n]['sha256']==digest for n,digest in value['files_sha256'].items()) and identity['receipt_sha256']==value['files_sha256']['process-receipt.json'] and identity['invocation_sha256']==value['files_sha256']['invocation.json'] and folder+'saved.scn' not in files,'Every original complete process file, OS receipt, invocation and absent rejected save required')
    guards=capture['guarded_files_sha256'];require(guards and all(Path(name).is_relative_to(CI) and files[Path(name).relative_to(CI).as_posix()]['sha256']==digest for name,digest in guards.items()),'Every original source, runtime, fixture and resource guard required')
    return dict(actual_original_processes=45,actual_unique_PID_start_identities=len(seen),original_guard_records=len(guards),families=expected['families'],runtime_source=original.COMPILED,original_producer=producer,all_original_controls_and_guards_preserved=True)


def inspect_profile(profile,base,pin,capture_lock):
    record=load(base/'api.json');final_api(record,pin['source'],pin['run_id'],pin['branch'],pin['workflow'],pin['jobs']);artifact=record['artifact'];archive=base/'producer.zip'
    require(artifact['id']==pin['artifact_id'] and artifact['name']=='independent-original-rejections-full-witness-'+profile and artifact['expired'] is False and artifact['size_in_bytes']==pin['archive_bytes']==archive.stat().st_size and artifact['digest']=='sha256:'+pin['archive_sha256'] and sha(archive)==pin['archive_sha256'] and artifact['workflow_run']['id']==pin['run_id'] and artifact['workflow_run']['head_sha']==pin['source'],'Exact complete independent published witness ZIP required')
    payload=base/'decoded';members=decode(archive,payload);folder=payload/'rejection-independent'/profile
    proof=load(folder/'proof.json');capture=load(folder/'original-capture.json');audit=load(folder/'fresh-original-audit.json');old=load(folder/'original-published-audit.json');index=load(folder/'original-raw-index.json');outer=load(folder/'outer-members.json')
    raw_api_path=payload/'class-rejection-published'/profile/'api.json';raw_api=load(raw_api_path);raw_pin=replay.validate_api(raw_api,capture_lock,profile)
    require(proof['protocol']=='phase6-independent-published-original-rejection-profile-v1' and proof['status']=='independently-replayed-all45-original-normal-host-rejections-only' and proof['profile']==profile and proof['auditor_source']==pin['source'] and proof['input_protocol']==capture_lock['protocol'] and proof['original_source']==capture_lock['source'] and proof['original_run_id']==capture_lock['run_id'] and proof['original_job_id']==raw_pin['job_id'] and proof['original_artifact']==raw_api['artifact'] and proof['original_archive_bytes']==raw_pin['archive_bytes'] and proof['original_archive_sha256']==raw_pin['archive_sha256'],'Complete distinct original capture and actual independent auditor lineage required')
    require(proof['actual_original_processes']==45 and proof['new_simulator_processes']==0 and proof['all_original_raw_bytes_and_aliases_unchanged'] is True and proof['original_SDK_operation_flags_preserved'] is True and all(proof[k] is False for k in FLAGS),'Independent raw replay must retain every original byte, operation flag and pending acceptance scope')
    require(index['protocol']=='phase6-lossless-original-rejection-input-bundle-v1' and index['status']=='preserved-original-files-only-not-qualified' and index['source_root']==str(CI) and index['missing_guarded_paths']==[] and index['original_files_rewritten'] is False and index['source_and_runtime_rejection_audits_still_required'] is True and sha(folder/'original-raw-index.json')==proof['raw_index_sha256'] and len(index['files'])==index['closure']['logical_files']==proof['original_raw_logical_files'] and index['closure']['all_logical_names_types_lengths_and_digests_preserved'] is True,'Full unchanged independently restored raw logical file/alias/type/length/mode index required')
    require(sha(folder/'outer-members.json')==proof['outer_members_sha256'] and len(outer)==proof['original_raw_members'] and sha(raw_api_path)==proof['source_api_sha256'],'Every exact independently read outer member and original API witness required')
    oldprefix='out/hosted-native-class-rejections/'+profile+'/'
    require(outer[oldprefix+'raw-index.json']['sha256']==proof['raw_index_sha256'] and outer[oldprefix+'raw-original-inputs.tar.gz']['sha256']==index['archive_sha256'] and outer[oldprefix+'raw-original-inputs.tar.gz']['bytes']==index['archive_bytes'],'Complete raw archive and logical input table must retain exact published identities')
    capname='out/native-class-rejections/'+profile+'/rejections.json'
    require(sha(folder/'original-capture.json')==proof['original_capture_sha256']==proof['original_capture_copy_sha256']==audit['capture_sha256']==index['files'][capname]['sha256'] and sha(folder/'original-published-audit.json')==proof['original_audit_sha256']==proof['original_published_audit_copy_sha256']==outer[oldprefix+'original-rejections-audit.json']['sha256'] and sha(folder/'fresh-original-audit.json')==proof['fresh_original_audit_sha256'],'Actual original capture and both independently compared original audit byte identities required')
    comparison=inputs.compare_original_audit(old,audit,[v['id'] for v in original.conserved_sources()['exact_original_controls']]);require(comparison==proof['original_audit_comparison']==load(folder/'original-audit-comparison.json'),'Every original audit type, value, membership and list order must reproduce exactly')
    command=proof['commands'];require(len(command)==1 and command[0]['label']=='unchanged-original-independent-rejection-audit' and command[0]['actual_pid']>0 and command[0]['actual_returncode']==0 and command[0]['log_sha256']==sha(folder/'fresh-original-audit.log') and command[0]['argv'][1:3]==['-B','Tests/Production/RemainingVessels/rejections.py'],'Actual completed unchanged original auditor command and complete log required')
    scope=proof['original_scoped_rejections'];coverage=original_coverage(profile,capture,audit,scope,index,original.conserved_sources(),capture_lock['source'])
    require(coverage['original_guard_records']==proof['original_guard_records'] and all(Path(name).is_relative_to(CI) and index['files'][Path(name).relative_to(CI).as_posix()]['sha256']==digest for name,digest in scope['metadata_sha256'].items()),'Every exact original guard and scoped metadata identity required')
    compiler=proof['original_actual_host_compiler_proof'];require(compiler==load(folder/'original-host-compiler-proof.json') and compiler['actual_original_host_compiler_processes']==compiler['actual_unique_PID_start_identities']==7 and compiler['actual_container_adapter_retained'] is True and compiler['original_argv_source_SDK_and_sanitizers_preserved'] is True and compiler['original488_runtime_package_versions_unchanged'] is True and compiler['compiler_version_or_ABI_macros_overridden'] is False,'Actual original seven-process compiler/alias/ABI proof required')
    compiler_prefix='out/rejection-fixture-compiler/'+profile+'/';provenance=folder/'compiler-provenance'
    for name,value in outer.items():
        if name.startswith(compiler_prefix) and (Path(name).suffix in ('.json','.log') or Path(name).name=='container-compiler-adapter'):
            target=provenance/Path(name).name;require(target.stat().st_size==value['bytes'] and sha(target)==value['sha256'],'Actual compiler receipt, preprocessor log and declared adapter bytes required')
    source=provenance/'rejection_fixture_compiler_bridge.py';require(sha(source)==compiler['original_compiler_source_sha256']==sha(ROOT/'Tests/Production/Closeout/rejection_fixture_compiler_bridge.py'),'Exact unchanged compiler transport source required')
    bridge=load(provenance/'compiler-bridge.json');require(bridge['source']==capture_lock['source'] and bridge['profile']==profile and bridge['actual_engine_CPP_ABI']==compiler['actual_engine_CPP_ABI'],'Original actual compiler report scope required')
    for request in bridge['requests']:
        name=Path(request['actual_host_argv'][-1]).name;require(sha(provenance/'fixtures'/name)==request['output_sha256']==index['files'][Path(request['actual_host_argv'][-1]).relative_to(CI).as_posix()]['sha256'],'All seven original actual fixture output bytes required')
    core=proof['original_core_identity'];current=source_identity();require(core['collector_source']==pin['source'] and {k:v for k,v in core.items() if k!='collector_source'}=={k:v for k,v in current.items() if k!='collector_source'},'Actual623 native/current-Windows core sources must remain identical')
    return dict(coverage=coverage,original_capture_sha256=proof['original_capture_sha256'],original_audit_sha256=proof['original_audit_sha256'],fresh_original_audit_sha256=proof['fresh_original_audit_sha256'],original_audit_comparison=comparison,original_raw_logical_files=proof['original_raw_logical_files'],original_guard_records=proof['original_guard_records'],raw_index_sha256=proof['raw_index_sha256'],outer_members_sha256=proof['outer_members_sha256'],independent_source=pin['source'],independent_run_id=pin['run_id'],independent_artifact_id=pin['artifact_id'],independent_archive_sha256=pin['archive_sha256'],independent_proof_sha256=sha(folder/'proof.json'),original_raw_artifact_id=raw_pin['artifact_id'],original_raw_archive_sha256=raw_pin['archive_sha256'],original_compiler_proof=compiler,all_published_witness_members=members)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT==CI,'Actual standard hosted worker required')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out'),'Fresh separate final rejection facet output required');a.output.mkdir(parents=True)
    lock=load(LOCK);capture_lock=load(CAPTURE_LOCK);require(set(lock['profiles'])==set(capture_lock['profiles'])==set(PROFILES),'All four original independently audited profiles required')
    final_api(load(a.inputs/'capture-final-api.json'),capture_lock['source'],capture_lock['run_id'],capture_lock['branch'],capture_lock['workflow'],capture_lock['jobs'])
    conserved=original.conserved_sources();core=source_identity();profiles={profile:inspect_profile(profile,a.inputs/profile,lock['profiles'][profile],capture_lock) for profile in PROFILES}
    require(original.conserved_sources()==conserved and source_identity()==core,'Immutable owning sources changed during final rejection aggregation')
    report=dict(protocol='phase6-renewed-independent-rejection-facet-v1',status='verified-four-profile-original-rejection-controls-facet-only',auditor_source=os.environ['GITHUB_SHA'],passed_class_facets=['rejection-controls'],profiles=profiles,families=requirements()['class-eligibility']['families'],actual_original_processes=180,actual_original_compiler_processes=28,original_capture_source=capture_lock['source'],original_capture_run_id=capture_lock['run_id'],compiled_runtime_source=original.COMPILED,original_auditors_conserved=conserved,actual_core_identity=core,source_control_lock_sha256=sha(LOCK),original_capture_lock_sha256=sha(CAPTURE_LOCK),original_complete_capture_api_sha256=sha(a.inputs/'capture-final-api.json'),new_simulator_processes=0,old_capture_or_pending_flags_relabelled=False,all_original_tests_sanitizers_guards_and_acceptance_unchanged=True,complete_raw_captures_and_witnesses_stayed_on_GitHub=True,scope='Only original all45 normal-host deliberate rejections in each of four profiles. Every original raw audit independently reexecuted and exact fields/values reproduced. Full class eligibility, candidate freeze, normal157 admission, workflows, interfaces, lifecycle and local acceptance remain separate.',**{k:False for k in FLAGS})
    atomic_json(a.output/'proof.json',report);print(report['status'])


if __name__=='__main__':main()
