#!/usr/bin/env python3
"""Close only the published native API subset, retaining actual source/API/member proofs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat
import zipfile
from hosted_native_package import ROOT,require,sha,load
from inspect_hosted_native_general_api import PINS,SOURCE,RUN,safe,validate_api


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and not a.output.exists(),
            'Actual hosted final native API audit and fresh output required');a.output.mkdir(parents=True)
    producer=os.environ['GITHUB_SHA'];profiles={};protected={}
    for profile,pin in PINS.items():
        base=a.inputs/profile;record=load(base/'api.json');run=record['run'];artifact=record['artifact']
        require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and
                run['id']==int(os.environ['GITHUB_RUN_ID']) and run['head_sha']==producer and run['run_attempt']==1 and
                run['head_branch']=='qualification/native-general-api-independent-v1' and
                run['path']=='.github/workflows/phase6-native-general-api-independent.yml' and
                artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==producer and
                artifact['name']=='independent-native-GeneralApi-'+profile and artifact['expired'] is False,
                'Actual same-source independent native API producer/artifact required')
        jobs=[j for j in record['jobs'] if j['name']=='Independently audit native API '+profile]
        require(len(jobs)==1 and jobs[0]['run_id']==run['id'] and jobs[0]['head_sha']==producer and
                jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and
                'ubuntu-24.04' in jobs[0]['labels'] and 'self-hosted' not in jobs[0]['labels'],'Actual passed independent profile job required')
        archive=base/'producer.zip';require(archive.stat().st_size==artifact['size_in_bytes']<16*1024**2 and
                'sha256:'+sha(archive)==artifact['digest'],'Actual independent profile proof ZIP differs')
        target=a.output/'profiles'/profile;target.mkdir(parents=True);seen=set();bodies={}
        with zipfile.ZipFile(archive) as incoming:
            require(len(incoming.infolist())<200 and sum(i.file_size for i in incoming.infolist())<32*1024**2,'Bounded complete independent profile proof required')
            for item in incoming.infolist():
                if item.is_dir():continue
                name=item.filename;safe(name);require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16),'Duplicate/case-colliding/symlink independent proof member');seen.add(name.casefold())
                path=target/name;path.parent.mkdir(parents=True,exist_ok=True);body=incoming.read(item);path.write_bytes(body);bodies[name]=hashlib.sha256(body).hexdigest()
        prefix='native-api-independent/'+profile+'/'
        report=load(target/prefix/'proof.json');raw=load(target/prefix/'raw-members.json');audit=load(target/prefix/'independent-native-api-audit.json')
        original_api=target/'native-api-published'/profile/'api.json';validate_api(load(original_api),profile)
        require(report['protocol']=='phase6-independent-published-native-GeneralApi-v1' and report['status']=='verified-published-native-GeneralApi-profile-only' and
                report['profile']==profile and report['auditor_source']==producer and report['original_collector_source']==SOURCE and
                report['original_run_id']==RUN and (report['original_job_id'],report['original_artifact_id'],report['original_archive_bytes'],report['original_archive_sha256'])==pin and
                report['actual_processes']==2 and report['reexecuted_original_audit_same_bytes'] is True and
                report['all_original_source_runtime_provider_and_evidence_bytes_unchanged'] is True and
                report['qualification_granted'] is False and report['complete_general_api_qualification'] is False and
                report['normal_admission_qualified'] is False and report['phase6_complete'] is False,'Complete independent native-only profile proof required')
        require(report['source_api_sha256']==sha(original_api) and report['actual_raw_member_count']==len(raw) and
                report['actual_raw_decoded_bytes']==sum(i['bytes'] for i in raw.values()) and
                report['raw_members_sha256']==sha(target/prefix/'raw-members.json') and
                report['independent_audit_sha256']==report['original_audit_sha256']==sha(target/prefix/'independent-native-api-audit.json'),
                'Exact raw/API/original/recomputed audit byte closure differs')
        identity=audit['runtime_identity'];require(audit['status']=='passed-native-api-script-diagnostic-only' and
                identity['runtime_source_commit']=='ccc02c8a34bd1f227624d8778a141e8736ae8111' and identity['profile']==profile and
                identity['sanitizer_linked'] is True and audit['startup_exit_policy_audited'] is True and
                audit['normal_admission_qualified'] is False and audit['phase6_complete'] is False,'Actual sanitized native API identity/startup scope differs')
        for variant,count in (('original',10),('corrected',11)):
            process=report['original_pid_receipts'][variant];observed=audit['observed'][variant]
            require(process['actual_collector_pid']==observed['actual_pid']>0 and process['actual_returncode']==0 and
                    process['cancelled'] is False and process['terminal'] is True and
                    observed['returncode']==0 and observed['completed_pass_markers']==count,'Actual original/corrected native process/assertion result differs')
        startup=audit['observed']['corrected']['startup_exit'];require(startup['existing_save_preserved'] is True and startup['assertion_passes']==11 and
                startup['completed_frames']==0 and startup['finalized_ticks']==1,'Specific corrected API startup-exit result differs')
        (target/'producer-api.json').write_bytes((base/'api.json').read_bytes())
        profiles[profile]=dict(original_capture_source=SOURCE,original_capture_run_id=RUN,original_capture_artifact_id=pin[1],
            independent_job_id=jobs[0]['id'],independent_artifact=artifact,actual_processes=2,observed=audit['observed'],
            proof_member_sha256=bodies,actual_raw_member_count=len(raw),actual_raw_decoded_bytes=report['actual_raw_decoded_bytes'])
        protected.update({str(path.relative_to(a.output)):sha(path) for path in target.rglob('*') if path.is_file()})
    sources={}
    for folder in ('Tests/Production/Closeout','Tests/Production/GeneralApiCorrection'):
        for path in sorted((ROOT/folder).rglob('*.py')):
            relative=path.relative_to(ROOT).as_posix();body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+relative])
            require(path.read_bytes()==body,'Actual immutable native API audit source changed');sources[relative]=sha(path)
    require(set(profiles)==set(PINS) and all(sha(a.output/name)==value for name,value in protected.items()),'Complete native API four-profile proof changed')
    report=dict(protocol='phase6-independent-published-native-GeneralApi-matrix-v1',status='verified-complete-native-GeneralApi-subset-only',
        auditor_source=producer,github_run_id=int(os.environ['GITHUB_RUN_ID']),github_run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),
        profiles=profiles,actual_original_and_corrected_processes=8,source_sha256=sources,proof_member_sha256=protected,
        every_original_assertion_startup_policy_sanitizer_and_failure_preserved=True,
        windows_API_reference_and_joint_qualification_pending=True,full157_admission_pending=True,
        qualification_granted=False,complete_general_api_qualification=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    (a.output/'proof.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])


if __name__=='__main__':main()
