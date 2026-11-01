#!/usr/bin/env python3
"""Verify preserved hosted native evidence without generating expected traces."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent))
from frozen_reference import load
from capture import compare,require

def sha(data): return hashlib.sha256(data).hexdigest()
def local(root,name):
    relative=PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts,'invalid evidence path')
    path=(root/relative).resolve()
    require(path.is_relative_to(root.resolve()),'evidence escapes its root')
    return path

def verify():
    _,golden=load()
    provenance=json.loads((HERE/'provenance.json').read_text())
    require(provenance['status']=='passed' and provenance['run_id']==41291123424,'hosted evidence identity differs')
    builds=set();parity=None
    require(len(provenance['artifacts'])==5,'missing hosted native SPICE artifacts')
    for record in provenance['artifacts']:
        path=local(HERE,record['file'])
        require(sha(path.read_bytes())==record['sha256'],'preserved native artifact changed')
        members={}
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None,'corrupt native evidence')
            stored=set()
            for member in record['members']:
                if 'storage' in member:
                    storage=member['storage']
                    require(storage['kind']=='existing_zip_member','unknown trace deduplication')
                    with zipfile.ZipFile(local(ROOT,storage['archive'])) as source:
                        data=source.read(storage['member'])
                else:
                    stored.add(member['path']);data=archive.read(member['path'])
                require(sha(data)==member['sha256'] and len(data)==member['bytes'],'native evidence member changed')
                require(member['path'] not in members,'duplicate native evidence member')
                members[member['path']]=data
            require(len(archive.namelist())==len(stored) and set(archive.namelist())==stored,'unmanifested native evidence')
        if record['name']=='native-spice-parity':
            parity=json.loads(members['native-spice-parity.json'])
        else:
            report=json.loads(members['out/spice-observation/comparison.json'])
            require(report['status']=='passed' and report['source']==provenance['source'] and
                report['working_tree_dirty'] is False,'native execution provenance differs')
            first=members['out/spice-observation/trace-1.csv']
            require(first==members['out/spice-observation/trace-2.csv']==golden,'native/original traces differ')
            compare(golden,first)
            builds.add((report['host'].split('-')[0],report['configuration']))
    require(builds=={(host,config) for host in ('Linux','Windows') for config in ('Debug','Release')},'native coverage differs')
    require(parity and parity['status']=='passed' and parity['source']==provenance['source'],'cross-platform comparison differs')
    print('Verified all four hosted native SPICE builds: repeated traces are byte-identical to frozen original Windows')

if __name__=='__main__': verify()
