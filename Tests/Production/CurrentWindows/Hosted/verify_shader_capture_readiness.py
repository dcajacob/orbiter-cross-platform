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

CONTROL_NAME='shader-source-complete-current-stock-controls'
CONTROL_ID=13660628419
CONTROL_SIZE=19011
CONTROL_DIGEST='sha256:80d9eb00833fb1615deae555f8bff541520f549c3513b67ad4fa7601dfc20a05'


def verify(record):
    artifacts=record['artifacts']
    names={'shader-source-complete-current-stock-'+'-'.join(cell) for cell in EXPECTED}
    require(len(artifacts)==9 and {a['name'] for a in artifacts}==names|{CONTROL_NAME} and
            len({a['id'] for a in artifacts})==9,
            'Exact eight capture cells plus the distinct preserved control artifact required')
    control=next(a for a in artifacts if a['name']==CONTROL_NAME)
    require(control['id']==CONTROL_ID and control['size_in_bytes']==CONTROL_SIZE and control['digest']==CONTROL_DIGEST and
            control['expired'] is False and control['workflow_run']['id']==RUN and control['workflow_run']['head_sha']==CAPTURE,
            'Exact successful capture-control API artifact required')
    selected=[a for a in artifacts if a['name'] in names]
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
        actual_capture_cells=cells,actual_capture_control_artifact=control,physical_comparisons_pending=True,native_comparisons_pending=True,
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
