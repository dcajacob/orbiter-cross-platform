#!/usr/bin/env python3
"""Reject damaged copies of actual SDK clock and vessel observations."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from clock_observation import inspect_clock,require,rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    p.add_argument('--frames',type=int,default=960)
    a=p.parse_args();require(not a.output.exists() and a.frames>=2,'Fresh clock-control output and at least two actual frames required')
    names=('stock-clock.csv','stock-vessel-state.csv')
    def hashes(root):return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
    before=hashes(a.capture);positive=inspect_clock(a.capture,a.frames);controls=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-stock-clock-control-') as temporary:
        for name in ('missing_tick','reordered_ticks','nonfinite_clock','system_clock_regression',
                     'different_vessel_snapshot','missing_clock_column','zero_system_step','zero_acceleration'):
            out=Path(temporary)/name;out.mkdir()
            for filename in names:shutil.copy2(a.capture/filename,out/filename)
            values=rows(out/'stock-clock.csv');fields=list(values[0])
            if name=='missing_tick':del values[1]
            elif name=='reordered_ticks':values[1],values[2]=values[2],values[1]
            elif name=='nonfinite_clock':values[1]['system_seconds']='nan'
            elif name=='system_clock_regression':values[2]['system_seconds']=str(float(values[0]['system_seconds'])-1)
            elif name=='different_vessel_snapshot':values[-1]['simulation_seconds']=str(float(values[-1]['simulation_seconds'])+.125)
            elif name=='missing_clock_column':
                fields.remove('system_step')
                for row in values:del row['system_step']
            elif name=='zero_system_step':values[1]['system_step']='0'
            elif name=='zero_acceleration':values[1]['time_acceleration']='0'
            with (out/'stock-clock.csv').open('w',newline='') as target:
                writer=csv.DictWriter(target,fieldnames=fields);writer.writeheader();writer.writerows(values)
            try:inspect_clock(out,a.frames)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged SDK clock observation accepted: '+name)
    require(hashes(a.capture)==before,'Owning SDK clock or vessel observations changed')
    source=Path(__file__)
    a.output.write_text(json.dumps(dict(status='passed',positive=positive,controls=controls,
        owning_capture_files_sha256=before,owning_capture_unchanged=True,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        reader_sha256=hashlib.sha256((source.parent/'clock_observation.py').read_bytes()).hexdigest()),indent=2)+'\n')
    print('Actual clock and vessel observations pass; eight damaged copies rejected; owning evidence unchanged')


if __name__=='__main__':main()
