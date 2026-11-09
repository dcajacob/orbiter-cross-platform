#!/usr/bin/env python3
"""Seal only the separate Mesa repair and all original/new control evidence."""
import json
from pathlib import Path
import subprocess
import tarfile
from contracts import ROOT,require,sha,load,atomic_json


def main():
    base=ROOT/'out/hosted-mesa-topology';require(base.is_dir(),'Actual separate Mesa repair output required')
    report=load(base/'build.json');archive=base.with_suffix('.tar.gz');require(not archive.exists(),'Fresh separate Mesa repair archive required')
    members={}
    for path in base.rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(base);parts=relative.parts
        keep=parts[0] in {'cpu-controls','allocator-controls'} or 'install' in parts or path.suffix in {'.json','.log','.txt','.xml'} or relative.as_posix()=='mesa/mesa-26.0.8/src/util/u_cpu_detect.c'
        if not keep:continue
        require(path.resolve().is_relative_to(base),'Separate Mesa repair link escaped its owning output')
        members[path.relative_to(ROOT).as_posix()]=dict(sha256=sha(path),symlink=path.readlink().as_posix() if path.is_symlink() else None)
    require(members,'Actual separate Mesa repair evidence missing')
    with tarfile.open(archive,'w:gz',compresslevel=3) as target:
        for name in sorted(members):target.add(ROOT/name,arcname=name,recursive=False)
    require(all(sha(ROOT/name)==value['sha256'] for name,value in members.items()),'Separate repair evidence changed during retention')
    complete=report['status']=='built-Mesa-topology-cleanup-and-passed-dependency-controls-only' and set(report['controls'])=={'allocator','cpu-owner','egl'} and all(v['status']=='passed' and sha(v['path'])==v['sha256'] for v in report['controls'].values())
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(report['source_commit']==producer and not subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','HEAD','--'],text=True).strip(),'Actual immutable Mesa repair collector changed')
    result=dict(protocol='phase6-hosted-Mesa-topology-provider-v1',status='built-and-dependency-controls-only' if complete else 'failed-or-incomplete-unqualified',
        compiled_mesa_source=producer,original_provider_source=report['original_provider_source'],original_provider_restoration_sha256=sha(ROOT/'out/native-provider-restoration/restoration.json'),
        build_sha256=sha(base/'build.json'),container_receipt_sha256=sha(ROOT/'out/mesa-topology-container.json'),
        archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,members=members,controls=report['controls'],
        runtime_qualification_pending=True,full_stock_capture_pending=True,native_admission_qualified=False,phase6_complete=False)
    atomic_json(ROOT/'out/hosted-mesa-topology.json',result)
    require(complete,'All partial Mesa repair evidence retained; dependency controls did not pass')
    print(result['status'])


if __name__=='__main__':main()
