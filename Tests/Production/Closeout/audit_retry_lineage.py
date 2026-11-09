"""Authenticate the one recorded HTTP504 failure and the exact immutable audit retry.

The attempt-one-only restorer remains unchanged. This separate contract accepts
only the actual second attempt of the same source, with its complete first failure
and every full original audit gate. It never normalizes API attempt metadata.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re

RUN=42572661826
AUDITOR='a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7'
FIRST_JOB=129013339394
RETRY_JOB=129017134966
FIRST_ARTIFACT=13653861871
FIRST_SIZE=504023
FIRST_DIGEST='27a7bb25c20f123eb43a3c29e5d9863045c91729a1016d2c56edd706f416a417'
FIRST_LOG_SIZE=80023
FIRST_LOG_DIGEST='275a70063f7f44d5663cf8fb426da9734eff78af87632841888392d5613e886f'
FIRST_LOG_TEXT_SIZE=80020
FIRST_LOG_TEXT_DIGEST='f1966b1e2e7f599db11e4531407bbd8af27d0b0752edda496a2a79336475ad3e'
BRANCH='qualification/original-source-audit-v2'
WORKFLOW='.github/workflows/phase6-original-source-audit.yml'
ARTIFACT_NAME='source-complete-original-stock-independent-audit'
FIRST_MEMBERS={'original-stock-audit/api-records.json','original-stock-audit/transport/download.json',
               'original-stock-audit-controls.json'}


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(value):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z',value),
            'Explicit actual GitHub UTC timestamp required')
    return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))


def run_identity(record,attempt,conclusion):
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),
            'Exact authorized retry repository required')
    run=record['run']
    require(type(run['id']) is int and run['id']==RUN and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and
            run['head_sha']==AUDITOR and run['head_branch']==BRANCH and run['path']==WORKFLOW and
            type(run['run_attempt']) is int and run['run_attempt']==attempt and
            run['status']=='completed' and run['conclusion']==conclusion,
            'Exact completed same-source audit attempt and conclusion required')
    return run


def step(job,name,conclusion):
    values=[value for value in job['steps'] if value['name']==name]
    require(len(values)==1 and values[0]['status']=='completed' and values[0]['conclusion']==conclusion,
            'Actual audit attempt step differs: '+name)


def job_identity(record,identity,conclusion):
    jobs=record['jobs'];require(len(jobs)==1,'Exactly one actual audit job required')
    job=jobs[0]
    require(type(job['id']) is int and job['id']==identity and job['name']=='audit' and type(job['run_id']) is int and job['run_id']==RUN and job['head_sha']==AUDITOR and
            job['head_branch']==BRANCH and job['status']=='completed' and job['conclusion']==conclusion and
            'ubuntu-24.04' in job['labels'] and 'self-hosted' not in job['labels'],
            'Exact actual standard-runner audit job required')
    require(timestamp(job['started_at'])<=timestamp(job['completed_at']),'Actual audit job interval differs')
    return job


def artifact_interval(artifact,job):
    require(timestamp(job['started_at'])<=timestamp(artifact['created_at'])<=timestamp(artifact['updated_at'])<=timestamp(job['completed_at']),
            'Artifact does not belong to the exact actual audit attempt upload interval')


def log_identity(path):
    """Accept only the two exact byte identities of this log's known UTF8 BOM transport."""
    body=Path(path).read_bytes();checksum=hashlib.sha256(body).hexdigest();elided=False
    if len(body)==FIRST_LOG_SIZE and checksum==FIRST_LOG_DIGEST:
        canonical=body
    else:
        require(len(body)==FIRST_LOG_TEXT_SIZE and checksum==FIRST_LOG_TEXT_DIGEST,
                'First job log is neither its exact original bytes nor its exact known BOM-elided text representation')
        canonical=b'\xef\xbb\xbf'+body;elided=True
        require(len(canonical)==FIRST_LOG_SIZE and hashlib.sha256(canonical).hexdigest()==FIRST_LOG_DIGEST,
                'Known text transport does not reconstruct the exact original job log')
    return canonical,dict(protocol='exact-known-first-job-log-transport-v1',observed_bytes=len(body),observed_sha256=checksum,
        original_bytes=FIRST_LOG_SIZE,original_sha256=FIRST_LOG_DIGEST,known_leading_UTF8_BOM_elision=elided,
        input_file_rewritten=False,API_attempt_or_capture_bytes_modified=False)


def validate_first_api(record,steps):
    run=run_identity(record,1,'failure');job=job_identity(record,FIRST_JOB,'failure');artifact=record['artifact']
    require(artifact['id']==FIRST_ARTIFACT and artifact['name']==ARTIFACT_NAME and artifact['expired'] is False and
            artifact['size_in_bytes']==FIRST_SIZE and artifact['digest']=='sha256:'+FIRST_DIGEST and
            artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==AUDITOR and
            artifact['workflow_run']['head_branch']==BRANCH,'Exact preserved first failed artifact required')
    for name in (*steps[:3],steps[-1]):step(job,name,'success')
    step(job,steps[3],'failure')
    for name in steps[4:-1]:step(job,name,'skipped')
    artifact_interval(artifact,job)
    return job


