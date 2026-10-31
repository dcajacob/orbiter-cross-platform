#!/usr/bin/env python3
"""Verify explicitly accepted behavioral evidence; never update references."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import tempfile
import zipfile

from mesa_runtime import digest,require

ROOT=Path(__file__).resolve().parent


def load_reference(directory):
    metadata=json.loads((directory/'provenance.json').read_text())
    require(metadata['status']=='accepted' and metadata['automatic_refresh'] is False,'behavior references have not been accepted')
    require(digest(ROOT/'behavior-cases.json')==metadata['case_manifest_sha256'],'frozen behavior fixtures or budgets changed')
    manifest=json.loads((ROOT/'behavior-cases.json').read_text())
    require(manifest['budgets']==metadata['budgets'],'frozen behavior budgets changed')
    for name,checksum in metadata['input_profiles_sha256'].items():
        require(digest(ROOT/name)==checksum,'frozen behavioral data profile changed: '+name)
    for config,record in metadata['artifacts'].items():
        path=(directory/record['path']).resolve()
        require(ROOT in path.parents and digest(path)==record['sha256'],'frozen behavior ZIP changed: '+config)
        with zipfile.ZipFile(path) as archive:
            for name,checksum in record['members_sha256'].items():
                require(hashlib.sha256(archive.read(name)).hexdigest()==checksum,'frozen behavior member changed: '+name)
    comparison=(directory/metadata['comparison']['path']).resolve()
    require(ROOT in comparison.parents and digest(comparison)==metadata['comparison']['sha256'],
            'frozen hosted comparison evidence changed')
    return metadata


def compare_capture(directory,candidate,configuration):
    from behavior_suite import compare,validate,persistence_round_trip
    metadata=load_reference(directory)
    record=metadata['artifacts'][configuration]
    manifest=json.loads((ROOT/'behavior-cases.json').read_text())
    report=dict(status='pending',capture_commit=metadata['driver_source_commit'],cases={})
    with tempfile.TemporaryDirectory(prefix='orbiter-behavior-') as temporary:
        base=Path(temporary)
        with zipfile.ZipFile(directory/record['path']) as archive:
            for name in record['members_sha256']:
                rel=PurePosixPath(name)
                require(not rel.is_absolute() and '..' not in rel.parts,'invalid behavior archive member')
                path=base.joinpath(*rel.parts);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(name))
        for case in manifest['cases']:
            validate(candidate/case['id'],case)
            report['cases'][case['id']]=compare(base/'production-behavior'/case['id'],candidate/case['id'],case)
        report['stock_serialization_round_trip']=persistence_round_trip(candidate/'dg_persistence',candidate/'dg_reload')
    report['status']='passed'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT/'BehaviorReference')
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--configuration',choices=('Debug','Release'),default='Release')
    args=parser.parse_args()
    result=compare_capture(args.reference,args.candidate,args.configuration) if args.candidate else dict(status='passed',capture_commit=load_reference(args.reference)['driver_source_commit'])
    if args.candidate:(args.candidate/'frozen-behavior-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
