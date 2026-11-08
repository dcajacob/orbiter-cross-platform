#!/usr/bin/env python3
"""Restore the exact passive observer against its separately reverified immutable SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PureWindowsPath
import shutil
import subprocess
import sys
from restore_sdk import ROOT,PRODUCER as APPLICATION,unpack,require,sha

RUN=42529727362
PRODUCER='348880c447f8d86beb75a92ec4aaf23d44df6500'
PINS={'Debug':(13637186106,1456611,'72147583cd6598216b8da351b8128758437696359efff1bc48a954df5902d81f',128881146142),
      'Release':(13635944416,1399859,'d5f8a939957f76f2882df53b9f8d6331b0c2f7ca930218934d998fd6bcac3957',128881146178)}
STEPS=('Restore every exact SDK member and independently re-read all original source and unit receipts',
       'Verify the same immutable application and SDK from their separate source checkout',
       'Build the unchanged passive 960-tick stock observer against that exact SDK','Run actions/upload-artifact@v7')


def validate_api(record,configuration):
    require(configuration in PINS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact observer repository/configuration required')
    run=record['run'];artifact=record['artifact'];ident,size,digest,jobid=PINS[configuration]
    require(run['id']==RUN and run['head_sha']==PRODUCER and run['head_branch']=='qualification/current-stock-preparation' and
            run['path']=='.github/workflows/phase6-current-stock-preparation.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Exact completed passive observer producer required')
    require(artifact['id']==ident and artifact['name']=='current-stock-preparation-'+configuration and artifact['expired'] is False and
            artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and artifact['workflow_run']['id']==RUN and
            artifact['workflow_run']['head_sha']==PRODUCER,'Exact closed passive observer artifact required')
    jobs=[job for job in record['jobs'] if job['id']==jobid]
    require(len(jobs)==1,'Unique actual passive observer job required');job=jobs[0]
    require(job['name']=='Prepare exact current SDK and passive stock observer '+configuration and job['run_id']==RUN and
            job['head_sha']==PRODUCER and job['status']=='completed' and job['conclusion']=='success' and 'windows-2025' in job['labels'],
            'Actual successful standard Windows observer job required')
    for name in STEPS:
        steps=[s for s in job['steps'] if s['name']==name]
        require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','Original observer producer step differs: '+name)
    controls=[j for j in record['jobs'] if j['id']==128881042657]
    require(len(controls)==1 and controls[0]['run_id']==RUN and controls[0]['head_sha']==PRODUCER and
            controls[0]['status']=='completed' and controls[0]['conclusion']=='success','Original successful source-conservation controls required')
    return job


def verify_variant(original,compiled,variant):
    body=original.replace(b'\r\n',b'\n');anchor=b'require(frames==60,"Incomplete original stock observation")'
    require(body.count(anchor)==1 and compiled==body.replace(anchor,b'require(frames==960,"Incomplete repaired stock observation")') and
            variant['compiled_sha256']==hashlib.sha256(compiled).hexdigest() and
            variant['only_change']=='Validate 960 finalized ticks instead of 60; all observation calls and delays unchanged',
            'Restored passive stock observer differs beyond the original 960-tick assertion')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','source-owner'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=sorted(PINS),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual standard GitHub Windows observer restoration required')
    api=json.loads(a.api.read_text());job=validate_api(api,a.configuration);ident,size,digest,_=PINS[a.configuration]
    require(a.archive.stat().st_size==size and sha(a.archive)==digest,'Actual passive observer API ZIP differs')
    base=ROOT/'out/current-observer-restoration';target=ROOT/'out/current-stock-preparation'
    require(not base.exists() and not target.exists(),'Fresh observer restoration and preparation destinations required');base.mkdir(parents=True)
    payload=base/'source-artifact';outer=unpack(a.archive,payload)
    sdk=ROOT/'out/current-windows-sdk';restored=json.loads((sdk/'restoration.json').read_text());runtime=Path(restored['runtime'])
    require(restored['status']=='restored-and-verified-current-sdk-only' and restored['compiled_source']==APPLICATION and
            restored['configuration']==a.configuration and Path(restored['source_owner'])==a.source_owner and
            subprocess.check_output(['git','-C',str(a.source_owner),'rev-parse','HEAD'],text=True).strip()==APPLICATION,
            'Separately restored and independently verified exact current SDK/source owner required')
    guards=restored['runtime_files_sha256'];require(all(sha(runtime/name)==value for name,value in guards.items()),'Current SDK changed before observer restoration')
    original=payload/'current-stock-preparation';prep=json.loads((original/'preparation.json').read_text())
    require(prep['protocol']=='phase6-github-current-stock-preparation-v1' and prep['status']=='prepared-current-SDK-passive-stock-observer-only' and
            prep['collector_source']==PRODUCER and prep['compiled_application_source']==prep['observer_source']==APPLICATION and
            prep['configuration']==a.configuration and prep['owning_runtime_and_sources_unchanged'] is True and
            prep['stock_simulation_executed'] is False and prep['phase6_complete'] is False and prep['native_admission_qualified'] is False and
            prep['command']['actual_pid']>0 and prep['command']['actual_returncode']==0 and
            prep['command']['log_sha256']==sha(original/'observer-prepare.log'),'Original closed passive preparation receipt differs')
    shutil.copytree(original,target);work=target/'observer';built=json.loads((work/'observer-build.json').read_text());observer=built['observer']
    require(built['status']=='prepared-passive-observer-only' and observer['kind']=='remaining-stock' and
            observer['configuration']==a.configuration and observer['source_commit']==observer['sdk_source_commit']==APPLICATION and
            built['source_commit']==APPLICATION and PureWindowsPath(built['source'])==PureWindowsPath(str(a.source_owner)) and
            PureWindowsPath(observer['binary'])==PureWindowsPath(str(work/'ProductionCockpitDriver.dll')) and
            sha(work/'observer-build.json')==prep['observer_build_sha256'] and sha(work/'ProductionCockpitDriver.dll')==observer['sha256']==prep['observer_binary_sha256'] and
            built['sdk']['manifest_sha256']==prep['sdk_manifest_sha256']==sha(runtime/'test-runtime.json'),
            'Actual restored passive observer source/binary/SDK identity differs')
    fixture=a.source_owner/'Tests/Production/RemainingStock/Driver.cpp'
    verify_variant(fixture.read_bytes(),(work/'Driver-960.cpp').read_bytes(),built['observer_source_variant'])
    require(sha(target/'application-build.json')==prep['application_build_sha256']==restored['original_build_manifest_sha256'],
            'Prepared application roles differ from the separately verified exact SDK')
    require(all(sha(runtime/name)==value for name,value in guards.items()) and
            all(sha(payload/name)==value for name,value in outer.items()),'Original SDK or preparation evidence changed during restoration')
    members={path.relative_to(target).as_posix():sha(path) for path in target.rglob('*') if path.is_file()}
    require(all(sha(original/name)==value for name,value in members.items()),'Every restored preparation byte must retain its original identity')
    report=dict(protocol='phase6-github-passive-stock-observer-restoration-v1',status='restored-original-passive-observer-only',
        compiled_application_source=APPLICATION,compiled_observer_source=APPLICATION,original_preparation_source=PRODUCER,
        restorer_source=os.environ['GITHUB_SHA'],configuration=a.configuration,original_run_id=RUN,original_job_id=job['id'],
        original_artifact_id=ident,original_api_archive_sha256=digest,source_api_sha256=sha(a.api),sdk_restoration_sha256=sha(sdk/'restoration.json'),
        observer_manifest_sha256=sha(work/'observer-build.json'),observer_binary_sha256=observer['sha256'],restored_files_sha256=members,
        observer_rebuilt=False,stock_simulation_executed=False,phase6_complete=False,native_admission_qualified=False)
    (base/'restoration.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])


if __name__=='__main__':main()
