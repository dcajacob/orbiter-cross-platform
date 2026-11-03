#!/usr/bin/env python3
"""Recompute the full desktop performance matrix and verify fixed physics repeats."""
import argparse
import json
from pathlib import Path

from run import HERE, ROOT, audit, digest, require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('wayland', 'x11', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a=p.parse_args()
    require(not a.output.exists(), 'Performance audit output exists')
    profile=json.loads((HERE/'cases.json').read_text())
    expected={c['id']+'-'+str(repeat):c for c in profile['cases'] for repeat in range(1, profile['repeats']+1)}
    frames=profile['warmup_frames']+profile['sample_frames']
    result=dict(status='failed', phase6_complete=False, profile_sha256=digest(HERE/'cases.json'),
                source_sha256=digest(Path(__file__)), runs=[], identical_physics={}, method='Every declared interval; nearest-rank p95; per-run limits')
    inputs=[]
    physics={c['id']:set() for c in profile['cases']}
    try:
        for backend,base in (('wayland',a.wayland),('x11',a.x11)):
            manifest=json.loads((base/'performance-report.json').read_text())
            require(manifest['status']=='passed' and not manifest['smoke'] and manifest['backend']==backend and
                    manifest['profile_sha256']==result['profile_sha256'] and
                    manifest['warmup_frames']==profile['warmup_frames'] and
                    manifest['sample_frames']==profile['sample_frames'] and manifest['repeats']==profile['repeats'] and
                    set(manifest['cases'])==set(expected), 'Incomplete or smoke-only desktop matrix')
            for source,checksum in manifest['source_sha256'].items():
                require(digest(ROOT/source)==checksum, 'Benchmark source changed: '+source)
            inputs.append(manifest['inputs_sha256'])
            for name,case in expected.items():
                out=base/name
                recorded=manifest['cases'][name]
                for file,checksum in recorded['files_sha256'].items():
                    require(digest(out/file)==checksum, 'Recorded performance artifact changed: '+str(out/file))
                recomputed=audit(out,profile,backend,frames,profile['warmup_frames'],profile['sample_frames'],case)
                require(recomputed['status']=='passed' and all(recorded[k]==v for k,v in recomputed.items()),
                        'Recomputed frame-time gate differs or fails')
                require(recorded['scenario']==case['scenario'] and recorded['scenario_sha256']==case['sha256'] and
                        digest(ROOT/'Scenarios'/case['scenario'])==case['sha256'], 'Stock scenario identity differs')
                physics[case['id']].add(digest(out/'flight-state.csv'))
                priming=out/'window-priming.json'
                result['runs'].append(dict(backend=backend,case=name,path=str(out),
                    cadence=recomputed['cadence'],poll_to_present=recomputed['poll_to_present'],
                    swap=recomputed['swap'],window=recomputed['window'],cockpit_viewport=recomputed['cockpit_viewport'],renderer=recomputed['renderer'],
                    lifecycle=recomputed['lifecycle'],focused_frames=recomputed['focused_frames'],
                    host_before=recorded['host_before'],host_after=recorded['host_after'],
                    startup_priming=json.loads(priming.read_text()) if priming.exists() else None,
                    files_sha256=recorded['files_sha256'],
                    report_sha256=digest(out/'performance.json')))
        require(inputs[0]==inputs[1], 'Desktop backends used different application binaries')
        for name,checksums in physics.items():
            require(len(checksums)==1, 'Fixed physics differs across repetitions or desktop backends: '+name)
            result['identical_physics'][name]=next(iter(checksums))
        result.update(status='passed',inputs_sha256=inputs[0],processes=len(result['runs']),
            measured_intervals=len(result['runs'])*profile['sample_frames'],
            scene_presents=len(result['runs'])*frames,
            worst_median_ms=max(r['cadence']['median_ms'] for r in result['runs']),
            worst_p95_ms=max(r['cadence']['p95_ms'] for r in result['runs']))
    except BaseException as error:
        result['error']=str(error)
        raise
    finally:
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','processes','measured_intervals','worst_median_ms','worst_p95_ms')}))


if __name__=='__main__':
    main()
