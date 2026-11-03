#!/usr/bin/env python3
"""Prove that a valid low-median trace fails the unchanged p95 performance gate."""
import argparse
import csv
import json
from pathlib import Path
import tempfile

from run import HERE, audit, digest, require, rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    require(not a.output.exists(),'Performance gate control output exists')
    profile=json.loads((HERE/'cases.json').read_text())
    case=next(c for c in profile['cases'] if c['id']=='landed_exterior')
    frames=profile['warmup_frames']+profile['sample_frames']
    source=a.capture/'frame-times.csv'
    before=digest(source)
    original=audit(a.capture,profile,'wayland',frames,profile['warmup_frames'],profile['sample_frames'],case)
    require(original['status']=='passed','Gate control requires a valid complete capture')
    with tempfile.TemporaryDirectory(prefix='orbiter-performance-gate-') as temporary:
        view=Path(temporary)
        for file in a.capture.iterdir():
            if file.is_file() and file.name!='frame-times.csv':(view/file.name).symlink_to(file.resolve())
        timings=rows(source)
        warmup=profile['warmup_frames']
        previous=int(timings[warmup-1]['present_end_ns'])
        # 91 of 1800 intervals are 51 ms. The median is 16 ms but nearest-rank
        # p95 is 51 ms. No original capture or acceptance limit is changed.
        for index in range(warmup,frames):
            duration=51_000_000 if index>=frames-91 else 16_000_000
            end=previous+duration
            timings[index].update(loop_start_ns=str(previous+1000),swap_start_ns=str(end-1000),present_end_ns=str(end))
            previous=end
        with (view/'frame-times.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(timings[0]));writer.writeheader();writer.writerows(timings)
        negative=audit(view,profile,'wayland',frames,warmup,profile['sample_frames'],case)
    require(negative['cadence']['median_ms']==16 and negative['cadence']['p95_ms']==51 and
            negative['status']=='failed','Over-budget p95 was accepted despite a passing median')
    require(digest(source)==before,'Original performance capture changed')
    result=dict(status='passed',source_sha256=digest(Path(__file__)),capture_sha256=before,
                positive=original['cadence'],negative=negative['cadence'],
                negative_rejected=True,original_capture_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Median-only false pass rejected by the unchanged p95 gate')


if __name__=='__main__':
    main()
