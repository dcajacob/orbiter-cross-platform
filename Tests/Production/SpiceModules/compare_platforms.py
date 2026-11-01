#!/usr/bin/env python3
"""Require actual native-module observations from all four hosted builds."""
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
        record=json.loads(path.read_text());key=(record['host'].split('-')[0],record['configuration'])
        require(key not in builds and record['status']=='passed' and not record['working_tree_dirty'],'invalid/duplicate native SPICE build')
        first=(path.parent/'trace-1.csv').read_bytes();second=(path.parent/'trace-2.csv').read_bytes()
        require(first==second,'hosted native SPICE repeats differ');compare(golden,first)
        sources.add(record['source']);builds[key]=first
    require(set(builds)=={(host,config) for host in ['Linux','Windows'] for config in ['Debug','Release']} and len(sources)==1,
        'all four native module platform/configuration builds from the same source are required')
    comparisons=[compare(next(iter(builds.values())),data) for data in builds.values()]
    result=dict(status='passed',source=next(iter(sources)),scope='actual native production SPICE callbacks; not a world or renderer',
        builds=[dict(host=k[0],configuration=k[1]) for k in sorted(builds)],comparisons=comparisons,
        frozen_protocol_sha256_lf=metadata['protocol_sha256_lf'])
    args.report.write_text(json.dumps(result,indent=2)+'\n');print('All four native SPICE module builds match original Windows within unchanged budgets')

if __name__=='__main__':main()
