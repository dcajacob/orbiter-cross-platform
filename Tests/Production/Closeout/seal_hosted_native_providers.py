#!/usr/bin/env python3
"""Retain dependency runtimes and raw control/failure evidence without acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from contracts import ROOT,require,sha,atomic_json


def control_status(base,producer,image):
    control_files={'fontconfig':base/'fontconfig-controls/verification.json','gdk':base/'gdk-controls/verification.json','mesa':base/'mesa-controls/report.json'}
    controls={name:dict(path=str(path),sha256=sha(path),status=json.loads(path.read_text()).get('status')) if path.is_file() else None for name,path in control_files.items()}
    marker=base/'completed.json';completed=json.loads(marker.read_text()) if marker.is_file() else {}
    complete=completed==dict(status='completed-existing-dependency-controls-only',source_commit=producer,container_digest=image,phase6_complete=False) and all(c is not None and c['status']=='passed' for c in controls.values())
    return complete,controls


def retain_receipt(base,report):
    # Docker-created provider trees may be readable but not writable by the host.
    atomic_json(base.parent/'hosted-native-provider.json',report)


def main():
    base=ROOT/'out/hosted-native-providers';require(base.is_dir(),'Actual provider output required')
    archive=base.with_suffix('.tar.gz');require(not archive.exists(),'Fresh provider archive required')
    members={}
    full={'cache','compositor','fontconfig-controls','gdk-controls','mesa-controls'}
    for path in base.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(base);parts=relative.parts
        keep=parts[0] in full or 'install' in parts or path.suffix in ('.json','.log','.txt') or path.name=='libdecor-gtk.so'
        if not keep:continue
        require(path.resolve().is_relative_to(base),'Provider member/symlink escaped its owning output')
        members[path.relative_to(ROOT).as_posix()]=dict(sha256=sha(path),symlink=path.readlink().as_posix() if path.is_symlink() else None)
    require(members,'No actual provider evidence')
    with tarfile.open(archive,'w:gz',compresslevel=3) as target:
        for name in sorted(members):target.add(ROOT/name,arcname=name,recursive=False)
    require(all(sha(ROOT/name)==item['sha256'] for name,item in members.items()),'Actual provider bytes changed during retention')
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(not subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','HEAD','--'],text=True).strip(),'Owning tracked provider source changed')
    lock=json.loads((ROOT/'Tests/Production/Closeout/native-provider-container.lock.json').read_text())
    image='ubuntu@'+lock['image_digest']
    actual_image=json.loads((ROOT/'out/native-provider-container.json').read_text())
    require(len(actual_image)==1 and any(d.endswith('@'+lock['image_digest']) for d in actual_image[0]['RepoDigests']),
            'Actual Docker image does not match the official pinned userspace')
    complete,controls=control_status(base,producer,image)
    report=dict(protocol='phase6-hosted-native-provider-package-v1',status='built-and-dependency-controls-only' if complete else 'failed-or-incomplete-unqualified',
        source_commit=producer,actual_container_receipt_sha256=sha(ROOT/'out/native-provider-container.json'),container_lock_sha256=sha(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json'),
        archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,members=members,controls=controls,
        runtime_qualification_pending=True,full_stock_capture_pending=True,native_admission_qualified=False,phase6_complete=False)
    retain_receipt(base,report)
    require(complete,'Retained failed/incomplete provider evidence; no runtime qualification')
    print(report['status'])


if __name__=='__main__':main()
