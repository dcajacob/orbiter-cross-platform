#!/usr/bin/env python3
"""Require four clean native production terrain builds and frozen parity."""
import argparse
import json
from pathlib import Path
from frozen_reference import load
from capture import compare,require

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();metadata,golden=load();builds={};sources=set()
    for path in args.evidence.rglob('comparison.json'):
        report=json.loads(path.read_text());key=(report['host'].split('-')[0],report['configuration'])
        require(key not in builds and report['status']=='passed' and not report['working_tree_dirty'],'invalid/duplicate native terrain build')
        require(report['protocol_sha256_lf']==metadata['protocol_sha256_lf'],'terrain protocol differs')
        traces={}
        for mode in ('1','2'):
            first=(path.parent/f'mode-{mode}-trace-1.csv').read_bytes()
            require(first==(path.parent/f'mode-{mode}-trace-2.csv').read_bytes(),'hosted terrain repeats differ')
            compare(golden[mode],first);traces[mode]=first
        builds[key]=traces;sources.add(report['source'])
    require(set(builds)=={(host,config) for host in ('Linux','Windows') for config in ('Debug','Release')} and len(sources)==1,
        'all four same-source production terrain builds are required')
    first=next(iter(builds.values()))
    results=[dict(host=key[0],configuration=key[1],modes={mode:compare(first[mode],traces[mode]) for mode in ('1','2')})
        for key,traces in sorted(builds.items())]
    args.report.write_text(json.dumps(dict(status='passed',source=next(iter(sources)),results=results,
        protocol_sha256_lf=metadata['protocol_sha256_lf'],scope='direct production terrain queries; not a native world or renderer'),indent=2)+'\n')
    print('Four production terrain builds and repeats match frozen Windows within unchanged budgets')

if __name__=='__main__':main()
