#!/usr/bin/env python3
"""Reject missing background stations and docking ports in copied real captures."""
import argparse
import csv
import json
from pathlib import Path
import tempfile

from original import select_suite,settings_path
from original import HERE,digest,inspect_trace,require,rows,settings,source_digest


def write(path,samples):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',choices=('stations','shuttle-a'),default='stations')
    p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();select_suite(a.suite);require(not a.output.exists(),'Station gate-control output exists')
    config=settings();case=config['cases'][0]
    require(a.capture.name==case['id']+'-1','Control requires the first real original station capture')
    names=('stock-vessel-state.csv','stock-vessel-docks.csv')
    before={name:digest(a.capture/name) for name in names}
    inspect_trace(a.capture,case,config)
    state,docks=[rows(a.capture/name) for name in names]
    station=next(r for r in state if r['tick']=='30' and r['focus']=='0' and (r['class'].lower() in ('mir','wheel') if a.suite=='stations' else int(r['docks'])>0))
    port=next(r for r in docks if r['tick']=='30' and r['object']==station['object'])
    rejected=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-station-gate-') as temporary:
        view=Path(temporary)
        for kind in ('vessel','dock'):
            write(view/names[0],[r for r in state if kind!='vessel' or r is not station])
            write(view/names[1],[r for r in docks if kind!='dock' or r is not port])
            try:inspect_trace(view,case,config)
            except ValueError as error:
                expected='vessel manifest differs' if kind=='vessel' else 'docking-port observations'
                require(expected in str(error),'Station negative control failed for another reason')
                rejected.append(kind)
    require(rejected==['vessel','dock'],'Incomplete station observation was accepted')
    require(before=={name:digest(a.capture/name) for name in names},'Original station capture changed')
    a.output.write_text(json.dumps(dict(status='passed',source_sha256_lf=source_digest(Path(__file__)),
        capture_sha256=before,missing_nonfocus_station_rejected=True,missing_port_rejected=True,
        original_capture_unchanged=True),indent=2)+'\n')
    print('Missing non-focus station and docking port rejected; original capture unchanged')


if __name__=='__main__':main()
