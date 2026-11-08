#!/usr/bin/env python3
"""Restore an API-bound current SDK with its original immutable owning source."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PureWindowsPath
import re
import stat
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows'))
from retain_hosted_sdk import require,sha,safe

PRODUCER='c08f93151827949ee3ad498f8021f35c11753fde'
RUN=42525562745
PINS={'Debug':(13636121355,302580954,'92feab053d8120c90f0abdfa0e90b7466fcfb0c7833b610245d4e90323ad0419'),
      'Release':(13635896646,207768498,'079b7ad0c06dd66454a9a60697670bee370fbcca0e040a4d877e934d952dd206')}
REQUIRED_STEPS=('Rebuild and test the current production application and SDK',
    'Unpack and verify the same-build Windows application and SDK',
    'Execute real Windows Orbiter with Sol, ISS and source-built ShuttlePB',
    'Verify actual GDI pixels, GPU blits, context restoration and DC ownership',
    'Compare every current production cockpit with the original Windows reference',
    'Compare current window-routed stock controls with frozen Windows',
    'Retain the exact current application and SDK for full stock qualification',
    'Upload the current SDK without granting stock qualification')


def validate_api(record,configuration):
    require(configuration in PINS and record['repository']=={'owner':'dcajacob','repo':'orbiter-cross-platform'},'Authorized repository/configuration required')
    run=record['run'];artifact=record['artifact'];ident,size,digest=PINS[configuration]
    require(run['id']==RUN and run['head_sha']==PRODUCER and run['head_branch']=='qualification/current-windows-sdk-retry' and
            run['path']=='.github/workflows/phase6-current-windows-sdk.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Exact completed current SDK producer required')
    require(artifact['id']==ident and artifact['name']=='current-windows-sdk-'+configuration and artifact['expired'] is False and
            artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and
            artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==PRODUCER,'Exact retained source SDK artifact required')
    found=[j for j in record['jobs'] if j['name']=='current-windows / Real Windows client '+configuration+' x64']
    require(len(found)==1,'Unique actual current SDK job required');job=found[0]
    require(job['run_id']==RUN and job['head_sha']==PRODUCER and job['status']=='completed' and job['conclusion']=='success' and
            'windows-2025' in job['labels'],'Successful matching standard Windows SDK job required')
    for name in REQUIRED_STEPS:
        steps=[s for s in job['steps'] if s['name']==name]
        require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','Actual Windows build/test/retention step differs: '+name)
    compared=[j for j in record['jobs'] if j['id']==128875554076]
    require(len(compared)==1 and compared[0]['run_id']==RUN and compared[0]['head_sha']==PRODUCER and
            compared[0]['status']=='completed' and compared[0]['conclusion']=='success','Actual current Debug/Release comparison gate required')
    return job


def unpack(archive,target,expected=None):
    require(not target.exists(),'Fresh SDK restoration output required');target.mkdir(parents=True)
    seen=set();files={}
    with zipfile.ZipFile(archive) as source:
        require(sum(i.file_size for i in source.infolist())<4*1024**3 and len(source.infolist())<50000,'SDK archive exceeds bounded restoration')
        for member in source.infolist():
            if member.is_dir():continue
            name=member.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(member.external_attr>>16),'Duplicate/case-colliding/symlink SDK member')
            seen.add(name.casefold());require(expected is None or name in expected,'Unmanifested SDK runtime member')
            body=source.read(member);checksum=hashlib.sha256(body).hexdigest()
            require(expected is None or checksum==expected[name],'Actual sealed SDK runtime byte differs')
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body);files[name]=checksum
    require(files and (expected is None or set(files)==set(expected)),'Complete nonempty SDK runtime closure required')
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','source-owner','output'):parser.add_argument('--'+name,type=lambda p:Path(p).resolve(),required=True)
    parser.add_argument('--configuration',choices=sorted(PINS),required=True);a=parser.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual GitHub Windows SDK restoration required')
    record=json.loads(a.api.read_text());job=validate_api(record,a.configuration);ident,size,digest=PINS[a.configuration]
    require(a.archive.stat().st_size==size and sha(a.archive)==digest,'Actual downloaded SDK ZIP differs from API bytes')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh repository-owned SDK destination required')
    a.output.mkdir(parents=True);payload=a.output/'source-artifact';outer=unpack(a.archive,payload)
    report=json.loads((payload/'current-application.json').read_text());item=report['configurations'][a.configuration]
    require(report['protocol']=='phase6-github-current-application-v1' and report['status']=='built-and-client-tested-awaiting-complete-stock-qualification' and
            report['source_commit']==PRODUCER and report['owning_sources_unchanged'] is True and item['status']=='built' and
            report['github']['run_id']==RUN and report['github']['run_attempt']==1 and report['github']['source']==PRODUCER and
            report['github']['image_os'] in ('win25','win25-vs2026') and report['phase6_complete'] is False and
            report['native_admission_qualified'] is False,'Original closed current SDK build receipt differs')
    runtime=a.output/'runtime';require(PureWindowsPath(item['runtime'])==PureWindowsPath(str(runtime)),
            'Restored SDK must preserve its recorded absolute GitHub workspace path')
    archive=payload/'runtime.zip';require(sha(archive)==report['runtime_archive_sha256'] and archive.stat().st_size==report['runtime_archive_bytes'],
            'Sealed inner SDK archive differs')
    unpack(archive,runtime,item['runtime_files_sha256'])
    require(sha(runtime/'test-runtime.json')==item['sdk_manifest_sha256'],'Actual restored SDK manifest differs')
    require(subprocess.check_output(['git','-C',str(a.source_owner),'rev-parse','HEAD'],text=True).strip()==PRODUCER,
            'Actual separate immutable SDK source checkout differs')
    helper=a.source_owner/'Tests/Production/CurrentWindows/retain_hosted_sdk.py'
    original=subprocess.check_output(['git','-C',str(a.source_owner),'show',PRODUCER+':Tests/Production/CurrentWindows/retain_hosted_sdk.py'])
    require(helper.read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),'Original SDK source reader changed')
    spec=importlib.util.spec_from_file_location('immutable_current_sdk_reader',helper);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    require(reader.source_files(PRODUCER)==report['source_guard_sha256_lf'],'Complete actual immutable application-source closure differs')
    require(reader.runtime_files(runtime,PRODUCER)==item['runtime_files_sha256'],'Actual complete current runtime closure differs')
    inventory=json.loads((payload/'registered-tests.json').read_text());tests=reader.unit_result(inventory,payload/'runtime-ctest.xml')
    require(tests==item['tests'] and tests['executed_processes']==28 and sha(payload/'build-inputs.json')==item['build_inputs_sha256'],
            'Original complete passed Windows unit/compiler receipt differs')
    require(all(sha(payload/name)==value for name,value in outer.items()),'Original API-bound SDK evidence changed during restoration')
    receipt=dict(protocol='phase6-github-current-sdk-restoration-v1',status='restored-and-verified-current-sdk-only',
        compiled_source=PRODUCER,collector_source=os.environ['GITHUB_SHA'],configuration=a.configuration,
        original_run_id=RUN,original_job_id=job['id'],original_artifact_id=ident,original_artifact_sha256=digest,
        original_build_manifest_sha256=sha(payload/'current-application.json'),runtime=str(runtime),source_owner=str(a.source_owner),
        source_guard_sha256_lf=report['source_guard_sha256_lf'],runtime_files_sha256=item['runtime_files_sha256'],tests=tests,
        source_api_sha256=sha(a.api),stock_simulation_executed=False,phase6_complete=False,native_admission_qualified=False)
    (a.output/'restoration.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'])


if __name__=='__main__':main()
