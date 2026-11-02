#!/usr/bin/env python3
"""Verify and stage explicitly accepted Windows cockpit evidence, without refresh."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from mesa_runtime import digest,require

BUDGETS=dict(position_m=.01,velocity_m_s=1e-5,rotation_rad=1e-8,
             angular_velocity_rad_s=1e-10,mjd_days=1e-10,
             propellant_relative=1e-8,propellant_absolute_kg=1e-8)
RELEASE='https://github.com/dcajacob/orbiter-cross-platform/releases/download/production-windows-cockpit-v1/'

def metadata(path):
    record=json.loads(path.read_text())
    require(record['status']=='accepted' and record['automatic_refresh'] is False,'Cockpit reference gate is not accepted')
    require(record['budgets']==BUDGETS and record['image_ssim_minimum']==.98,'Frozen cockpit budgets changed')
    for name,checksum in record['input_files_sha256_lf'].items():
        file=(ROOT/name).resolve()
        require(ROOT in file.parents and hashlib.sha256(file.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==checksum,'Frozen cockpit input changed: '+name)
    require(set(record['artifacts'])=={'Debug','Release','comparison'},'Incomplete accepted Windows cockpit artifacts')
    with subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as reader:
        for name,checksum in record['source_files_sha256_lf'].items():
            require('\n' not in name,'Invalid source path')
            reader.stdin.write((record['source_commit']+':'+name+'\n').encode());reader.stdin.flush()
            header=reader.stdout.readline().split()
            require(len(header)==3 and header[1]==b'blob','Pinned cockpit source unavailable; full Git history is required: '+name)
            source=reader.stdout.read(int(header[2]));require(reader.stdout.read(1)==b'\n','Incomplete pinned cockpit source')
            require(hashlib.sha256(source.replace(b'\r\n',b'\n')).hexdigest()==checksum,'Pinned cockpit source differs: '+name)
        reader.stdin.close();require(reader.wait()==0,'Cockpit source verification failed')
    return record

def obtain(entry,cache,offline):
    name=entry['name']+'.zip'
    require(Path(name).name==name,'Invalid cockpit archive filename')
    destination=cache/name
    if not destination.exists():
        require(not offline,'Offline cockpit archive missing: '+str(destination))
        cache.mkdir(parents=True,exist_ok=True)
        temporary=cache/(name+'.partial')
        try:
            with urllib.request.urlopen(RELEASE+name,timeout=120) as source,temporary.open('wb') as target:
                shutil.copyfileobj(source,target)
            require(digest(temporary)==entry['sha256'],'Downloaded accepted cockpit archive digest differs')
            temporary.replace(destination)
        finally:temporary.unlink(missing_ok=True)
    require(digest(destination)==entry['sha256'],'Cached accepted cockpit archive digest differs: '+name)
    return destination

def stage(record,cache,output,offline=False):
    require(not output.exists(),'Cockpit reference output exists; replacement is forbidden')
    archives={name:obtain(entry,cache,offline) for name,entry in record['artifacts'].items()}
    output.mkdir(parents=True)
    for configuration in ('Debug','Release'):
        entry=record['artifacts'][configuration]
        with zipfile.ZipFile(archives[configuration]) as archive:
            for name,checksum in record['reference_files_sha256'][configuration].items():
                target=(output/configuration/name).resolve()
                require((output/configuration).resolve() in target.parents,'Invalid frozen cockpit file path')
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.read('out/cockpit-reference/'+name))
                require(digest(target)==checksum,'Accepted cockpit reference file differs: '+name)
    with zipfile.ZipFile(archives['comparison']) as archive:
        comparison=json.loads(archive.read('cockpit-comparison.json'))
        require(comparison['status']=='passed' and set(comparison['cases'])==set(record['cases']),'Original cockpit comparison is incomplete')
    (output/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    return dict(status='passed',run_id=record['run_id'],application_source=record['application_source'],cases=len(record['cases']))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,default=Path(__file__).with_name('Reference')/'provenance.json')
    p.add_argument('--cache',type=Path);p.add_argument('--output',type=Path);p.add_argument('--offline',action='store_true')
    a=p.parse_args();record=metadata(a.reference)
    require(bool(a.cache)==bool(a.output),'--cache and --output must be provided together')
    result=stage(record,a.cache,a.output,a.offline) if a.output else dict(status='passed',run_id=record['run_id'])
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
