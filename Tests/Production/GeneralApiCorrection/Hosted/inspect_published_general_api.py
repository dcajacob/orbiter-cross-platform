#!/usr/bin/env python3
"""Re-read published Windows audits and original raw cases on a separate hosted runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PureWindowsPath
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import require,sha,load,APPLICATION
import audit_hosted_general_api as audit
import replay_published_general_api as replay
import restore_sdk

AUDITOR='ee3c61df1a5f829485aba7cf7517ea08a3f0861c'
AUDIT_RUN=42719673631
WORKSPACE=PureWindowsPath('D:/a/orbiter-cross-platform/orbiter-cross-platform')
PUBLISHED_PINS={'Debug': (129510432132, 13720470280, 2052096, '6526027f41fb49c9522c7fd1c82baee011db2043c628008737c0b6075c15f13e'), 'Release': (129510432125, 13718879679, 1890617, 'f53c525b0e33d2f48ff340ce68648e70626a36c315f47e7d2921f4d448653df4')}


def validate_api(record,configuration):
    require(configuration in replay.PINS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact published audit repository/configuration required')
    run=record['run'];artifact=record['artifact']
    require(run['id']==AUDIT_RUN and run['head_sha']==AUDITOR and run['head_branch']=='qualification/current-windows-general-api-reaudit-v3' and
            run['path']=='.github/workflows/phase6-current-windows-general-api-reaudit.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Exact complete successful read-only audit run required')
    require(artifact['name']=='published-Windows-GeneralApi-reaudit-'+configuration and artifact['expired'] is False and
            artifact['workflow_run']['id']==AUDIT_RUN and artifact['workflow_run']['head_sha']==AUDITOR and
            0<artifact['size_in_bytes']<16*1024**2 and len(artifact['digest'])==71 and artifact['digest'].startswith('sha256:'),
            'Actual bounded source-bound Windows audit artifact required')
    expected_job,ident,size,digest=PUBLISHED_PINS[configuration]
    require((artifact['id'],artifact['size_in_bytes'],artifact['digest'])==(ident,size,'sha256:'+digest),
            'Exact actually published Windows audit artifact id/length/digest required')
    jobs=record['jobs'];require(len(jobs)==3 and len({j['id'] for j in jobs})==3 and
            {j['name'] for j in jobs}=={'readiness','Reaudit existing Windows API Debug','Reaudit existing Windows API Release'},
            'Complete exact read-only audit job roster required')
    for job in jobs:
        label='ubuntu-24.04' if job['name']=='readiness' else 'windows-2025'
        require(job['run_id']==AUDIT_RUN and job['head_sha']==AUDITOR and job['status']=='completed' and job['conclusion']=='success' and
                label in job['labels'] and 'self-hosted' not in job['labels'],'All actual standard-runner read-only jobs must pass')
    selected=next(j for j in jobs if j['name']=='Reaudit existing Windows API '+configuration)
    require(selected['id']==expected_job,'Exact actually completed Windows audit job required')
    return selected


def evidence_path(name,published,sdk_payload,sdk_runtime,sdk_outer):
    path=PureWindowsPath(name)
    require(path.is_absolute() and '..' not in path.parts and path.is_relative_to(WORKSPACE/'out'),'Original evidence path outside its explicit Windows workspace')
    relative=path.relative_to(WORKSPACE/'out').as_posix()
    aliases={'current-sdk-source/producer.zip':sdk_outer,'current-windows-sdk/source-artifact/runtime.zip':sdk_payload/'runtime.zip',
             'current-windows-sdk/runtime/test-runtime.json':sdk_runtime/'test-runtime.json'}
    return aliases.get(relative,published/relative)



def immutable_sdk_sources():
    # Recompute the original C08 owner's complete canonical source vector directly
    # from immutable Git blobs; no current-working-tree substitution is permitted.
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',APPLICATION],text=True).splitlines()
    result={}
    with subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as reader:
        for name in names:
            restore_sdk.safe(name);reader.stdin.write((APPLICATION+':'+name+'\n').encode());reader.stdin.flush()
            header=reader.stdout.readline().split()
            require(len(header)==3 and header[1]==b'blob','Immutable compiled SDK source blob missing')
            body=reader.stdout.read(int(header[2]));require(reader.stdout.read(1)==b'\n','Incomplete immutable SDK source blob')
            result[name]=hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()
        reader.stdin.close();require(reader.wait()==0,'Immutable SDK source batch reader failed')
    require(result,'Complete immutable compiled SDK source vector required')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=sorted(replay.PINS),required=True)
    p.add_argument('--output',type=lambda v:Path(v).resolve(),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists(),'Fresh actual hosted Linux publication audit required')
    a.output.mkdir(parents=True);configuration=a.configuration;cell=configuration+'-GeneralApi'
    retained=a.output/'proof';retained.mkdir()
    progress=dict(protocol='phase6-Windows-GeneralApi-publication-progress-v1',configuration=configuration,
        auditor_source=os.environ['GITHUB_SHA'],status='running',completed_stages=[],
        new_simulator_processes_launched=0,qualification_granted=False,phase6_complete=False)
    def completed(stage):
        progress['completed_stages'].append(stage)
        (retained/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    completed('initialized-fresh-read-only-output')
    base=ROOT/'out/published-Windows-api-audit'/configuration;record=load(base/'api.json');job=validate_api(record,configuration)
    archive=base/'producer.zip';artifact=record['artifact']
    require(archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],'Published audit ZIP length/digest differs')
    published=a.output/'published-artifact';published_files=replay.unpack_capture(archive,published)
    original_base=ROOT/'out/published-Windows-api-source'/configuration
    original_api=load(original_base/'api.json');replay.validate_capture_api(original_api,configuration)
    old_archive=original_base/'producer.zip';old_pin=replay.PINS[configuration]
    require(old_archive.stat().st_size==old_pin[2] and sha(old_archive)==old_pin[3],'Original actually failed capture ZIP differs')
    original=a.output/'original-artifact';raw_files=replay.unpack_capture(old_archive,original)
    materialization=load(published/'published-Windows-api-source'/configuration/'materialization.json')
    require(materialization['status']=='restored-exact-original-observations-for-read-only-audit' and
            materialization['raw_member_sha256']==raw_files==materialization['materialized_member_sha256'] and
            materialization['original_capture_source']==replay.CAPTURE_SOURCE and materialization['original_run_id']==replay.CAPTURE_RUN and
            materialization['auditor_source']==AUDITOR and materialization['auditor_run_id']==AUDIT_RUN and
            materialization['old_failed_run_status_preserved'] is True and materialization['new_simulator_processes_launched']==0 and
            materialization['actual_original_member_count']==len(raw_files),'Exact complete original raw member materialization required')
    (retained/'original-raw-members.json').write_text(json.dumps(raw_files,indent=2)+'\n')
    (retained/'published-audit-members.json').write_text(json.dumps(published_files,indent=2)+'\n')
    completed('both-exact-raw-ZIPs-and-complete-materialization-re-read')
    shared=set(raw_files)&set(published_files)
    require(shared and all(raw_files[n]==published_files[n] for n in shared),'A republished original capture member changed')
    report_path=published/'Windows-api-published-reaudit'/cell/'audit.json';report=load(report_path)
    require(report['status']=='passed-current-Windows-api-diagnostic-only' and report['configuration']==configuration and
            report['profiles']==[configuration+'-'+m for m in ('automatic','sse2')] and report['actual_processes']==8 and
            report['github']['collector_commit']==replay.CAPTURE_SOURCE and report['github']['run_id']==replay.CAPTURE_RUN and
            report['auditor_source']==AUDITOR and report['auditor_github_run_id']==AUDIT_RUN and report['published_capture_reaudit'] is True and
            report['new_simulator_processes_launched']==0 and report['original_case_auditor_body_unchanged'] is True and
            report['original_actual_case_auditor_sha256_lf']==audit.LEGACY_SHA256_LF and
            report['original_raw_captured_input_bytes_preserved'] is True and report['normal_admission_qualified'] is False and
            report['complete_general_api_qualification'] is False and report['phase6_complete'] is False,'Complete separately identified Windows actual-case audit required')
    sdk_base=ROOT/'out/current-sdk-source';restore_sdk.validate_api(load(sdk_base/'api.json'),configuration)
    _,size,digest=restore_sdk.PINS[configuration];sdk_outer=sdk_base/'producer.zip'
    require(sdk_outer.stat().st_size==size and sha(sdk_outer)==digest,'Exact C08 SDK outer archive differs')
    sdk_payload=a.output/'sdk-source-artifact';restore_sdk.unpack(sdk_outer,sdk_payload)
    build=load(sdk_payload/'current-application.json');item=build['configurations'][configuration];inner=sdk_payload/'runtime.zip'
    require(sha(inner)==build['runtime_archive_sha256'] and inner.stat().st_size==build['runtime_archive_bytes'] and
            build['source_commit']==APPLICATION and build['owning_sources_unchanged'] is True,'Exact original SDK inner seal/source differs')
    require(immutable_sdk_sources()==build['source_guard_sha256_lf'],'Every original compiled SDK owning source hash must equal its immutable Git blob')
    sdk_runtime=a.output/'sdk-runtime';restore_sdk.unpack(inner,sdk_runtime,item['runtime_files_sha256'])
    body,sealed=audit.inspect_hosted_sdk_members(inner,sdk_runtime,item,item['sdk_manifest_sha256'])
    from retain_hosted_sdk import unit_result
    require(unit_result(load(sdk_payload/'registered-tests.json'),sdk_payload/'runtime-ctest.xml')==item['tests'] and
            item['tests']['executed_processes']==28,'Every original Windows unit receipt required')
    completed('complete-original-SDK-seal-and-all28-unit-receipts-re-read')
    verified_evidence={}
    for name,value in report['evidence_sha256'].items():
        target=evidence_path(name,published,sdk_payload,sdk_runtime,sdk_outer)
        require(target.is_file() and not target.is_symlink() and sha(target)==value,'Published protected evidence byte differs: '+name)
        verified_evidence[name]=value
    completed('every-published-protected-evidence-byte-matches')
    cfg=load(original/'current-api-requests'/cell/'request.json');worker=load(original/'current-api-requests'/cell/'worker-result.json')
    observer=load(original/'current-api-observer'/configuration/'observer-build.json')['observer']
    export=original/'current-api-exports'/cell
    require(worker['actual_processes']==8 and worker['roles']==cfg['roles']==report['roles'] and
            set(worker['export_files_sha256'])=={x.relative_to(export).as_posix() for x in export.rglob('*') if x.is_file()} and
            all(sha(export/n)==v for n,v in worker['export_files_sha256'].items()),'Every original exported actual case byte required')
    cases=audit.inspect_cases(cfg,worker,export,observer,published/'Windows-api-canonical-inputs'/configuration)
    require(cases==report['results'],'Independent original case assertions must reproduce the actual Windows audit results')
    identities=report['original_case_reader_inputs']
    require(set(identities)=={audit.ORIGINAL,audit.EARTH,'Scenarios/Tests/GeneralApiTest.scn'},'Complete locked API reader input closure required')
    for name in identities:
        source=subprocess.check_output(['git','-C',str(ROOT),'show',APPLICATION+':'+name]).replace(b'\r\n',b'\n')
        require(sha(published/'Windows-api-canonical-inputs'/configuration/name)==hashlib.sha256(source).hexdigest()==
                identities[name]['canonical_source_sha256_lf'],'Exact immutable canonical case input differs')
    compiled=report['compiled_observer_source_identity'];immutable=subprocess.check_output(['git','-C',str(ROOT),'show',APPLICATION+':Tests/Production/GeneralApiCorrection/Observer.cpp'])
    raw_source=replay.exact_source_bytes(immutable,observer['source_sha256'])
    require(audit.inspect_compiled_source(raw_source,immutable,observer['source_sha256'],build['source_guard_sha256_lf']['Tests/Production/GeneralApiCorrection/Observer.cpp'])==compiled,
            'Original observer raw and canonical source identities differ')
    completed('unchanged-original-case-body-and-nested-startup-policy-reproduced')
    sources={}
    for folder in ('Tests/Production/GeneralApiCorrection','Tests/Production/Closeout'):
        for source in sorted((ROOT/folder).rglob('*.py')):
            relative=source.relative_to(ROOT).as_posix();body=subprocess.check_output(['git','-C',str(ROOT),'show',os.environ['GITHUB_SHA']+':'+relative])
            require(source.read_bytes()==body,'Actual publication auditor source changed');sources[relative]=sha(source)
    for source,name in ((report_path,'original-Windows-audit.json'),(base/'api.json','read-only-audit-api.json'),
                        (original_base/'api.json','original-failed-capture-api.json'),(sdk_base/'api.json','sdk-api.json')):
        shutil.copy2(source,retained/name)
    proof=dict(protocol='phase6-independent-published-Windows-GeneralApi-v1',status='verified-published-Windows-GeneralApi-configuration-only',
        configuration=configuration,profiles=report['profiles'],actual_original_processes=8,
        auditor_source=os.environ['GITHUB_SHA'],auditor_run_id=int(os.environ['GITHUB_RUN_ID']),
        original_capture_source=replay.CAPTURE_SOURCE,original_capture_run_id=replay.CAPTURE_RUN,original_capture_conclusion='failure',
        original_capture_artifact_id=old_pin[1],original_capture_archive_sha256=old_pin[3],
        actual_original_raw_members=raw_files,actual_published_audit_members=published_files,
        read_only_auditor_source=AUDITOR,read_only_audit_run_id=AUDIT_RUN,read_only_audit_job_id=job['id'],read_only_audit_artifact=artifact,
        original_actual_case_assertions_reexecuted_unchanged=True,actual_case_results=cases,
        all_published_protected_evidence_sha256=verified_evidence,compiled_observer_source_identity=compiled,
        original_SDK_all_member_and_28_unit_receipts_reverified=True,source_sha256=sources,
        retained_receipt_sha256={x.name:sha(x) for x in retained.iterdir()},
        no_new_simulator_processes=True,new_simulator_processes_launched=0,
        joint_GeneralApi_qualification_pending=True,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    (retained/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');progress['status']='passed-complete-read-only-publication-audit';completed('complete-independent-configuration-proof');print(proof['status'])


if __name__=='__main__':main()
