"""Re-read both immutable audit attempts and every retained retry input at use time."""
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,load
import audit_retry_lineage as retry
import restore_source_complete_reference as prior
import restore_source_complete_retry_reference as reference

FIXED={'reference-api/audit.json','reference-api/audit.zip','reference-api/first.json',
       'reference-api/first.zip','reference-api/first-job.log','reference-api/original.json'}


def paths(out,restored):
    members=restored['successful_audit_decoded_members_sha256']
    require(type(members) is dict and members,'Complete successful audit member closure required')
    names=FIXED|{'reference-audit-restoration/source-artifact/'+name for name in members}|{
        'reference-audit-restoration/first-attempt-source-artifact/'+name for name in retry.FIRST_MEMBERS}
    result={}
    for name in sorted(names):
        safe=str(prior.transport.legacy.safe(name));require(name==safe,'Canonical retained retry member path required')
        path=Path(out)/name
        require(path.is_file() and not path.is_symlink() and path.resolve()==path,
                'Missing or redirected retained retry input: '+name)
        result[name]=path
    return result


def inventory(out):
    restored=load(Path(out)/'reference-audit-restoration/restoration.json')
    return {name:dict(path=str(path),sha256=sha(path)) for name,path in paths(out,restored).items()}


def validate_paths(cfg,workspace):
    values=cfg['reference_retry_inputs']
    require(type(values) is dict and values,'Explicit immutable retry input inventory required')
    for name,value in values.items():
        require(type(name) is str and str(prior.transport.legacy.safe(name))==name and
                set(value)=={'path','sha256'} and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
                PureWindowsPath(value['path'])==workspace/'out'/name,
                'Retry evidence must retain its exact inherited workspace path and byte identity')


def guarded(cfg,restored=None):
    out=Path(cfg['reference_restoration']['path']).parents[1]
    if restored is None:restored=load(cfg['reference_restoration']['path'])
    expected=paths(out,restored);values=cfg['reference_retry_inputs']
    require(set(values)==set(expected),'Missing or substituted retained retry proof member')
    result={}
    for name,path in expected.items():
        require(Path(values[name]['path'])==path and sha(path)==values[name]['sha256'],
                'Actual retained audit attempt/API/ZIP/log/member changed: '+name)
        result[str(path)]=values[name]['sha256']
    return result


def verify(cfg,restored,manifest):
    protected=guarded(cfg,restored);out=Path(cfg['reference_restoration']['path']).parents[1]
    success=load(out/'reference-api/audit.json');first=load(out/'reference-api/first.json')
    reference.validate_audit_api(success);retry.validate_first_api(first,prior.STEPS)
    archive=out/'reference-api/audit.zip';decoded=out/'reference-audit-restoration/source-artifact'
    members=prior.transport.legacy.inspect_archive(archive,decoded,retry.RETRY_DIGEST,retry.RETRY_SIZE)
    require(members==restored['successful_audit_decoded_members_sha256'],
            'Actual successful audit source members differ from the full restoration receipt')
    with tempfile.TemporaryDirectory(prefix='orbiter-exact-first-audit-') as temporary:
        lineage=retry.inspect_first_evidence(first,out/'reference-api/first.zip',out/'reference-api/first-job.log',
                                           Path(temporary)/'decoded',prior)
    lineage.update(first_attempt_api_sha256=sha(out/'reference-api/first.json'),successful_attempt=2,
        successful_job_id=retry.RETRY_JOB,successful_artifact_id=retry.RETRY_ARTIFACT,
        successful_artifact_sha256='sha256:'+retry.RETRY_DIGEST)
    require(prior.transport.legacy.inspect_archive(out/'reference-api/first.zip',
            out/'reference-audit-restoration/first-attempt-source-artifact',retry.FIRST_DIGEST,retry.FIRST_SIZE)==
            lineage['first_decoded_members_sha256'],'Retained first failure members differ from the exact failed API ZIP')
    require(lineage==restored['audit_retry_lineage'] and
            lineage['same_original_transport_sha256']==sha(out/'reference-audit-restoration/source-artifact/original-stock-audit/transport/download.json')==cfg['reference_transport']['sha256'] and
            restored['source_audit_api_sha256']==sha(out/'reference-api/audit.json') and
            restored['actual_reference_api_sha256']==sha(out/'reference-api/original.json') and
            restored['original_audit_run_id']==retry.RUN and restored['original_audit_artifact_id']==retry.RETRY_ARTIFACT and
            restored['original_audit_archive_sha256']=='sha256:'+retry.RETRY_DIGEST,
            'Both real immutable audit attempts and the unchanged original cohort must match exactly')
    fresh=load(out/'reference-api/original.json');recorded=load(decoded/'original-stock-audit/api-records.json')
    require(prior.transport.run_identity(fresh['workflow_run'],fresh['jobs'])==
            prior.transport.run_identity(recorded['workflow_run'],recorded['jobs'])==prior.transport.run_identity(manifest['workflow_run']),
            'Actual complete original API/source/job identities differ')
    reference.bind_artifacts(recorded,fresh,manifest)
    require(guarded(cfg,restored)==protected,'Retry inputs changed during independent proof inspection')
    return dict(audit_retry_lineage=lineage,reference_retry_inputs_sha256={name:value['sha256'] for name,value in cfg['reference_retry_inputs'].items()},
                actual_retry_proof_inputs_independently_reverified=True)
