#!/usr/bin/env python3
"""Restore exact original evidence after the specifically verified immutable audit retry."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/RemainingStockPersistence')]
from contracts import require,sha,load
import source_complete_original_transport as transport
from audit_source_complete_original_stock import PRODUCER as ORIGINAL,PROFILES,writer_result
import restore_source_complete_reference as prior
import audit_retry_lineage as retry

AUDITOR='a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7'
STEPS=('Verify every helper and unchanged-source control',
       'Verify the actual completed original cohort and retain exact API ZIP bytes',
       'Independently bind and restore every original artifact member',
       'Stage the immutable original Debug application and SDK','Stage the immutable original Release application and SDK',
       'Stage independent exact Mesa DLLs and notices without executing Windows code',
       'Audit all original writers, exact-save reloads and direct build pairs','Run actions/upload-artifact@v7')


def validate_audit_api(record):
    return retry.validate_retry_api(record,STEPS)


def audit_receipts(manifest,writer,cohort,manifest_sha,writer_sha):
    require(manifest['status']=='passed' and manifest['protocol']==transport.PROTOCOL and manifest['source_commit']==ORIGINAL and
            manifest['phase6_complete'] is False and manifest['native_admission_qualified'] is False,'Exact original hosted cohort transport required')
    writer_result(writer,manifest_sha)
    require(cohort['protocol']=='phase6-source-complete-original-windows-persistence-audit-v2' and
            cohort['status']=='passed-source-complete-original-Windows-writer-and-exact-save-reload-audit' and
            cohort['observer_source']==ORIGINAL and cohort['auditor_source']==AUDITOR and cohort['transport_sha256']==manifest_sha and
            cohort['writer_audit_sha256']==writer_sha and cohort['actual_windows_processes']==608 and
            cohort['actual_windows_presentations']==608*960 and cohort['writer_processes']==cohort['reload_processes']==304 and
            set(cohort['profiles'])==PROFILES and set(cohort['build_pairs'])=={'automatic','sse2'} and
            cohort['phase6_complete'] is False and cohort['native_admission_qualified'] is False,
            'Complete independently audited original writer/reload and build-pair cohort required')


def bind_artifacts(recorded,fresh,manifest):
    def identities(artifacts):
        values=[transport.legacy.artifact_identity(item,manifest['workflow_run'],False) for item in artifacts]
        require(len(values)==len({v['profile'] for v in values})==len({v['id'] for v in values})==4,
                'Four distinct exact original artifact/profile identities required')
        return {item['profile']:item for item in values}
    actual=identities(fresh['artifacts'])
    require(identities(recorded['artifacts'])==actual==identities([item['api_artifact'] for item in manifest['artifacts']]) and
            set(actual)==PROFILES,'Every actual original API artifact must be the exact artifact independently audited')
    return actual


def extract(archive,target):
    require(not target.exists(),'Fresh decoded original evidence root required');target.mkdir(parents=True)
    seen=set()
    with zipfile.ZipFile(archive) as source:
        require(shutil.disk_usage(target).free>=sum(m.file_size for m in source.infolist())+8*1024**3,'Original evidence capacity and unchanged reserve required')
        for member in source.infolist():
            name=str(transport.legacy.safe(member.filename))
            require(name.casefold() not in seen and not stat.S_ISLNK(member.external_attr>>16),'Duplicate/case-colliding/symlink original evidence member')
            seen.add(name.casefold())
            if member.is_dir():continue
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            with source.open(member) as incoming,path.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('audit-api','audit-archive','reference-api'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    for name in ('first-attempt-api','first-attempt-archive','first-attempt-log'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true','Hosted reference restoration only; no local bulk transfers')
    guarded_APIs={str(path):sha(path) for path in (a.audit_api,a.reference_api,a.first_attempt_api)}
    api=load(a.audit_api);validate_audit_api(api);artifact=api['artifact']
    require(a.audit_archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(a.audit_archive)==artifact['digest'],
            'Actual independent audit API archive differs')
    base=ROOT/'out/reference-audit-restoration';require(not base.exists(),'Fresh audit source restoration required');base.mkdir(parents=True)
    first=load(a.first_attempt_api)
    lineage=retry.inspect_first_evidence(first,a.first_attempt_archive,a.first_attempt_log,base/'first-attempt-source-artifact',prior)
    lineage['first_attempt_api_sha256']=sha(a.first_attempt_api)
    payload=base/'source-artifact';extract(a.audit_archive,payload)
    original=payload/'original-stock-audit';manifest_file=original/'transport/download.json';writer_file=original/'independent/writer-audit.json'
    cohort_file=original/'independent/original-persistence-audit.json';manifest=load(manifest_file);writer=load(writer_file);cohort=load(cohort_file)
    audit_receipts(manifest,writer,cohort,sha(manifest_file),sha(writer_file))
    require(sha(manifest_file)==lineage['same_original_transport_sha256'],'The retry changed original source/API/member transport evidence')
    lineage.update(successful_attempt=api['run']['run_attempt'],successful_job_id=api['jobs'][0]['id'],successful_artifact_id=artifact['id'],successful_artifact_sha256=artifact['digest'])
    recorded=load(original/'api-records.json');fresh=load(a.reference_api)
    require(transport.run_identity(recorded['workflow_run'],recorded['jobs'])==transport.run_identity(fresh['workflow_run'],fresh['jobs'])==
            transport.run_identity(manifest['workflow_run']) and fresh['workflow_run']['id']==transport.RUN and
            fresh['workflow_run']['head_sha']==ORIGINAL,'Actual current API producer/job identities differ from the independently audited reference')
    bind_artifacts(recorded,fresh,manifest)
    destination=ROOT/'out/original-stock-audit/transport';require(not destination.exists(),'Fresh immutable original transport destination required');destination.mkdir(parents=True)
    shutil.copy2(manifest_file,destination/'download.json');decoded={}
    for item in manifest['artifacts']:
        profile=item['profile'];require(item['decoded']=='out/original-stock-audit/transport/'+profile and
            item['path']=='out/original-stock-audit/archives/'+item['name']+'.zip','Exact original repository-relative transport paths required')
        archive=ROOT/item['path'];require(archive.stat().st_size==item['bytes'] and sha(archive)==item['sha256'],'Actual retained original API ZIP differs')
        target=ROOT/item['decoded'];extract(archive,target);decoded[profile]=target
    bindings=transport.inspect_matrix(manifest,ROOT,decoded,ORIGINAL)
    require(all(binding['decoded_members_sha256']==next(a for a in manifest['artifacts'] if a['profile']==profile)['decoded_members_sha256']
                for profile,binding in bindings.items()),'Every original decoded member must retain its independent audit identity')
    for name in ('writer-audit.json','original-persistence-audit.json'):
        target=ROOT/'out/original-stock-audit/independent'/name;require(not target.exists(),'Fresh immutable reference audit receipt required');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original/'independent'/name,target)
    require(sha(destination/'download.json')==sha(manifest_file),'Original reference transport was rewritten during restoration')
    report=dict(protocol='phase6-source-complete-original-reference-retry-restoration-v3',status='restored-exact-original-cohort-after-verified-audit-retry-only',audit_retry_lineage=lineage,
        original_capture_source=ORIGINAL,original_auditor_source=AUDITOR,original_audit_run_id=api['run']['id'],
        original_audit_artifact_id=artifact['id'],original_audit_archive_sha256=artifact['digest'],
        restorer_source=os.environ['GITHUB_SHA'],actual_reference_api_sha256=sha(a.reference_api),source_audit_api_sha256=sha(a.audit_api),
        original_transport_sha256=sha(manifest_file),original_writer_audit_sha256=sha(writer_file),original_cohort_audit_sha256=sha(cohort_file),
        original_api_archive_bindings=bindings,original_windows_processes=608,current_or_native_qualification_granted=False,
        original_saves_relabelled=False,phase6_complete=False,native_admission_qualified=False)
    require(sha(a.first_attempt_archive)==retry.FIRST_DIGEST and sha(a.first_attempt_log)==retry.FIRST_LOG_DIGEST and
            all(sha(path)==value for path,value in guarded_APIs.items()) and
            transport.legacy.inspect_archive(a.first_attempt_archive,base/'first-attempt-source-artifact',retry.FIRST_DIGEST,retry.FIRST_SIZE)==lineage['first_decoded_members_sha256'],
            'Preserved first attempt or actual source API receipts changed during successful reference restoration')
    (base/'restoration.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])


if __name__=='__main__':main()
