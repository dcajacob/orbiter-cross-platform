#!/usr/bin/env python3
"""Read retained failed native process logs without rebuilding or rerunning simulations."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import zipfile
from contracts import require,sha

SOURCE='d23d371a510dd464cde95a301dbc685514391f9c'
RUN=42532847296
PINS={'Debug-sse2':(128890766428,13641126773,353656142,'65c4e26ae581e3e7ca19417e808b6bd5a0b6e58624905d5040593a246302d30e'),
      'Debug-automatic':(128890766460,13641516291,353874040,'86aee54aab893ebb311a0e005b6af83e1bfaabb007478e98f6933f9f3c9304b8')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=sorted(PINS),required=True)
    p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true','Hosted retained-byte diagnosis only; no local bulk transfers')
    job_id,ident,size,digest=PINS[a.profile];base=a.root/a.profile;api=json.loads((base/'api.json').read_text())
    run=api['run'];artifact=api['artifact'];job=next(j for j in api['jobs'] if j['id']==job_id)
    require(run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/native-stock-writers' and
            run['path']=='.github/workflows/phase6-native-stock-writers.yml' and run['run_attempt']==1 and
            job['run_id']==RUN and job['head_sha']==SOURCE and job['status']=='completed' and job['conclusion']=='failure' and
            'ubuntu-24.04' in job['labels'],'Actual original failed native writer job required')
    require(artifact['id']==ident and artifact['name']=='normal-native-stock-writers-'+a.profile and
            artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and artifact['expired'] is False and
            artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE,
            'Actual retained failed writer artifact identity differs')
    archive=base/'producer.zip';require(archive.stat().st_size==size and sha(archive)==digest,'Actual failed writer ZIP differs from API digest')
    target=base/'selected';require(not target.exists(),'Fresh retained diagnostic directory required');target.mkdir(parents=True)
    prefix='native-stock-writer/'+a.profile+'/'
    top={'hosted-native-writer/'+a.profile+'/'+name for name in ('collection.json','all-38-stock-writers-twice.log','actual-system-packages.txt','supplemental-system-packages.txt')}
    result=dict(status='retained-failed-native-process-logs-only',compiled_runtime_source='ccc02c8a34bd1f227624d8778a141e8736ae8111',
        compiled_provider_source='60ba46377f236c2d4705f444c0174e0f5af8252f',capture_collector_source=SOURCE,profile=a.profile,
        original_run_id=RUN,original_job_id=job_id,original_artifact_id=ident,original_archive_sha256=digest,
        files={},processes={},simulation_executed=False,binaries_rebuilt=False,qualification_granted=False,phase6_complete=False)
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();require(len(names)==len(set(names)),'Duplicate retained ZIP members')
        for name in names:
            path=PurePosixPath(name)
            require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,'Unsafe retained ZIP path')
            relative=name.removeprefix(prefix)
            selected=name in top or (name.startswith(prefix) and (relative=='capture.json' or
                re.fullmatch(r'remaining_stock_\d{3}-[12]/(?:console\.log|process-result\.json|process-receipt\.json|invocation\.json|graphics-lifecycle\.json|stock-vessel-(?:complete|failure)\.txt|scene-summary\.json)',relative)))
            if not selected:continue
            entry=source.getinfo(name);require(entry.file_size<16*1024**2,'Selected retained text/report exceeds bound')
            body=source.read(name);destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(body)
            result['files'][name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
            if name.startswith(prefix) and '/' in relative:
                folder,filename=relative.split('/',1);record=result['processes'].setdefault(folder,{})
                if filename=='process-result.json':record['process_result']=json.loads(body)
                if filename=='console.log':
                    text=body.decode(errors='replace');record['console_sha256']=hashlib.sha256(body).hexdigest()
                    record['diagnostics']=[line for line in text.splitlines() if any(s in line for s in
                        ('ERROR:','SUMMARY:','runtime error:','Assertion','LeakSanitizer','AddressSanitizer','error while loading','terminate called'))]
                    if folder in ('remaining_stock_001-1','remaining_stock_002-1'):
                        print(a.profile+'/'+folder+' actual original console tail:\n'+text[-14000:],flush=True)
        capture=target/prefix/'capture.json';require(capture.is_file(),'Actual original failed capture report missing')
        report=json.loads(capture.read_text());require(report['producer_commit']==SOURCE and report['runtime_source_commit']==result['compiled_runtime_source'],
            'Actual failed capture/source identity differs')
        result['capture_status']=report['status'];result['capture_failures']=report['failures']
        require(result['processes'] and all('process_result' in value and 'console_sha256' in value for value in result['processes'].values()),
                'Actual per-process exit and raw console pair required')
    require(sha(archive)==digest,'Retained failed writer archive changed')
    (base/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','profile','capture_status','capture_failures','processes')}),flush=True)


if __name__=='__main__':main()
