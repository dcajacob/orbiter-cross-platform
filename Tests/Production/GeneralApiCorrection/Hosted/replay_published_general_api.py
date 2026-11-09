#!/usr/bin/env python3
"""Restore exact published observations for read-only audit; never launch a simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import require,sha,load,APPLICATION
import restore_sdk
import restore_observer

CAPTURE_SOURCE='8ad65617139767cba1e8fe92ef47bfedab6edd09'
CAPTURE_RUN=42713286498
PINS={
 'Debug':(129488509539,13716298901,4256069,'90fcf54a1a7fee0caabbf722aed70870c6be44fec0d01668cc084a1219290ddd'),
 'Release':(129488509553,13716124351,4124978,'e7ec93daf0ac6f63f67d0e5f53d210cac17e12a8ebd4e53e0f1924985a008ae4')}


def validate_capture_api(record,configuration):
    require(configuration in PINS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact capture repository/configuration required')
    run=record['run'];artifact=record['artifact'];job_id,ident,size,digest=PINS[configuration]
    require(run['id']==CAPTURE_RUN and run['head_sha']==CAPTURE_SOURCE and run['head_branch']=='qualification/current-windows-general-api-v3' and
            run['path']=='.github/workflows/phase6-current-windows-general-api.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='failure','Preserve the exact actually failed source-reader producer; no status normalization')
    require(artifact['id']==ident and artifact['name']=='hosted-current-Windows-GeneralApi-'+configuration and artifact['expired'] is False and
            artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and artifact['workflow_run']['id']==CAPTURE_RUN and
            artifact['workflow_run']['head_sha']==CAPTURE_SOURCE,'Exact closed complete actual observation artifact required')
    selected=[j for j in record['jobs'] if j['id']==job_id]
    require(len(selected)==1,'One actual original observation job required');job=selected[0]
    require(job['head_sha']==CAPTURE_SOURCE and job['run_id']==CAPTURE_RUN and job['name']=='Current Windows original corrected observer matrix '+configuration and
            job['status']=='completed' and job['conclusion']=='failure' and 'windows-2025' in job['labels'] and 'self-hosted' not in job['labels'],
            'Original standard-runner failed source-reader job must retain its actual identity')
    steps={x['name']:x for x in job['steps']}
    for name,status in (
      ('Restore all immutable application SDK members and re-read every original unit receipt','success'),
      ('Restore the exact original passive driver bytes without enabling them or changing the SDK','success'),
      ('Compile the unchanged passive General API observer against the exact retained SDK','success'),
      ('Execute all eight actual original corrected and observer-off-on cases in the inherited session','success'),
      ('Independently re-read all unchanged original API assertions and exact SDK compiler source receipts','failure'),
      ('Run actions/upload-artifact@v7','success')):
        require(name in steps and steps[name]['status']=='completed' and steps[name]['conclusion']==status,'Original actual capture/failed-reader/upload step differs: '+name)
    return job


def merge_tree(source,destination,protected_metadata=False,history=None):
    destination=Path(destination);source=Path(source);files={}
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(source);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        require(target.parent.resolve()==target.parent and not target.is_symlink(),'Restored capture parent cannot redirect')
        if target.exists():
            if sha(target)!=sha(path):
                allowed={Path('current-sdk-source/api.json'),Path('current-observer-download/api.json')}
                require(protected_metadata and relative in allowed and history is not None,'Restoration would replace an unrelated or changed byte: '+str(relative))
                copy=history/relative;copy.parent.mkdir(parents=True,exist_ok=True);require(not copy.exists(),'Fresh current API diagnostic preservation required')
                shutil.copy2(target,copy);target.unlink();shutil.copy2(path,target)
            else:pass
        else:shutil.copy2(path,target)
        require(sha(target)==sha(path),'Restored original capture byte changed')
        files[relative.as_posix()]=sha(path)
    return files


def unpack_capture(archive,destination):
    require(not destination.exists(),'Fresh capture restoration required');destination.mkdir(parents=True);files={};seen=set()
    with zipfile.ZipFile(archive) as incoming:
        require(len(incoming.infolist())<50000 and sum(i.file_size for i in incoming.infolist())<1024**3,'Bounded complete raw API artifact required')
        for item in incoming.infolist():
            if item.is_dir():continue
            name=item.filename;restore_sdk.safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16),'Duplicate/colliding/symlink published API member');seen.add(name.casefold())
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(incoming.read(item));files[name]=sha(target)
    require(files,'Nonempty original observation artifact required');return files



def exact_source_bytes(immutable,recorded_sha256):
    canonical=immutable.replace(b'\r\n',b'\n')
    variants=[immutable,canonical,canonical.replace(b'\n',b'\r\n')]
    matches=[body for body in variants if hashlib.sha256(body).hexdigest()==recorded_sha256]
    require(matches,'Recorded raw source is not the exact immutable Git text in LF or CRLF encoding')
    return matches[0]


def restore_exact_source(owner,commit,relative,recorded_sha256):
    restore_sdk.safe(relative);path=Path(owner)/relative
    immutable=subprocess.check_output(['git','-C',str(owner),'show',commit+':'+relative])
    expected=exact_source_bytes(immutable,recorded_sha256)
    require(path.is_file() and not path.is_symlink() and path.read_bytes().replace(b'\r\n',b'\n')==immutable.replace(b'\r\n',b'\n'),
            'Fresh source checkout differs from its immutable canonical owner')
    if path.read_bytes()!=expected:path.write_bytes(expected)
    require(sha(path)==recorded_sha256,'Exact original raw source encoding was not restored')
    return dict(commit=commit,path=str(path),raw_sha256=recorded_sha256,canonical_sha256_lf=hashlib.sha256(immutable.replace(b'\r\n',b'\n')).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=sorted(PINS),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual standard hosted Windows read-only materialization required')
    name=a.configuration+'-GeneralApi';base=ROOT/'out/published-Windows-api-source'/a.configuration;record=load(base/'api.json');validate_capture_api(record,a.configuration)
    _,_,size,digest=PINS[a.configuration];archive=base/'producer.zip';require(archive.stat().st_size==size and sha(archive)==digest,'Actual published observation ZIP digest/length differs')
    original=base/'original-artifact';raw=unpack_capture(archive,original)
    sdk_api=ROOT/'out/current-sdk-source/api.json';sdk_record=load(sdk_api);restore_sdk.validate_api(sdk_record,a.configuration)
    _,sdk_size,sdk_digest=restore_sdk.PINS[a.configuration];sdk_archive=ROOT/'out/current-sdk-source/producer.zip'
    require(sdk_archive.stat().st_size==sdk_size and sha(sdk_archive)==sdk_digest,'Actual original C08 SDK API ZIP differs')
    sdk=ROOT/'out/current-windows-sdk';payload=sdk/'source-artifact';restore_sdk.unpack(sdk_archive,payload)
    built=load(payload/'current-application.json');item=built['configurations'][a.configuration]
    inner=payload/'runtime.zip';require(sha(inner)==built['runtime_archive_sha256'] and inner.stat().st_size==built['runtime_archive_bytes'],'Original sealed inner SDK differs')
    restore_sdk.unpack(inner,sdk/'runtime',item['runtime_files_sha256'])
    fixture_api=ROOT/'out/current-observer-download/api.json';restore_observer.validate_api(load(fixture_api),a.configuration)
    _,fixture_size,fixture_digest,_=restore_observer.PINS[a.configuration];fixture_archive=ROOT/'out/current-observer-download/producer.zip'
    require(fixture_archive.stat().st_size==fixture_size and sha(fixture_archive)==fixture_digest,'Actual original inactive fixture ZIP differs')
    fixture_payload=ROOT/'out/current-observer-restoration/source-artifact';restore_sdk.unpack(fixture_archive,fixture_payload)
    merge_tree(fixture_payload/'current-stock-preparation',ROOT/'out/current-stock-preparation')
    history=base/'fresh-API-before-original-byte-restoration'
    restored=merge_tree(original,ROOT/'out',protected_metadata=True,history=history)
    # All original transport/source records keep their original bytes and original run.
    restore_sdk.validate_api(load(ROOT/'out/current-sdk-source/api.json'),a.configuration)
    restore_observer.validate_api(load(ROOT/'out/current-observer-download/api.json'),a.configuration)
    cfg=load(ROOT/'out/current-api-requests'/name/'request.json')
    require(cfg['github']['collector_commit']==CAPTURE_SOURCE and cfg['github']['run_id']==CAPTURE_RUN and
            cfg['configuration']==a.configuration,'Original request/capture source must remain unchanged')
    worker=load(ROOT/'out/current-api-requests'/name/'worker-result.json')
    require(worker['status']=='captured-current-Windows-original-and-corrected-api-diagnostic-only' and worker['actual_processes']==8,
            'Complete actual observations required; no new simulation may replace them')
    source_restorations=[]
    runners=load(cfg['roles']['runner']['manifest_path'])
    for relative,value in runners['files_sha256'].items():
        source_restorations.append(restore_exact_source(ROOT/'capture-source',CAPTURE_SOURCE,relative,value))
    observer=load(cfg['roles']['observer']['manifest_path'])['observer']
    source_restorations.append(restore_exact_source(ROOT/'application-source',APPLICATION,'Tests/Production/GeneralApiCorrection/Observer.cpp',observer['source_sha256']))
    plan=load(cfg['renderer_shader_delivery']['path'])
    for value in plan['files'].values():
        source_restorations.append(restore_exact_source(ROOT/'application-source',APPLICATION,value['source'],value['sha256']))
    cmake='OVP/OGLClient/CMakeLists.txt';cmake_path=str(ROOT/'application-source'/cmake)
    source_restorations.append(restore_exact_source(ROOT/'application-source',APPLICATION,cmake,plan['guarded_files_sha256'][cmake_path]))
    # Restore the original provider bytes separately; retain the original provider metadata verbatim.
    mesa_fresh=ROOT/'out/replayed-Mesa-original-provider'
    subprocess.run([sys.executable,'-B',str(ROOT/'application-source/Tests/Production/stage_mesa.py'),'stage',
                    '--cache','out/replayed-Mesa-cache','--destination',str(mesa_fresh)],cwd=ROOT,check=True)
    old_provider=load(ROOT/'out/current-stock-mesa/mesa-runtime.json');fresh_provider=load(mesa_fresh/'mesa-runtime.json')
    require(old_provider['files']==fresh_provider['files'] and old_provider['lock_sha256']==fresh_provider['lock_sha256'] and old_provider['packages']==fresh_provider['packages'],'Original provider byte/file/package/lock map changed')
    for relative,value in old_provider['files'].items():
        source=mesa_fresh/relative;target=ROOT/'out/current-stock-mesa'/relative;require(sha(source)==value['sha256'],'Original provider source byte differs')
        if target.exists():require(sha(target)==value['sha256'],'Conflicting original provider byte')
        else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    require(all(sha(ROOT/'out'/n)==v for n,v in restored.items()),'Original published member changed while restoring inputs')
    proof=dict(protocol='phase6-restored-published-existing-Windows-GeneralApi-v1',status='restored-exact-original-observations-for-read-only-audit',
        original_capture_source=CAPTURE_SOURCE,original_run_id=CAPTURE_RUN,configuration=a.configuration,
        original_artifact_id=PINS[a.configuration][1],original_archive_sha256=digest,original_archive_bytes=size,
        actual_original_member_count=len(raw),raw_member_sha256=raw,materialized_member_sha256=restored,
        auditor_source=os.environ['GITHUB_SHA'],auditor_run_id=int(os.environ['GITHUB_RUN_ID']),
        original_capture_source_and_request_and_recorded_PIDs_preserved=True,old_failed_run_status_preserved=True,
        exact_original_raw_source_snapshots=source_restorations,source_code_canonical_identity_and_recorded_raw_hashes_both_preserved=True,
        new_simulator_processes_launched=0,qualification_granted=False,normal_admission_qualified=False,phase6_complete=False)
    (base/'materialization.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof['status'])


if __name__=='__main__':main()
