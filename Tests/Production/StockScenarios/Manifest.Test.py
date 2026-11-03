#!/usr/bin/env python3
"""Reject loss of a non-focus ship even when all sixty frames complete normally."""
import argparse
import csv
import json
from pathlib import Path
import tempfile

from inventory import digest,require
from run import inspect,rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'All-object control output exists')
    manifest=json.loads(a.manifest.read_text())
    name='2024 Edition/Spotlights.scn';case=manifest['cases'][name]
    require(case['status']=='passed' and a.capture.name==case['output'],'Control requires complete real Spotlights capture')
    before=digest(a.capture/'flight-state.csv')
    require(inspect(a.capture,case,0)['status']=='passed','Positive all-object capture is invalid')
    with tempfile.TemporaryDirectory(prefix='orbiter-stock-manifest-') as temporary:
        view=Path(temporary)
        for file in a.capture.iterdir():
            if file.is_file() and file.name!='flight-state.csv':(view/file.name).symlink_to(file.resolve())
        samples=rows(a.capture/'flight-state.csv')
        omitted=next(r for r in samples if r['tick']=='30' and r['object']!=r['focus'])
        samples.remove(omitted)
        with (view/'flight-state.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
        failed=inspect(view,case,0)
    require(failed['status']=='failed' and any('vessel manifest at tick 30' in s for s in failed['problems']),
            'Missing non-focus ship was accepted')
    require(digest(a.capture/'flight-state.csv')==before,'Original complete capture changed')
    result=dict(status='passed',source_sha256=digest(Path(__file__)),capture_sha256=before,
        omitted=dict(tick=30,object=omitted['object'],focus=omitted['focus']),
        incomplete_manifest_rejected=True,original_capture_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Missing non-focus ship rejected despite normal presentation/teardown')


if __name__=='__main__':main()
