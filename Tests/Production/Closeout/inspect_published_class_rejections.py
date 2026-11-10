#!/usr/bin/env python3
"""Independently replay every unchanged original rejection audit from exact published raw bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import sys
import zipfile
from contracts import ROOT,PROFILES,require,load,sha,atomic_json
import hosted_class_rejections as original
import restore_rejection_input_bundle as inputs
import restore_rejection_sdk_header as sdk
from hosted_native_general_api import source_identity


def validate_api(api,lock,profile):
    require(profile in PROFILES and profile in lock['profiles'],'One completed exact original profile required')
    run=api['run'];jobs=api['jobs'];artifact=api['artifact'];pin=lock['profiles'][profile]
    require(api['repository']==lock['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['id']==lock['run_id'] and run['head_sha']==lock['source'] and run['head_branch']==lock['branch'] and run['path']==lock['workflow'] and run['run_attempt']==1 and run['status'] in ('queued','in_progress','completed'),'Exact original public rejection producer required')
    require(len(jobs)==len(lock['jobs'])==5 and len({j['id'] for j in jobs})==5,'Complete original readiness/four-profile job roster required')
    for j in jobs:require(lock['jobs'].get(str(j['id']))==j['name'] and j['run_id']==run['id'] and j['head_sha']==run['head_sha'] and j['labels']==['ubuntu-24.04'],'Exact original standard hosted profile source/role required')
    for identity in (lock['readiness_job_id'],pin['job_id']):
        selected=next(j for j in jobs if j['id']==identity);require(selected['status']=='completed' and selected['conclusion']=='success','Only completed successful readiness and selected profile may be replayed')
    require(artifact['id']==pin['artifact_id'] and artifact['name']=='original-class-normal-host-rejection-controls-'+profile and artifact['expired'] is False and artifact['size_in_bytes']==pin['archive_bytes'] and artifact['digest']=='sha256:'+pin['archive_sha256'] and artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==run['head_sha'],'Exact published original rejection ZIP source/digest required')
    return pin


def restore_outer(archive,payload,profile):
    require(not payload.exists(),'Fresh complete outer artifact restoration required');payload.mkdir(parents=True);members={};seen=set();total=0
    with zipfile.ZipFile(archive) as incoming:
        for item in incoming.infolist():
            name=item.filename;p=PurePosixPath(name)
            require(name and (str(p)==name or item.is_dir() and str(p)+'/'==name) and not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,'Safe unique nonredirected original artifact member required')
            seen.add(name.casefold());total+=item.file_size;require(len(seen)<100000 and total<8*1024**3,'Bounded complete original rejection artifact required')
            dest=payload/name
            if item.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            with incoming.open(item) as source,dest.open('xb') as output:shutil.copyfileobj(source,output,1024*1024)
            require(dest.stat().st_size==item.file_size,'Full original outer member required');members[name]=dict(bytes=item.file_size,sha256=sha(dest))
    base='hosted-native-class-rejections/'+profile+'/'
    require({base+n for n in ('collection.json','raw-index.json','raw-original-inputs.tar.gz','original-rejections-audit.json','original-SDK-header-restoration.json','original-fixture-SDK.json','original-Windows-PE.json')}<=set(members),'Every complete actual original capture, audit and input bundle required')
    return members


def semantic_sdk(report):
    result={k:v for k,v in report.items() if k!='header_was_present'}
    # Tool argv/return codes are exact, but nm/readelf output formatting can
    # differ between Ubuntu24 auditor and Ubuntu26 capture. Retain both raw
    # receipts and compare every actual exported/imported symbol and NEEDED.
    def visit(value):
        if isinstance(value,dict):
            if set(value)=={'argv','actual_returncode','stdout_sha256','stderr_sha256'}:
                require(value['actual_returncode']==0 and all(len(value[k])==64 for k in ('stdout_sha256','stderr_sha256')),'Successful actual metadata command receipt required')
                return {k:value[k] for k in ('argv','actual_returncode')}
            return {k:visit(v) for k,v in value.items()}
        if isinstance(value,list):return [visit(v) for v in value]
        return value
    return visit(result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','lock','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual independent standard Ubuntu worker required; no local raw transfer or simulator')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out/rejection-independent'),'Fresh separate original rejection audit output required');a.output.mkdir(parents=True)
    report=dict(protocol='phase6-independent-published-original-rejection-profile-v1',status='running',profile=a.profile,auditor_source=os.environ['GITHUB_SHA'],commands=[],new_simulator_processes=0,complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(a.output/'proof.json',report)
    try:
        lock=load(a.lock);api=load(a.api);pin=validate_api(api,lock,a.profile)
        require(a.archive.stat().st_size==pin['archive_bytes'] and sha(a.archive)==pin['archive_sha256'],'Actual complete original rejection ZIP differs')
        frozen=original.conserved_sources();core=source_identity();members=restore_outer(a.archive,a.output/'original-artifact',a.profile);payload=a.output/'original-artifact';old=payload/'hosted-native-class-rejections'/a.profile
        atomic_json(a.output/'outer-members.json',members);collection=load(old/'collection.json');index=load(old/'raw-index.json')
        require(collection['status']=='captured-and-audited-original-normal-host-rejection-controls-only' and collection['collector_source']==lock['source'] and collection['profile']==a.profile and collection['actual_processes']==45 and collection['compiled_runtime_source']==original.COMPILED and collection['published_raw_independent_replay_pending'] is True and all(collection[k] is False for k in ('complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')),'Exact complete original scoped rejection collection required')
        require(collection['original_rejection_source_identity']==frozen and collection['core_source_identity']['collector_source']==lock['source'] and {k:v for k,v in collection['core_source_identity'].items() if k!='collector_source'}=={k:v for k,v in core.items() if k!='collector_source'},'Original complete core/fixture/collector/auditor source identity required')
        for command in collection['commands']:require(command['actual_pid']>0 and command['actual_returncode']==0 and not command.get('timed_out') and sha(old/(command['label']+'.log'))==command['log_sha256'],'Every original preparation/capture/audit command and completed log required')
        capname='out/native-class-rejections/'+a.profile+'/rejections.json';require(capname in index['files'],'Original raw capture must be present in its exact lossless bundle')
        # Read the original capture only after the full archive/index digest and
        # membership have been checked by the unchanged lossless bundle reader.
        import rejection_input_bundle as bundle
        require(bundle.inspect_archive(old/'raw-original-inputs.tar.gz',index['files'])==index['closure'],'Complete original logical input closure required')
        import tarfile
        with tarfile.open(old/'raw-original-inputs.tar.gz') as incoming:captured=json.load(incoming.extractfile(capname))
        require(captured['producer_commit']==lock['source'] and captured['runtime_owner']==str(ROOT) and captured['controls_requested']==frozen['exact_original_controls'] and len(captured['controls'])==45,'Actual original source/owner/all45 controls required')
        orders={str(Path(capname).parent/control):list(value['files_sha256']) for control,value in captured['controls'].items()}
        restoration=inputs.restore(ROOT,old/'raw-original-inputs.tar.gz',index,a.output/'objects',orders);atomic_json(a.output/'restored-original-inputs.json',restoration)
        capture=ROOT/capname;hosted=ROOT/'out/hosted-native-class-rejections'/a.profile
        shutil.copy2(capture,a.output/'original-capture.json');shutil.copy2(old/'original-rejections-audit.json',a.output/'original-published-audit.json')
        require(load(capture)==captured and captured['guarded_files_sha256'] and all(sha(name)==value for name,value in captured['guarded_files_sha256'].items()),'Every original raw source/runtime/resource/fixture guard must remain exact')
        for name in ('collection.json','original-rejections-audit.json','original-SDK-header-restoration.json','original-fixture-SDK.json','original-Windows-PE.json'):require((hosted/name).read_bytes()==(old/name).read_bytes(),'Outer and lossless original metadata bytes differ')
        before=load(old/'original-SDK-header-restoration.json');fresh=sdk.restore(a.profile,ROOT/'out/phase6-hosted-native'/a.profile/'build.json',a.output/'fresh-SDK-check.json')
        require(before['header_was_present'] is False and fresh['header_was_present'] is True and semantic_sdk(before)==semantic_sdk(fresh),'Actual SDK template/token/descriptor owner/topology/header identities must reproduce; original creation flag remains unchanged')
        require(original.preserved_pe(a.profile)==load(old/'original-Windows-PE.json'),'Actual original preserved Windows HST PE and complete provenance must reproduce')
        argv=[sys.executable,'-B','Tests/Production/RemainingVessels/rejections.py','--capture',str(capture),'--output',str(a.output/'fresh-original-audit.json')]
        with (a.output/'fresh-original-audit.log').open('w') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);code=child.wait(timeout=1800)
        report['commands'].append(dict(label='unchanged-original-independent-rejection-audit',argv=argv,actual_pid=child.pid,actual_returncode=code,log_sha256=sha(a.output/'fresh-original-audit.log')));save();require(code==0,'Unchanged original Ccc rejection audit must pass every control')
        fresh_audit=load(a.output/'fresh-original-audit.json');comparison=inputs.compare_original_audit(load(old/'original-rejections-audit.json'),fresh_audit,[v['id'] for v in frozen['exact_original_controls']]);atomic_json(a.output/'original-audit-comparison.json',comparison)
        scope=original.inspect_profile(a.profile,capture,hosted/'original-rejections-audit.json');require(scope==collection['actual_original_rejection_scope'],'Every original45-process rejection scope observation must reproduce exactly')
        require(bundle.inventory(ROOT,{ROOT/name for name in index['files']})==(index['files'],[]) and all(sha(payload/name)==value['sha256'] for name,value in members.items()),'Every original logical member, alias and published raw byte must remain unchanged after independent replay')
        require(original.conserved_sources()==frozen and source_identity()==core,'Original owning source changed during independent audit')
        report.update(status='independently-replayed-all45-original-normal-host-rejections-only',original_source=lock['source'],original_run_id=lock['run_id'],original_job_id=pin['job_id'],original_artifact=api['artifact'],original_archive_sha256=sha(a.archive),original_archive_bytes=a.archive.stat().st_size,source_api_sha256=sha(a.api),original_core_identity=core,original_raw_members=len(members),original_raw_logical_files=len(index['files']),all_original_raw_bytes_and_aliases_unchanged=True,original_capture_sha256=sha(capture),original_audit_sha256=sha(old/'original-rejections-audit.json'),fresh_original_audit_sha256=sha(a.output/'fresh-original-audit.json'),original_audit_comparison=comparison,original_SDK_operation_flags_preserved=True,original_scoped_rejections=scope,actual_original_processes=45,original_guard_records=len(captured['guarded_files_sha256']),outer_members_sha256=sha(a.output/'outer-members.json'),raw_index_sha256=sha(old/'raw-index.json'),original_capture_copy_sha256=sha(a.output/'original-capture.json'),original_published_audit_copy_sha256=sha(a.output/'original-published-audit.json'))
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
