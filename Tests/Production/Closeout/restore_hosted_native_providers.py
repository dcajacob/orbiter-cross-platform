#!/usr/bin/env python3
"""Restore exact passed dependency bytes without changing their compiled producer."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import zipfile
from hosted_native_package import ROOT,require,sha,load

RUN=42528403133
PRODUCER='60ba46377f236c2d4705f444c0174e0f5af8252f'
ARTIFACT=13636482999
SIZE=164848563
DIGEST='6304d1701c0fc0775b80046d1ed3aa813b07313207027046d9a026be4f1dfe9e'
PREFIX='out/hosted-native-providers'


def safe(name):
    value=PurePosixPath(name)
    require(name and name!='.' and str(value)==name and not value.is_absolute() and '..' not in value.parts and
            ':' not in name and '\\' not in name,'Unsafe provider archive path')
    return value


def validate_api(record):
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==RUN and run['head_sha']==PRODUCER and
            run['head_branch']=='qualification/native-providers-retry' and run['path']=='.github/workflows/phase6-native-providers.yml' and
            run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','Exact successful standard provider producer required')
    require(artifact['id']==ARTIFACT and artifact['name']=='native-stock-runtime-providers' and artifact['expired'] is False and
            artifact['size_in_bytes']==SIZE and artifact['digest']=='sha256:'+DIGEST and
            artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==PRODUCER,'Exact closed source-bound provider artifact required')
    require(len(jobs)==1 and jobs[0]['id']==128876988468 and jobs[0]['run_id']==RUN and jobs[0]['head_sha']==PRODUCER and
            jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and 'ubuntu-24.04' in jobs[0]['labels'],
            'Actual successful provider job on the standard Ubuntu runner required')


def restore_tree(archive,expected,owner):
    base=owner/PREFIX;require(not base.exists(),'Fresh source-bound provider tree required')
    links=[];seen=set()
    with tarfile.open(archive,'r:gz') as incoming:
        require(sum(m.size for m in incoming.getmembers())<8*1024**3,'Provider archive exceeds bounded restoration')
        for info in incoming.getmembers():
            name=str(safe(info.name));require(PurePosixPath(name).is_relative_to(PREFIX) and name in expected and
                    name.casefold() not in seen and not info.mode&0o7000,'Unmanifested, duplicate or unsafe provider member')
            seen.add(name.casefold());path=owner/name;path.parent.mkdir(parents=True,exist_ok=True)
            require(not path.exists() and not path.is_symlink(),'Provider restoration would overwrite another input')
            if info.isfile():
                require(expected[name]['symlink'] is None,'Provider link kind differs');path.write_bytes(incoming.extractfile(info).read());path.chmod(info.mode&0o777)
                require(sha(path)==expected[name]['sha256'],'Actual restored provider byte differs')
            elif info.issym():
                require(expected[name]['symlink']==info.linkname,'Actual provider symlink differs')
                target=Path(info.linkname);resolved=Path(os.path.normpath(str(target if target.is_absolute() else path.parent/target)))
                require(resolved.is_relative_to(base),'Provider symlink escapes the guarded tree');links.append((path,info.linkname,True))
            elif info.islnk():
                target=str(safe(info.linkname));require(target in expected and expected[name]['symlink'] is None and
                    expected[name]['sha256']==expected[target]['sha256'],'Unsafe or mismatched provider hardlink');links.append((path,owner/target,False))
            else:raise ValueError('Unsupported provider archive member kind')
    require(len(seen)==len(expected),'Complete provider archive closure required')
    pending=links
    while pending:
        remaining=[]
        for path,target,symbolic in pending:
            if symbolic:path.symlink_to(target)
            elif Path(target).is_file():os.link(target,path)
            else:remaining.append((path,target,symbolic))
        require(len(remaining)<len(pending),'Unresolvable provider hardlink closure');pending=remaining
    require(all((owner/name).resolve().is_relative_to(base) and sha(owner/name)==item['sha256'] for name,item in expected.items()),
            'Complete restored provider byte/link closure differs')
    return base


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):parser.add_argument('--'+name,type=lambda p:Path(p).resolve(),required=True)
    a=parser.parse_args();require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh provider receipt below repository out required')
    api=load(a.api);validate_api(api);require(a.archive.stat().st_size==SIZE and sha(a.archive)==DIGEST,'Actual downloaded provider API ZIP differs')
    source=a.output.parent/'provider-source';require(not source.exists(),'Fresh original provider payload required');source.mkdir(parents=True)
    wanted={'hosted-native-providers.tar.gz','hosted-native-provider.json','native-provider-container.json','native-provider-controls.json'};found={}
    with zipfile.ZipFile(a.archive) as z:
        for member in z.infolist():
            if member.is_dir():continue
            name=str(safe(member.filename));leaf=PurePosixPath(name).name
            if leaf in wanted:
                require(leaf not in found,'Duplicate original provider payload');target=source/leaf;target.write_bytes(z.read(member));found[leaf]=sha(target)
    require(set(found)==wanted,'Complete original provider payload/receipts required')
    sealed=load(source/'hosted-native-provider.json');archive=source/'hosted-native-providers.tar.gz'
    require(sealed['protocol']=='phase6-hosted-native-provider-package-v1' and sealed['source_commit']==PRODUCER and
            sealed['status']=='built-and-dependency-controls-only' and sealed['archive_sha256']==sha(archive) and
            sealed['archive_bytes']==archive.stat().st_size and sealed['phase6_complete'] is False and
            sealed['native_admission_qualified'] is False and sealed['runtime_qualification_pending'] is True,
            'Complete original dependency-only producer receipt required')
    require(sha(source/'native-provider-container.json')==sealed['actual_container_receipt_sha256'] and
            sha(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json')==sealed['container_lock_sha256'],
            'Exact original provider userspace/lock identity differs')
    base=restore_tree(archive,sealed['members'],ROOT)
    require(set(sealed['controls'])=={'fontconfig','gdk','mesa'} and all(c['status']=='passed' and sha(c['path'])==c['sha256'] for c in sealed['controls'].values()),
            'Original passed dependency controls changed')
    record=dict(protocol='phase6-hosted-native-provider-restoration-v1',status='restored-verified-dependency-bytes-only',
        compiled_provider_source=PRODUCER,collector_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        original_run_id=RUN,original_artifact_id=ARTIFACT,original_artifact_sha256=DIGEST,source_api_sha256=sha(a.api),
        original_manifest_sha256=sha(source/'hosted-native-provider.json'),runtime_root=str(base),members=sealed['members'],
        actual_original_package_inventory_sha256=sha(base/'system-packages.txt'),stock_runtime_qualification_pending=True,
        phase6_complete=False,native_admission_qualified=False)
    a.output.write_text(json.dumps(record,indent=2)+'\n');print(record['status'])


if __name__=='__main__':main()
