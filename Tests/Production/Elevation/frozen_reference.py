#!/usr/bin/env python3
"""Read the frozen original Windows terrain evidence; never regenerate it."""
import hashlib
import json
from pathlib import PurePosixPath
import zipfile
from capture import HERE,protocol,compare,require,rows

def load():
    lock=protocol();directory=HERE/'Reference';metadata=json.loads((directory/'provenance.json').read_text())
    require(metadata['status']=='accepted' and metadata['automatic_refresh'] is False,'original terrain reference is not accepted')
    require(metadata['runtime_source']==lock['runtime_source'] and
        hashlib.sha256((HERE/'protocol.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest()==metadata['protocol_sha256_lf'],
        'original terrain protocol/runtime changed')
    builds={};comparison=None
    for entry in metadata['evidence']:
        relative=PurePosixPath(entry['file'])
        require(not relative.is_absolute() and '..' not in relative.parts,'invalid original terrain artifact path')
        path=directory/relative
        require(path.stat().st_size==entry['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],
            'original terrain artifact changed')
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None and len(archive.namelist())==len(entry['members_sha256']) and
                set(archive.namelist())==set(entry['members_sha256']),'original terrain artifact members differ')
            for name,expected in entry['members_sha256'].items():
                require(hashlib.sha256(archive.read(name)).hexdigest()==expected,'original terrain evidence member changed')
            if 'comparison_member' in entry:
                comparison=json.loads(archive.read(entry['comparison_member']));continue
            report=json.loads(archive.read(entry['capture_member']))
            require(report['status']=='passed' and report['configuration']==entry['configuration'] and
                report['source']==metadata['observer_source'] and report['runtime_source']==metadata['runtime_source'] and
                report['protocol_sha256_lf']==metadata['protocol_sha256_lf'],'original terrain capture identity differs')
            traces={}
            for mode,members in entry['trace_members'].items():
                first,second=(archive.read(name) for name in members)
                require(first==second,'frozen terrain repeats differ');observations=rows(first)
                require({row['mode'] for row in observations}=={mode},'terrain mode differs')
                traces[mode]=first
            require(entry['configuration'] not in builds,'duplicate terrain configuration')
            builds[entry['configuration']]=traces
    require(set(builds)=={'Debug','Release'} and comparison and comparison['status']=='passed' and
        comparison['source']==metadata['observer_source'] and comparison['protocol_sha256_lf']==metadata['protocol_sha256_lf'],
        'both original terrain configurations and comparison are required')
    for mode in ('1','2'):compare(builds['Debug'][mode],builds['Release'][mode])
    return metadata,builds['Debug']

if __name__=='__main__':
    load();print('Verified frozen original Windows heights, normals, levels and repeats in linear/cubic modes')
