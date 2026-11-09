#!/usr/bin/env python3
"""Validate all eight actual closed shader-source capture API artifacts before any audit."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/Closeout')]
from contracts import require,load,atomic_json
from inspect_source_complete_shader_phase import api_identity,EXPECTED,CAPTURE,RUN


def verify(record):
    artifacts=record['artifacts']
    names={'shader-source-complete-current-stock-'+'-'.join(cell) for cell in EXPECTED}
    selected=[a for a in artifacts if a['name'].startswith('shader-source-complete-current-stock-')]
    require(len(selected)==8 and {a['name'] for a in selected}==names and
            len({a['id'] for a in selected})==8,'All eight distinct actual complete shader capture artifacts required')
    require(all('self-hosted' not in job['labels'] for job in record['jobs']),
            'Only standard GitHub-hosted capture runners are authorized')
    cells={}
    for cell in sorted(EXPECTED):
        artifact=next(a for a in selected if a['name']=='shader-source-complete-current-stock-'+'-'.join(cell))
        job=api_identity(dict(repository=record['repository'],run=record['run'],jobs=record['jobs'],artifact=artifact),cell)
        cells['-'.join(cell)]=dict(job_id=job['id'],artifact=artifact)
    return dict(protocol='phase6-independent-shader-current-capture-readiness-v1',
        status='verified-all-eight-closed-current-source-API-cells-only',capture_source=CAPTURE,capture_run_id=RUN,
        actual_capture_cells=cells,physical_comparisons_pending=True,native_comparisons_pending=True,
        phase6_complete=False,native_admission_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args()
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform' and os.environ.get('ImageOS')=='ubuntu24',
            'Actual standard hosted Ubuntu24 readiness required')
    require(not a.output.exists(),'Fresh independent readiness output required')
    result=verify(load(a.api));atomic_json(a.output,result);print(result['status'])


if __name__=='__main__':main()
