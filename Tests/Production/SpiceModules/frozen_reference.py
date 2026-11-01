#!/usr/bin/env python3
"""Read accepted Windows module evidence; never write or refresh a reference."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import zipfile
from capture import HERE,protocol,rows,compare,require

def load():
    directory=HERE/'Reference'
    metadata=json.loads((directory/'provenance.json').read_text())
    require(metadata['status']=='accepted' and metadata['automatic_refresh'] is False,'Windows SPICE reference not accepted')
    require(hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest()==metadata['protocol_sha256'],'accepted SPICE protocol changed')
    protocol();traces=[];configurations=set()
    for record in metadata['evidence']:
        name=PurePosixPath(record['file'])
        require(not name.is_absolute() and '..' not in name.parts,'invalid SPICE reference path')
        path=directory/name
        require(hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'accepted SPICE artifact changed')
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None and set(archive.namelist())==set(record['members_sha256']) and
                len(archive.namelist())==len(record['members_sha256']),'SPICE artifact members differ')
            for member,checksum in record['members_sha256'].items():
                require(hashlib.sha256(archive.read(member)).hexdigest()==checksum,'SPICE artifact member changed')
            report=json.loads(archive.read(record['capture_member']))
            require(report['status']=='passed' and report['configuration']==record['configuration'] and
                report['source']==record['source'] and report['runtime_source']==protocol()['runtime_source'] and
                report['protocol_sha256']==metadata['protocol_sha256'],'SPICE capture provenance differs')
            first,second=(archive.read(member) for member in record['trace_members'])
            require(first==second,'accepted Windows SPICE repeats differ');rows(first)
            traces.append(first);configurations.add(record['configuration'])
    require(len(traces)==2 and configurations=={'Debug','Release'},'both Windows SPICE configurations are required')
    compare(*traces)
    return metadata,traces[0]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args();metadata,golden=load()
    report=compare(golden,args.candidate.read_bytes()) if args.candidate else dict(status='passed')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
