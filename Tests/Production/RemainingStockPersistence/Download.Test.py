#!/usr/bin/env python3
"""Check actual artifact metadata, retained ZIP transfer and damaged requests."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import zipfile

import download
import transport
from observations import require,sha

HERE=Path(__file__).resolve().parent


def rejects(name,action,reason,controls):
    try:action()
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as error:
        require(reason in str(error),'Wrong transfer rejection for '+name+': '+str(error))
        controls.append(dict(control=name,reason=str(error)))
        print(name,'rejected:',str(error)[:150],flush=True)
    else:raise ValueError('Changed Windows artifact request/bytes accepted: '+name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('retained-archive','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--public-request',type=lambda v:Path(v).resolve(),default=HERE/'DownloadApiFixture.json')
    a=p.parse_args();require(not a.output.exists(),'Fresh artifact transfer controls required')
    request=json.loads(a.public_request.read_text());run,records=download.request_records(request,True)
    protected={str(a.public_request):sha(a.public_request),str(a.retained_archive):sha(a.retained_archive)}
    source_hashes={name:sha(HERE/name) for name in ('download.py','transport.py','observations.py')}
    report=dict(status='failed',controls=[],workflow_run=run,source_sha256=source_hashes,
        native_admission_qualified=False,phase6_complete=False,
        scope='Actual public four-profile diagnostic metadata and one retained real ZIP stream/extraction only. No live network transfer, new simulator execution or full Windows persistence matrix is inferred.')
    try:
        mutations={
            'missing_profile':lambda d:d['artifacts'].pop(),
            'duplicate_artifact':lambda d:d['artifacts'][1]['api_artifact'].update(id=d['artifacts'][0]['api_artifact']['id']),
            'duplicate_profile':lambda d:d['artifacts'].__setitem__(1,copy.deepcopy(d['artifacts'][0])),
            'different_repository':lambda d:d['workflow_run']['repository'].update(full_name='other/repository'),
            'different_branch':lambda d:d['workflow_run'].update(head_branch='other-branch'),
            'different_workflow':lambda d:d['workflow_run'].update(path=transport.WORKFLOWS[False]),
            'unfinished_run':lambda d:d['workflow_run'].update(status='in_progress'),
            'failed_run_without_explicit_retention':lambda d:d['workflow_run'].update(conclusion='failure'),
            'different_source':lambda d:d['workflow_run'].update(head_sha='0'*40),
            'expired_artifact':lambda d:d['artifacts'][0]['api_artifact'].update(expired=True),
            'invalid_digest':lambda d:d['artifacts'][0]['api_artifact'].update(digest='sha256:'+'g'*64),
            'different_artifact_run':lambda d:d['artifacts'][0]['api_artifact']['workflow_run'].update(id=run['id']+1),
            'different_artifact_source':lambda d:d['artifacts'][0]['api_artifact']['workflow_run'].update(head_sha='0'*40),
            'insecure_download_reference':lambda d:d['artifacts'][0].update(download_url='http://example.invalid/archive'),
            'embedded_credentials':lambda d:d['artifacts'][0].update(download_url='https://user:password@example.invalid/archive'),
        }
        identity_reasons={'missing_profile','duplicate_artifact','duplicate_profile'}
        run_reasons={'different_repository','different_branch','different_workflow','unfinished_run','failed_run_without_explicit_retention'}
        url_reasons={'insecure_download_reference','embedded_credentials'}
        for name,mutate in mutations.items():
            damaged=copy.deepcopy(request);mutate(damaged)
            reason='unique actual Windows profiles' if name in identity_reasons else 'workflow/repository/source identity' if name in run_reasons else 'HTTPS artifact download' if name in url_reasons else 'Artifact profile/digest/size/expiry'
            rejects(name,lambda:download.request_records(damaged,True),reason,report['controls'])
        rejects('diagnostic_as_full_workflow',lambda:download.request_records(request,False),'workflow/repository/source identity',report['controls'])
        failed=copy.deepcopy(request);failed['workflow_run']['conclusion']='failure'
        require(download.request_records(failed,True,True)[0]['conclusion']=='failure','Explicit failed-run retention positive failed')
        active=copy.deepcopy(request);active['workflow_run'].update(status='in_progress',conclusion=None)
        require(download.request_records(active,True,False,True)[0]['status']=='in_progress','Explicit active-run diagnostic retention positive failed')
        rejects('active_workflow_as_full_reference',lambda:transport.run_identity(active['workflow_run'],True),
                'workflow/repository/source identity',report['controls'])
        diagnostic=dict(status='passed',protocol=transport.PROTOCOL,diagnostic_only=True,source_commit=run['head_sha'],artifacts=[])
        rejects('diagnostic_transport_as_qualification',lambda:transport.inspect_matrix(diagnostic,Path('/unused'),{},run['head_sha']),
                'Complete matching four-profile',report['controls'])
        identity,public,_=next(r for r in records if r[0]['sha256']==sha(a.retained_archive))
        with tempfile.TemporaryDirectory(prefix='orbiter-artifact-transfer-controls-') as temporary:
            root=Path(temporary);positive=root/'positive';positive.mkdir()
            opener=lambda _url,**_kwargs:a.retained_archive.open('rb')
            result=download.transfer(identity,public,'https://example.invalid/retained-stream',positive,root,opener)
            require(result['sha256']==sha(a.retained_archive) and result['api_digest']=='sha256:'+result['sha256'] and
                    len(result['decoded_members_sha256'])>0 and 'download_url' not in json.dumps(result),
                    'Exact real retained stream extraction or URL privacy positive failed')
            report['retained_stream_positive']={k:result[k] for k in ('id','profile','bytes','sha256','api_digest')}
            report['retained_stream_positive']['members']=len(result['decoded_members_sha256'])
            for name,field,value in [('wrong_zip_digest','sha256','0'*64),('wrong_zip_size','bytes',identity['bytes']+1)]:
                damaged=dict(identity);damaged[field]=value;target=root/name;target.mkdir()
                rejects(name,lambda:download.transfer(damaged,public,'https://example.invalid/retained-stream',target,root,opener),
                        'API-advertised digest/size',report['controls'])
                require((target/(identity['profile']+'.zip')).is_file(),'Failed raw ZIP bytes were discarded')
            target=root/'truncated';target.mkdir();prefix=a.retained_archive.read_bytes()[:4096]
            rejects('truncated_transfer',lambda:download.transfer(identity,public,'https://example.invalid/retained-stream',target,root,
                lambda _url,**_kwargs:io.BytesIO(prefix)),'API-advertised digest/size',report['controls'])
            require((target/(identity['profile']+'.zip')).read_bytes()==prefix,'Actual failed transfer prefix was discarded')
            secret_url='https://example.invalid/archive?private_control_token=do-not-retain'
            def failing(_url,**_kwargs):raise urllib.error.URLError(secret_url)
            try:download.transfer(identity,public,secret_url,root/'unreachable',root,failing)
            except ValueError as error:
                require('private_control_token' not in str(error) and 'URLError' in str(error),'Signed transfer reference leaked into error text')
                report['controls'].append(dict(control='signed_reference_failure_privacy',reason=str(error)))
            else:raise ValueError('Failed transfer unexpectedly succeeded')
            with zipfile.ZipFile(a.retained_archive) as source:
                sample=next(n for n in source.namelist() if n.endswith('/invocation.json'));body=source.read(sample)
            for name,extra,reason in (
                ('traversal_member',lambda z:z.writestr('../outside.txt',body),'Unsafe artifact member'),
                ('case_collision_member',lambda z:z.writestr(sample.upper(),body),'case-colliding'),
            ):
                blob=io.BytesIO()
                with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(sample,body);extra(z)
                bytes_=blob.getvalue();damaged=dict(identity,bytes=len(bytes_),sha256=hashlib.sha256(bytes_).hexdigest())
                target=root/name;target.mkdir()
                rejects(name,lambda:download.transfer(damaged,public,'https://example.invalid/damaged-real-member-copy',target,root,
                    lambda _url,**_kwargs:io.BytesIO(bytes_)),reason,report['controls'])
                require(not (root/'outside.txt').exists(),'Artifact member escaped its output')
        with tempfile.TemporaryDirectory(prefix='phase6-request-cleanup-controls-',dir=download.ROOT/'out') as temporary:
            root=Path(temporary)
            for name,existing in (('invalid_request_consumed',False),('existing_output_request_consumed',True)):
                private=root/(name+'.json');target=root/name
                if existing:target.mkdir();(target/'keep.txt').write_text('preserved output')
                damaged=copy.deepcopy(request);damaged['workflow_run']['repository']['full_name']='other/repository'
                damaged['artifacts'][0]['download_url']='https://example.invalid/archive?private_control_token=do-not-retain'
                private.write_text(json.dumps(damaged))
                process=subprocess.run([sys.executable,'-B',str(HERE/'download.py'),'--request',str(private),
                    '--diagnostic','--output',str(target),'--consume-request'],capture_output=True,text=True)
                require(process.returncode!=0 and not private.exists() and 'private_control_token' not in process.stdout+process.stderr,
                        'Failed CLI request cleanup or transfer URL privacy changed')
                if existing:require((target/'keep.txt').read_text()=='preserved output','Existing download output was replaced')
                report['controls'].append(dict(control=name,reason='Actual CLI rejected the request/output, consumed its private file and preserved existing bytes'))
        require(all(sha(Path(n))==v for n,v in protected.items()) and source_hashes=={n:sha(HERE/n) for n in source_hashes},
                'Retained actual Windows ZIP/API metadata or transfer source changed during controls')
        report.update(status='passed-artifact-transfer-controls',actual_four_profile_api_metadata_checked=True,
                      owning_inputs_unchanged=True,test_sha256=sha(Path(__file__)),protected_input_sha256=protected)
    except BaseException as error:report['error']=str(error);raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(len(report['controls']),'damaged artifact/metadata/transfer controls rejected;',report['retained_stream_positive']['members'],'real ZIP members verified',flush=True)


if __name__=='__main__':main()
