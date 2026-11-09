#!/usr/bin/env python3
"""Independently restore and re-audit the exact published four-profile native API bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import sys
from hosted_native_package import ROOT,require,sha,load
import hosted_native_general_api as api

SOURCE='a75157bdec9f49b17da6ca04eb57699e16c87e8a'
RUN=42701960873
PINS={
 'Debug-automatic':(129448961099,13712350791,320264924,'388805482645bddfa827f57cd33e79dc2d5aae8c540bbb6b1128dff5595ab072'),
 'Debug-sse2':(129448960890,13712865162,320241034,'f74c4129d8bc4da547a8efcff7ff86d1564453d519fc8a1ec60f5c30abb15345'),
 'Release-automatic':(129448960802,13713145583,320274510,'641aa84ab0ad6a98cf495178738bab07324581de340c0843f7ca4d4848e8a860'),
 'Release-sse2':(129448960799,13712112855,320250511,'edefd3fd32ad99e441911fdc2e54aa601ae9b7d36f46dc53a0b2b3f5e1fdc7d1')}


def validate_api(record,profile):
    require(profile in PINS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact authorized native API profile/repository required')
    run=record['run'];artifact=record['artifact'];job_id,ident,size,digest=PINS[profile]
    require(run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/native-general-api-v2' and
            run['path']=='.github/workflows/phase6-native-general-api.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Exact complete actual native API producer required')
    require(artifact['id']==ident and artifact['name']=='native-GeneralApi-'+profile and artifact['size_in_bytes']==size and
            artifact['digest']=='sha256:'+digest and artifact['expired'] is False and
            artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE,'Exact published native API artifact identity required')
    jobs=record['jobs'];require(len(jobs)==5 and len({j['id'] for j in jobs})==5,'Complete actual API producer job roster required')
    expected={129448700566:'readiness',**{pin[0]:'Native original and corrected API '+p.replace('-',' ',1) for p,pin in PINS.items()}}
    for job in jobs:
        require(job['id'] in expected and job['name']==expected[job['id']] and job['run_id']==RUN and job['head_sha']==SOURCE and
                job['status']=='completed' and job['conclusion']=='success' and 'ubuntu-24.04' in job['labels'] and
                'self-hosted' not in job['labels'],'Every actual completed standard-runner API producer required')
    return next(j for j in jobs if j['id']==job_id)


def safe(name):
    value=PurePosixPath(name)
    require(name and str(value)==name and not value.is_absolute() and '..' not in value.parts and
            ':' not in name and '\\' not in name,'Unsafe native API evidence member')
    return value


def restore_archive(archive,destination,profile,owner):
    import zipfile
    archive=Path(archive);destination=Path(destination);owner=Path(owner)
    require(not destination.exists(),'Fresh original native API member restoration required');destination.mkdir(parents=True)
    selected='native-general-api-capture/'+profile+'/'
    resources={'native-stock-assets/'+n for n in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json')}
    files={};seen=set();materialized={}
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist();require(len(entries)<50000 and sum(i.file_size for i in entries)<4*1024**3,'Bounded complete native API archive required')
        for item in entries:
            name=item.filename.rstrip('/') if item.is_dir() else item.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,
                    'Duplicate, redirected or privileged native API member')
            seen.add(name.casefold())
            if item.is_dir():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);body=incoming.read(item);target.write_bytes(body)
            files[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
            if name.startswith(selected) or name in resources:
                actual=owner/'out'/name;actual.parent.mkdir(parents=True,exist_ok=True)
                require(actual.parent.resolve()==actual.parent and not actual.exists() and not actual.is_symlink(),'Original API restoration would replace or redirect evidence')
                os.link(target,actual);materialized[str(actual)]=files[name]['sha256']
    require(selected+'diagnostic.json' in files and resources<=set(files) and materialized,'Complete actual capture and unchanged resource manifests required')
    require(all(sha(destination/name)==item['sha256'] for name,item in files.items()) and
            all(sha(path)==value for path,value in materialized.items()),'Actual restored native API members changed')
    return files,materialized


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=sorted(PINS),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Independent audit must execute on the actual hosted Linux workspace')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh hosted independent API proof required');a.output.mkdir(parents=True)
    report=dict(protocol='phase6-independent-published-native-GeneralApi-v1',status='running',profile=a.profile,
        auditor_source=os.environ['GITHUB_SHA'],original_collector_source=SOURCE,original_run_id=RUN,
        qualification_granted=False,complete_general_api_qualification=False,normal_admission_qualified=False,phase6_complete=False)
    def save():(a.output/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        record=load(a.api);job=validate_api(record,a.profile);job_id,ident,size,digest=PINS[a.profile]
        require(a.archive.stat().st_size==size and sha(a.archive)==digest,'Actual published native API ZIP digest/length differs')
        original=a.output/'original-artifact';files,materialized=restore_archive(a.archive,original,a.profile,ROOT)
        report.update(original_job_id=job_id,original_artifact_id=ident,original_archive_bytes=size,original_archive_sha256=digest,
                      actual_raw_member_count=len(files),actual_raw_decoded_bytes=sum(i['bytes'] for i in files.values()),
                      source_api_sha256=sha(a.api));save()
        (a.output/'raw-members.json').write_text(json.dumps(files,indent=2)+'\n')
        capture=ROOT/'out/native-general-api-capture'/a.profile
        collection=load(original/'hosted-native-api'/a.profile/'collection.json')
        old_audit=original/'hosted-native-api'/a.profile/'independent-native-api-audit.json'
        require(collection['protocol']=='phase6-hosted-native-general-api-v1' and
                collection['status']=='captured-and-independently-audited-native-GeneralApi-diagnostics-only' and
                collection['collector_source']==SOURCE and collection['compiled_runtime_source']==api.RUNTIME and
                collection['profile']==a.profile and collection['actual_processes']==2 and collection['phase6_complete'] is False and
                collection['complete_general_api_qualification'] is False,'Actual complete original API-only collection required')
        require(collection['actual_api_results']['capture_sha256']==sha(capture/'diagnostic.json') and
                collection['actual_api_results']['independent_audit_sha256']==sha(old_audit),'Original collection/capture/audit byte binding differs')
        diagnostic=load(capture/'diagnostic.json')
        require(diagnostic['producer_commit']==SOURCE and diagnostic['normal_admission_qualified'] is False and
                diagnostic['phase6_complete'] is False,'Actual original producer must not be relabelled')
        source_proof=api.source_identity()
        require(collection['source_identity']['collector_source']==SOURCE and
                collection['source_identity']['complete_locked_source_count']==623 and
                collection['source_identity']['locked_source_paths_sha256']==source_proof['locked_source_paths_sha256'] and
                collection['source_identity']['original_api_sources_sha256']==source_proof['original_api_sources_sha256'],
                'Original complete core and API source identity differs')
        for item in collection['commands']:
            require(item['actual_returncode']==0 and item['actual_pid']>0 and not item.get('timed_out',False) and
                    sha(original/'hosted-native-api'/a.profile/(item['label']+'.log'))==item['log_sha256'],
                    'Actual completed collection process/log receipt differs')
        require((original/'phase6-hosted-native'/a.profile/'build.json').read_bytes()==(ROOT/'out/phase6-hosted-native'/a.profile/'build.json').read_bytes(),'Captured and independently restored compiled package manifests differ')
        original_audit=load(old_audit)
        require(all(sha(path)==value for path,value in original_audit['evidence_sha256'].items()),'Every original audit source/provider/runtime/raw evidence byte must still match')
        script=ROOT/'Tests/Production/GeneralApiCorrection/audit_native.py'
        require(script.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+script.relative_to(ROOT).as_posix()]),
                'Original native API auditor body changed')
        output=a.output/'independent-native-api-audit.json';argv=[sys.executable,'-B',str(script),'--capture',str(capture),
            '--owner',str(ROOT),'--variant-version','v2','--output',str(output)]
        with (a.output/'independent-audit.log').open('w') as log:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT);report['audit_process']=dict(argv=argv,actual_pid=child.pid);save()
            try:report['audit_process']['actual_returncode']=child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                child.kill();report['audit_process'].update(actual_returncode=child.wait(),timed_out=True);raise
        report['audit_process']['log_sha256']=sha(a.output/'independent-audit.log')
        require(report['audit_process']['actual_returncode']==0,'Independent original native API reader failed')
        require(output.read_bytes()==old_audit.read_bytes(),'Independent original auditor result must reproduce every original evidence field and byte')
        actual=api.inspect_audit(capture,output,a.profile)
        require(all(sha(original/name)==item['sha256'] for name,item in files.items()) and
                all(sha(path)==value for path,value in materialized.items()),'Restored original member changed during independent audit')
        report.update(status='verified-published-native-GeneralApi-profile-only',actual_processes=actual['actual_processes'],
            original_pid_receipts={v:diagnostic['cases'][v]['process'] for v in ('original','corrected')},
            original_audit_sha256=sha(old_audit),independent_audit_sha256=sha(output),reexecuted_original_audit_same_bytes=True,
            raw_members_sha256=sha(a.output/'raw-members.json'),original_collection_sha256=sha(original/'hosted-native-api'/a.profile/'collection.json'),
            all_original_source_runtime_provider_and_evidence_bytes_unchanged=True,windows_reference_and_joint_qualification_pending=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
