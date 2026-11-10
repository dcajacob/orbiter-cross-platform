#!/usr/bin/env python3
"""Verify the exact prior archive's expanded size, then restore with a real disk reserve."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile
from contracts import ROOT,atomic_json,load,require,sha
from frozen_admission_api import REFERENCE,candidate,expected_paths,hosted
from rejection_input_bundle import safe
import restore_published_admission_reference as prior

CAP=8*1024**3
RESERVE=8*1024**3
COUNT=1123
RELATIVE=REFERENCE.relative_to(ROOT).as_posix()


def source_archive(folder):
    def get(path):return json.loads(subprocess.check_output([*prior.GH,path],timeout=60))
    run=get(prior.API+'/runs/'+str(prior.RUN))
    jobs=get(prior.API+'/runs/'+str(prior.RUN)+'/jobs?per_page=100')['jobs']
    artifact=get(prior.API+'/artifacts/'+str(prior.ARTIFACT))
    atomic_json(folder/'api.json',dict(run=run,jobs=jobs,artifact=artifact))
    prior.inspect_api(run,jobs,artifact)
    archive=prior.download(folder)
    require(shutil.disk_usage(folder).free>=prior.TAR_BYTES+RESERVE,'Prior reference decode must retain the eight-GiB reserve')
    with zipfile.ZipFile(archive) as z:
        require(len(z.infolist())==2 and set(z.namelist())=={'reference.json','reference.tar.gz'},'Exact prior two-member archive required')
        for name,bound,h in [('reference.json',8192,prior.RECEIPT_SHA),('reference.tar.gz',prior.TAR_BYTES,prior.TAR_SHA)]:
            info=z.getinfo(name)
            require(0<info.file_size<=bound and (name!='reference.tar.gz' or info.file_size==bound),'Exact sealed prior member bound required')
            path=folder/name
            with z.open(info) as source,path.open('xb') as output:shutil.copyfileobj(source,output,1024**2)
            require(sha(path)==h,'Exact previous reference inner member bytes required')
    return folder/'reference.tar.gz'


def index_archive(path,lock,folder,expected=None):
    """Read every exact body in one pass; never expand data based on an estimated size."""
    qsha=lock['identities']['reference']['joint_api']['qualified_report_sha256']
    require(sha(path)==prior.TAR_SHA and path.stat().st_size==prior.TAR_BYTES,'Exact prior reference TAR required')
    if expected is not None:
        require(0<expected['decoded_bytes']<CAP and len(expected['members'])==COUNT and
                sum(v['bytes'] for v in expected['members'].values())==expected['decoded_bytes'],
                'Complete measured byte capacity proof required')
        require(shutil.disk_usage(ROOT).free>=expected['decoded_bytes']+RESERVE,
                'Restore actual expanded reference size while retaining eight GiB free')
    observed={};folded=set();total=0;report=None
    progress=folder/'decode-progress.json'
    def save(status):
        atomic_json(progress,dict(status=status,decoded_members=len(observed),decoded_bytes=total,phase6_complete=False))
    save('reading-reference')
    try:
        with tarfile.open(path,mode='r|gz') as tar:
            for m in tar:
                name=m.name;relative=safe(name)
                require(relative.is_relative_to('out/joint-api-qualification') and name.casefold() not in folded and
                        m.isfile() and not m.mode&0o7000 and 0<=m.size<CAP and len(observed)<COUNT,
                        'Canonical unique complete original qualified file required')
                total+=m.size;folded.add(name.casefold())
                require(total<CAP,'Original reference exceeded safe hosted read-only bound')
                if expected is not None:
                    row=expected['members'].get(name)
                    require(row is not None and m.size==row['bytes'] and m.mode==row['mode'],'Original member size/type differs from measured readiness')
                    target=ROOT/relative
                    require(not target.exists() and not target.is_symlink() and target.resolve()==target,
                            'Fresh unredirected original qualified file required')
                    require(shutil.disk_usage(ROOT).free>=m.size+RESERVE,'Actual original member must leave eight GiB free')
                    target.parent.mkdir(parents=True,exist_ok=True)
                else:target=None
                if name==RELATIVE:require(0<m.size<4*1024**2,'Exact original qualification report must be bounded')
                h=hashlib.sha256();length=0;body=bytearray()
                stream=target.open('xb') if target else None
                try:
                    with tar.extractfile(m) as source:
                        for block in iter(lambda:source.read(1024**2),b''):
                            h.update(block);length+=len(block)
                            if stream:stream.write(block)
                            if name==RELATIVE:body.extend(block)
                finally:
                    if stream:stream.close()
                require(length==m.size,'Complete original evidence body required')
                record=dict(bytes=length,mode=m.mode,sha256=h.hexdigest())
                if target:
                    target.chmod(m.mode & 0o777)
                    require(record==row and sha(target)==record['sha256'],'Materialized exact measured body changed')
                if name==RELATIVE:
                    require(record['sha256']==qsha,'Independently qualified report changed');report=json.loads(body)
                observed[name]=record
                if len(observed)%100==0:save('reading-reference')
        require(report is not None and len(observed)==COUNT,'All actual original qualified reference bodies required')
        required=expected_paths(report)|{RELATIVE:qsha}
        require({k:v['sha256'] for k,v in observed.items()}==required,'Every original qualification byte/namespace required')
        if expected is not None:require(expected['members']==observed and expected['decoded_bytes']==total and shutil.disk_usage(ROOT).free>=RESERVE,'Measured exact member closure and eight-GiB reserve must hold')
        save('complete-exact-original-reference')
    except BaseException:
        save('incomplete-preserve-partial-diagnostics');raise
    return dict(decoded_bytes=total,members=observed)


def main():
    hosted()
    require(os.environ.get('GITHUB_REPOSITORY')==prior.REPO and sys.argv[1:] in (['--measure'],['--restore']),
            'Explicit actual standard hosted reference stage required')
    lock=candidate();folder=ROOT/'out/admission-reference-source';folder.mkdir(parents=True,exist_ok=False)
    measure=sys.argv[1]=='--measure';origin=dict(run_id=prior.RUN,source=prior.SOURCE,artifact_id=prior.ARTIFACT,
        archive_sha256=prior.ZIP_SHA,archive_bytes=prior.ZIP_BYTES,tar_sha256=prior.TAR_SHA,tar_bytes=prior.TAR_BYTES)
    fixed=dict(protocol='phase6-measured-qualified-reference-v1',status='measured-and-verified-original-qualification-inputs-only',
        source=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),candidate_id=lock['id'],exact_prior_origin=origin,
        eight_GiB_reserve=RESERVE,actual_qualification_guards=1125,reference_qualification_repeated=False,new_simulator_processes=0)
    cap=None
    if not measure:
        cap=load(ROOT/'out/admission-measured-capacity/capacity.json')
        require(all(cap[k]==v for k,v in fixed.items()),'Actual same-source measured readiness result required')
    path=source_archive(folder);result=index_archive(path,lock,folder,cap)
    if measure:
        out=ROOT/'out/admission-measured-capacity';out.mkdir()
        atomic_json(out/'capacity.json',fixed|result)
        print(json.dumps(dict(decoded_bytes=result['decoded_bytes'],members=len(result['members']),no_new_simulator_processes=True)))
    else:
        sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection'))
        import qualification
        require(len(qualification.inspect(REFERENCE)['evidence_sha256'])==1125,'Unchanged independent qualification reader must accept every restored guard')
        atomic_json(folder/'restored.json',fixed|dict(status='restored-original-qualified-bytes-with-measured-capacity',
            decoded_bytes=result['decoded_bytes'],actual_reference_sha256=sha(REFERENCE),materialized_files=len(result['members'])))
    require(sha(folder/'producer.zip')==prior.ZIP_SHA,'Original published whole ZIP changed')


if __name__=='__main__':main()
