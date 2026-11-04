#!/usr/bin/env python3
"""Preserve a complete four-profile GitHub artifact set and exact decoded bytes."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import shutil
import stat
import urllib.parse
import urllib.request
import zipfile

import transport
from observations import require,sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def request_records(request,diagnostic,allow_failed=False,allow_active=False):
    run=transport.run_identity(request['workflow_run'],diagnostic,allow_failed,allow_active)
    records=[]
    for item in request['artifacts']:
        public=item['api_artifact'];identity=transport.artifact_identity(public,run,diagnostic)
        url=urllib.parse.urlsplit(item['download_url'])
        require(url.scheme=='https' and url.hostname and not url.username and not url.password,
                'Connector-provided HTTPS artifact download reference required')
        records.append((identity,public,item['download_url']))
    require(len(records)==4 and {r[0]['profile'] for r in records}==transport.PROFILES and
            len({r[0]['id'] for r in records})==4,'Exactly four unique actual Windows profiles/artifact IDs required')
    return run,records


def transfer(identity,public,url,output,archive_root,opener=urllib.request.urlopen):
    archive=output/(identity['profile']+'.zip');decoded=output/identity['profile']
    # Errors retain the partial bytes but never expose the signed transfer URL.
    try:
        with opener(url,timeout=60) as source,archive.open('xb') as target:
            shutil.copyfileobj(source,target,4*1024*1024)
    except Exception as error:
        raise ValueError('Artifact '+str(identity['id'])+' transfer failed ('+type(error).__name__+'); any partial bytes retained') from None
    require(archive.stat().st_size==identity['bytes'] and sha(archive)==identity['sha256'],
            'Downloaded artifact differs from its API-advertised digest/size')
    decoded.mkdir();seen=set()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path=transport.safe(member.filename);name=str(path).casefold()
            require(name not in seen and not stat.S_ISLNK(member.external_attr>>16),
                    'Duplicate, case-colliding or symlink artifact member')
            seen.add(name)
            if member.is_dir():continue
            target=decoded/str(path);target.parent.mkdir(parents=True,exist_ok=True)
            with source.open(member) as incoming,target.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    members=transport.inspect_archive(archive,decoded,identity['sha256'],identity['bytes'])
    # The public API record is intentionally retained; signed URLs are not.
    public={key:public[key] for key in ('id','name','size_in_bytes','digest','expired','workflow_run')}
    return identity|dict(path=archive.relative_to(archive_root).as_posix(),decoded=decoded.relative_to(archive_root).as_posix(),
                         api_artifact=public,decoded_members_sha256=members)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('request','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--diagnostic',action='store_true',help='Explicitly select the two-scene diagnostic workflow, retaining all four profiles')
    p.add_argument('--allow-failed-run',action='store_true',help='Retain failed-run artifacts as diagnostic transport only')
    p.add_argument('--allow-active-run',action='store_true',help='Retain all four already-published artifacts from an active workflow as diagnostic transport only')
    p.add_argument('--consume-request',action='store_true',help='Remove the generated private signed-URL request when finished')
    a=p.parse_args()
    report=None
    try:
        require(not a.output.exists() and ROOT in a.output.parents,'Fresh output below the owning repository required')
        run,records=request_records(json.loads(a.request.read_text()),a.diagnostic,a.allow_failed_run,a.allow_active_run)
        a.output.mkdir(parents=True);manifest=a.output/'download.json'
        report=dict(status='downloading',protocol=transport.PROTOCOL,source_commit=run['head_sha'],workflow_run=run,
            diagnostic_only=a.diagnostic or a.allow_failed_run or a.allow_active_run,artifacts=[],failures={},
            downloader_sha256=sha(Path(__file__)),reader_sha256={name:sha(HERE/name) for name in ('transport.py','observations.py')},
            native_admission_qualified=False,phase6_complete=False,
            scope='API digest and exact artifact/member transfer only. Actual simulation, persistence, class admission and Phase 6 qualification remain separate.')
        def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
        save()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(transfer,identity,public,url,a.output,ROOT):identity for identity,public,url in records}
            for future in concurrent.futures.as_completed(futures):
                identity=futures[future]
                try:
                    result=future.result();report['artifacts'].append(result)
                    print(identity['profile'],'API digest and',len(result['decoded_members_sha256']),'decoded members verified',flush=True)
                except Exception as error:
                    report['failures'][identity['profile']]=str(error)
                    print(identity['profile'],'failed:',str(error),flush=True)
                save()
        require(len(report['artifacts'])==4 and not report['failures'],'Incomplete artifact transport retained; fresh recovery output required')
        require(report['downloader_sha256']==sha(Path(__file__)) and
                report['reader_sha256']=={name:sha(HERE/name) for name in report['reader_sha256']},
                'Owning transfer/reader source changed during download')
        report['status']='passed';save()
    except BaseException:
        if report is not None:report['status']='failed';save()
        raise
    finally:
        if a.consume_request:a.request.unlink(missing_ok=True)


if __name__=='__main__':main()
