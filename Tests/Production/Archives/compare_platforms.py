#!/usr/bin/env python3
"""Require all four full stock archive runs and exact cross-platform parity."""
import argparse
import json
from pathlib import Path
from frozen_reference import compare,load
from observations import require

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    provenance,golden=load()
    reports={}
    sources=set()
    for path in sorted(args.evidence.rglob('comparison.json')):
        report=json.loads(path.read_text())
        key=(report['host'].split('-')[0],report['configuration'])
        require(key not in reports,'duplicate archive platform/configuration')
        compare(golden,report)
        sources.add(report['source']);reports[key]=report
    require(set(reports)=={(host,config) for host in ('Linux','Windows') for config in ('Debug','Release')},
            'all four full stock archive builds are required')
    require(len(sources)==1,'archive builds used different sources')
    for report in reports.values():compare(next(iter(reports.values())),report)
    result=dict(status='passed',source=next(iter(sources)),archives=30,queries_per_run=1200,
        configurations=[dict(host=key[0],configuration=key[1]) for key in sorted(reports)],
        comparison='exact integer identities and decoded bytes',reference=provenance['evidence'],
        scope='actual shared production archive reader, not native world/terrain acceptance')
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print('Four shared production archive builds agree exactly with original Windows')

if __name__=='__main__':main()