def validate_retry_api(record,steps):
    run=run_identity(record,2,'success');job=job_identity(record,RETRY_JOB,'success');artifact=record['artifact']
    require(type(artifact['id']) is int and artifact['id']>0 and artifact['id']!=FIRST_ARTIFACT and
            artifact['name']==ARTIFACT_NAME and artifact['expired'] is False and
            type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<256*1024**2 and
            re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and
            artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==AUDITOR and
            artifact['workflow_run']['head_branch']==BRANCH,'Exact successful same-source retry artifact required')
    for name in steps:step(job,name,'success')
    artifact_interval(artifact,job)
    return job


def inspect_first_evidence(record,archive,log,target,legacy):
    """Retain the real failed bytes; a later successful result never replaces them."""
    job=validate_first_api(record,legacy.STEPS);archive=Path(archive);log=Path(log)
    require(archive.stat().st_size==FIRST_SIZE and sha(archive)==FIRST_DIGEST,'Exact first failed API ZIP required')
    canonical,log_transport=log_identity(log);text=canonical.decode('utf-8')
    require('urllib.error.HTTPError: HTTP Error 504: Gateway Time-out' in text and
            'Tests/Production/Cockpit/frozen.py' in text,
            'Recorded initial failure was not the pinned package transport HTTP504')
    legacy.extract(archive,target)
    members=legacy.transport.legacy.inspect_archive(archive,target,FIRST_DIGEST,FIRST_SIZE)
    require(set(members)==FIRST_MEMBERS,'Preserved failed attempt must retain all and only its three original outputs')
    manifest=json.loads((target/'original-stock-audit/transport/download.json').read_text())
    recorded=json.loads((target/'original-stock-audit/api-records.json').read_text())
    require(manifest['status']=='passed' and manifest['protocol']==legacy.transport.PROTOCOL and
            manifest['source_commit']==legacy.ORIGINAL and manifest['diagnostic_only'] is False and
            manifest['phase6_complete'] is False and manifest['native_admission_qualified'] is False and
            legacy.transport.run_identity(recorded['workflow_run'],recorded['jobs'])==
            legacy.transport.run_identity(manifest['workflow_run']),
            'Actual first attempt did not bind the same complete original source/API cohort')
    legacy.bind_artifacts(recorded,recorded,manifest)
    controls=json.loads((target/'original-stock-audit-controls.json').read_text())
    require(controls['status']=='passed' and controls['producer_commit']==AUDITOR and controls['sources_match_producer'] is True and
            controls['tests_run']==176 and controls['skipped']==controls['failures']==controls['errors']==0 and
            controls['phase6_complete'] is False,'Actual first audit source-bound helper controls differ')
    return dict(protocol='phase6-exact-original-audit-retry-lineage-v1',audit_run_id=RUN,auditor_source=AUDITOR,
        first_attempt=1,first_job_id=job['id'],first_conclusion='failure',first_failure='pinned-package-download-HTTP504-before-physics',
        first_artifact_id=FIRST_ARTIFACT,first_artifact_bytes=FIRST_SIZE,first_artifact_sha256=FIRST_DIGEST,
        first_job_log_sha256=FIRST_LOG_DIGEST,first_job_log_transport=log_transport,first_decoded_members_sha256=members,
        same_original_transport_sha256=sha(target/'original-stock-audit/transport/download.json'),
        successful_attempt_required=2,successful_job_required=RETRY_JOB,
        old_failed_attempt_relabelled=False,API_attempts_normalized=False,qualification_granted=False)


def main():
    import argparse
    import os
    import subprocess
    import sys
    root=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(root/'Tests/Production/CurrentWindows/Hosted'))
    import restore_source_complete_reference as legacy
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','log','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args()
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform' and os.environ.get('ImageOS')=='ubuntu24',
            'Actual standard hosted Ubuntu24 history verification required')
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    require(head==os.environ['GITHUB_SHA'] and a.output.is_relative_to(root/'out') and not a.output.exists(),
            'Actual immutable verifier source and fresh owned history report required')
    a.output.parent.mkdir(parents=True,exist_ok=True);api_sha=sha(a.api)
    result=inspect_first_evidence(json.loads(a.api.read_text()),a.archive,a.log,a.output.parent/'first-attempt-source-artifact',legacy)
    require(sha(a.api)==api_sha and sha(a.archive)==FIRST_DIGEST and log_identity(a.log)[1]==result['first_job_log_transport'],
            'Actual immutable failed attempt API/ZIP/log changed during history verification')
    result.update(status='verified-specific-failed-audit-history-only',verifier_source=head,verifier_sha256=sha(__file__),
        first_attempt_api_sha256=api_sha,successful_full608_retry_still_required=True,
        phase6_complete=False,native_admission_qualified=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
