#!/usr/bin/env python3
"""Stream the exact successful prerequisite of the preserved failed admission run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from contracts import ROOT,PROFILES,atomic_json,require,sha
from frozen_admission_api import candidate,extract_reference,hosted

SOURCE='55a20c2b04a44ce3dad3fdddc1698549e4a8d9d0'
RUN=42923285906
JOBS={'Restore exact previously qualified API evidence':(130203235510,'success'),
      **{'Full normal stock admission '+p:(i,'failure') for p,i in zip(PROFILES,(130204658227,130204658181,130204658280,130204658226),strict=True)}}
FAILED_STEP='Verify the complete current-run reference transfer API before retaining its exact bytes'
ARTIFACT=13811569784
ZIP_BYTES=977583841
ZIP_SHA='c6825243cf603e3c347ba34882f3decedb369e44283cb918344ded8e6c1833a5'
TAR_BYTES=977582707
TAR_SHA='454b72d4d7003d582d08da294303daa3d5f64be8103df62a92080e481ad32fe2'
RECEIPT_SHA='ee87026f89231db5e03669c1776bed1a7b1812cc1ef207947e184b1f4d3f6ff8'
REPO='dcajacob/orbiter-cross-platform'
GH=['gh','api','--hostname','github.com']
API='repos/'+REPO+'/actions'


def inspect_api(run,jobs,artifact):
    require((run['id'],run['head_sha'],run['run_attempt'],run['head_branch'],run['path'],run['status'],run['conclusion'])==
            (RUN,SOURCE,1,'qualification/frozen-normal-admission-v1','.github/workflows/phase6-frozen-normal-admission.yml','completed','failure') and
            run['repository']['full_name']==REPO and run['repository']['private'] is False,'Original failed run history required')
    require(len(jobs)==len(JOBS) and {j['name'] for j in jobs}==set(JOBS),'Exact original prerequisite and four failed job identities required')
    for j in jobs:
        require((j['id'],j['conclusion'])==JOBS[j['name']] and j['run_id']==RUN and j['head_sha']==SOURCE and
                j['run_attempt']==1 and j['status']=='completed' and j['labels']==['ubuntu-24.04'],
                'Original standard runner job status differs')
        failures=[s['name'] for s in j['steps'] if s['conclusion']=='failure']
        require(failures==([FAILED_STEP] if j['conclusion']=='failure' else []),'Only original failed reference transfer jobs may be replaced')
    require((artifact['id'],artifact['name'],artifact['size_in_bytes'],artifact['digest'],artifact['expired'],
             artifact['workflow_run']['id'],artifact['workflow_run']['head_sha'])==
            (ARTIFACT,'frozen-normal-admission-reference',ZIP_BYTES,'sha256:'+ZIP_SHA,False,RUN,SOURCE),
            'Exact original successful prerequisite artifact required')


def download(folder):
    require(shutil.disk_usage(folder).free>=3*ZIP_BYTES+8*1024**3,'Exact hosted reference restore must keep the eight-GiB free reserve')
    argv=['timeout','--foreground','900',*GH,API+'/artifacts/'+str(ARTIFACT)+'/zip']
    report=dict(status='streaming-exact-previous-reference',original_run_id=RUN,artifact_id=ARTIFACT,
                expected_bytes=ZIP_BYTES,expected_sha256=ZIP_SHA,argv=argv,attempts=[],original_attempts_relabelled=False)
    report_path=folder/'streaming-download.json';atomic_json(report_path,report)
    for i in range(1,4):
        path=folder/('reference-'+str(i)+'.partial.zip');log=folder/('reference-'+str(i)+'.log');h=hashlib.sha256();length=0
        with path.open('xb') as dest,log.open('xb') as errors:
            p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=errors,cwd=ROOT)
            try:
                with p.stdout as incoming:
                    for body in iter(lambda:incoming.read(1024**2),b''):
                        dest.write(body);h.update(body);length+=len(body)
                        require(length<=ZIP_BYTES,'Actual archive exceeded exact bound; preserve partial')
            finally:
                if p.poll() is None:
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:p.kill();p.wait()
                report['attempts'].append(dict(attempt=i,actual_pid=p.pid,returncode=p.returncode,bytes=length,sha256=h.hexdigest(),log_sha256=sha(log)))
                atomic_json(report_path,report)
        if p.returncode==0:
            require(length==ZIP_BYTES and h.hexdigest()==ZIP_SHA==sha(path),'Exact previous reference archive bytes required')
            result=folder/'producer.zip';path.rename(result)
            report['status']='verified-exact-previous-reference-ZIP';atomic_json(report_path,report);return result
        require(i<3 and any('HTTP '+str(code) in log.read_text(errors='replace') for code in (502,503,504)),
                'Exact hosted transfer failed; every original partial byte and process log retained')
    raise AssertionError('Unreachable retry state')


def main():
    hosted()
    require(os.environ.get('GITHUB_REPOSITORY')==REPO,'Exact public repository required')
    lock=candidate();folder=ROOT/'out/admission-reference-source';folder.mkdir(parents=True,exist_ok=False)
    def get(path):return json.loads(subprocess.check_output([*GH,path],timeout=60))
    run=get(API+'/runs/'+str(RUN));jobs=get(API+'/runs/'+str(RUN)+'/jobs?per_page=100')['jobs'];artifact=get(API+'/artifacts/'+str(ARTIFACT))
    atomic_json(folder/'api.json',dict(run=run,jobs=jobs,artifact=artifact))
    inspect_api(run,jobs,artifact)
    archive=download(folder);target=ROOT/'out/admission-reference-download';target.mkdir()
    with zipfile.ZipFile(archive) as z:
        require(len(z.infolist())==2 and set(z.namelist())=={'reference.json','reference.tar.gz'},'Exact prior reference package members required')
        pins={'reference.tar.gz':(TAR_BYTES,TAR_SHA),'reference.json':(8192,RECEIPT_SHA)}
        for m in z.infolist():
            cap,digest=pins[m.filename]
            require(0<m.file_size<=cap and (m.filename!='reference.tar.gz' or m.file_size==cap),'Exact bounded prior inner evidence required')
            path=target/m.filename
            with z.open(m) as source,path.open('xb') as out:shutil.copyfileobj(source,out,1024**2)
            require(sha(path)==digest,'Exact previous reference inner member bytes required')
    extract_reference(lock,target,origin=(SOURCE,RUN))
    require(shutil.disk_usage(ROOT).free>=8*1024**3 and sha(archive)==ZIP_SHA,'Complete source-bound original transfer must remain intact')
    atomic_json(folder/'restored.json',dict(status='restored-exact-prior-qualified-reference',candidate_id=lock['id'],
        archive_bytes=ZIP_BYTES,archive_sha256=ZIP_SHA,archive_artifact_id=ARTIFACT,previous_source=SOURCE,
        previous_run_id=RUN,previous_actual_workflow_conclusion='failure',all_original_1125_evidence_guards_reverified=True,
        reference_qualification_repeated=False,simulator_processes=0,phase6_complete=False))


if __name__=='__main__':main()
