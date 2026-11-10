#!/usr/bin/env python3
"""Reuse only the completed exact original package preflight; failed captures remain failed."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
SOURCE='b939aabdda71832a61646cf304ff211ee4cc50d4'
RUN=42806647208
ARTIFACT=13761595407
SIZE=175698
DIGEST='7dc1a4a4ac48548a8e088ae9a4ae4aa022eee91a60a04ccbda8e12cecb398c48'
JOBS={129797371846:'readiness',129802746178:'Debug-sse2',129802746248:'Release-sse2',129802746262:'Release-automatic',129802746295:'Debug-automatic'}


def validate_api(api):
    run=api['run'];jobs=api['jobs'];a=api['artifact']
    require(api['repository']=={'owner':'dcajacob','repo':'orbiter-cross-platform'} and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False and run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/native-class-rejections-v2' and run['path']=='.github/workflows/phase6-native-class-rejections.yml' and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='failure','Exact closed original failed capture history required')
    require(len(jobs)==5 and {j['id'] for j in jobs}==set(JOBS),'Every actual original job and failed profile must remain represented')
    for j in jobs:
        readiness=j['id']==129797371846
        require(j['head_sha']==SOURCE and j['run_id']==RUN and j['run_attempt']==1 and j['status']=='completed' and j['labels']==['ubuntu-24.04'] and j['name']==('readiness' if readiness else 'Original normal host class and loader rejection controls '+JOBS[j['id']]) and j['conclusion']==('success' if readiness else 'failure'),'Original success/failure and standard runner identity must remain exact')
        steps={v['name']:v for v in j['steps']}
        name=('Require one complete signed dated-archive package preflight before all four original captures' if readiness else 'Run all45 original normal host rejection controls with exact matching hosted userspace')
        require(steps[name]['conclusion']==('success' if readiness else 'failure') and steps['Run actions/upload-artifact@v7']['conclusion']=='success','Original completed preflight, failure and partial retention required')
    require(a['id']==ARTIFACT and a['name']=='native-class-rejections-readiness' and a['expired'] is False and a['size_in_bytes']==SIZE and a['digest']=='sha256:'+DIGEST and a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==SOURCE,'Exact published completed preflight artifact identity required')


def inspect(api,archive):
    validate_api(api);require(archive.stat().st_size==SIZE and sha(archive)==DIGEST,'Exact actual published setup ZIP bytes required')
    bodies={};seen=set()
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir():continue
            name=item.filename;p=PurePosixPath(name)
            require(name and str(p)==name and not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and item.file_size<10*1024**2,'Safe complete setup receipt member required')
            seen.add(name.casefold());bodies[name]=z.read(item)
    require(len(bodies)==26,'Complete exact setup receipt member scope required')
    read=lambda n:json.loads(bodies[n]);digest=lambda b:hashlib.sha256(b).hexdigest()
    controls=read('class-rejection-controls.json');pre=read('class-userspace-preflight/preflight.json');original=read('class-rejection-source-preflight.json')
    require(controls['status']=='passed' and controls['tests_run']==393 and controls['sources_match_producer'] is True and controls['producer_commit']==SOURCE and all(controls[k]==0 for k in ('failures','errors','skipped')),'Every original393 bounded source control must remain passed')
    require(original==load(ROOT/'Tests/Production/Closeout/class-rejection-original-source-v1.lock.json'),'Every original Ccc source, fixture and all45 controls must remain exact')
    require(pre['status']=='verified-complete-original-package-inventory-only' and pre['collector_source']==SOURCE and pre['snapshot']=='20261109T212432Z' and pre['actual_simulator_processes']==0 and pre['all_original_versions_preserved'] is True and pre['archive_signatures_and_tls_required'] is True and pre['qualification_granted'] is False and pre['phase6_complete'] is False,'Complete original package-only preflight, never runtime acceptance required')
    inventory=bodies['class-userspace-preflight/actual-system-packages.txt'];lines=inventory.decode().splitlines();packages=dict(line.split('=',1) for line in lines)
    require(pre['actual_package_count']==len(lines)==len(packages)==488 and pre['original_inventory_sha256']==pre['actual_inventory_sha256']==digest(inventory)=='0ae6765d460a0d744c48afdb242257d02a29da4845cf7e8b7fda42004e164900' and packages['libheif1:amd64']==packages['libheif-plugin-aomdec:amd64']=='1.21.2-3ubuntu0.6','Every exact original package including prior failed versions required')
    require([v['label'] for v in pre['commands']]==['signed-snapshot-update','restore-complete-original-package-versions'],'Both original complete signed package commands required')
    for command in pre['commands']:require(command['actual_returncode']==0 and command['actual_pid']>0 and not command.get('timed_out') and command['log_sha256']==digest(bodies['class-userspace-preflight/'+command['label']+'.log']),'Actual original successful command and log required')
    require(pre['commands'][0]['argv']==['apt-get','update'] and pre['commands'][1]['argv'][:4]==['apt-get','install','-y','--no-install-recommends'] and len(pre['commands'][1]['argv'][4:])==488 and set(pre['commands'][1]['argv'][4:])==set(lines),'Original full install arguments and exact488 versions required')
    require(digest(bodies['class-userspace-container.json'])==pre['actual_container_sha256'],'Actual original pinned container receipt required')
    container=read('class-userspace-container.json');lock=load(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json')
    require(len(container)==1 and any(v.endswith('@'+lock['image_digest']) for v in container[0]['RepoDigests']),'Original actual container image digest required')
    return dict(protocol='phase6-reused-completed-original-package-preflight-v1',status='verified-unchanged-package-prerequisite-only',producer_source=SOURCE,producer_run=RUN,artifact_id=ARTIFACT,artifact_sha256=DIGEST,actual_original_package_count=488,original_failed_four_profile_jobs_preserved=True,original393_controls_preserved=True,new_simulator_processes=0,each_new_capture_still_checks_full_original_package_inventory=True,qualification_granted=False,phase6_complete=False,hands_on_ready=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('api','archive','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh separate prerequisite verification required');atomic_json(a.output,inspect(load(a.api),a.archive))
