#!/usr/bin/env python3
"""Reject damaged copies of real v2 SDK clocks and finalized-frame metadata."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import capture
import protocols
from matched_clock import inspect_matched_clock
from clock_observation import rows

require=capture.require
NAMES=('stock-clock.csv','stock-step-clock.csv','stock-vessel-state.csv','scene-summary.json',protocols.MARKER)


def inspect(root,config):
    clock,_=inspect_matched_clock(root,config)
    protocols.inspect_frame(json.loads((root/'scene-summary.json').read_text()),config,clock)
    require((root/protocols.MARKER).read_bytes()==protocols.marker_bytes(config),'Executed finalized-frame descriptor differs')
    return clock


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh matched-clock control output required')
    config=capture.settings(protocols.V2)
    def hashes(root):return {name:capture.sha(root/name) for name in NAMES}
    before=hashes(a.capture);positive=inspect(a.capture,config);controls=[]
    damages=('missing_begin_tick','reordered_begin_ticks','nonfinite_begin_clock','different_system_elapsed',
             'different_begin_boundary','different_physical_step','different_begin_warp','different_final_step',
             'different_final_system_time','different_capture_protocol','different_capture_tick',
             'different_finalized_tick','different_capture_time','different_descriptor')
    with tempfile.TemporaryDirectory(prefix='orbiter-matched-clock-controls-') as temporary:
        for damage in damages:
            root=Path(temporary)/damage;root.mkdir()
            for name in NAMES:shutil.copy2(a.capture/name,root/name)
            if damage.startswith('different_capture_') or damage=='different_finalized_tick':
                path=root/'scene-summary.json';value=json.loads(path.read_text())
                key={'different_capture_protocol':'capture_protocol','different_capture_tick':'frames',
                     'different_finalized_tick':'finalized_tick','different_capture_time':'simulation_seconds'}[damage]
                value[key]='remaining-stock-repaired-v1' if key=='capture_protocol' else value[key]+1
                path.write_text(json.dumps(value)+'\n')
            elif damage=='different_descriptor':
                (root/protocols.MARKER).write_text(protocols.V2+' 799\n')
            else:
                path=root/('stock-clock.csv' if damage.startswith('different_final_') else 'stock-step-clock.csv')
                value=rows(path);fields=list(value[0]);index=10
                if damage=='missing_begin_tick':del value[index]
                elif damage=='reordered_begin_ticks':value[index],value[index+1]=value[index+1],value[index]
                else:
                    key={'nonfinite_begin_clock':'simulation_seconds','different_system_elapsed':'system_step',
                         'different_begin_boundary':'system_seconds','different_physical_step':'simulation_step',
                         'different_begin_warp':'time_acceleration','different_final_step':'simulation_step',
                         'different_final_system_time':'system_seconds'}[damage]
                    value[index][key]='nan' if damage=='nonfinite_begin_clock' else str(float(value[index][key])+.025)
                with path.open('w',newline='') as target:
                    writer=csv.DictWriter(target,fieldnames=fields);writer.writeheader();writer.writerows(value)
            try:inspect(root,config)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=damage,reason=str(error)))
            else:raise ValueError('Damaged actual matched-clock capture accepted: '+damage)
    require(hashes(a.capture)==before,'Owning actual matched-clock capture changed')
    sources=(Path(__file__),Path(protocols.__file__),capture.HERE.parent/'RemainingStock/matched_clock.py',
             capture.HERE.parent/'RemainingStock/clock_observation.py')
    a.output.write_text(json.dumps(dict(status='passed',protocol=protocols.V2,positive=positive,controls=controls,
        owning_capture_files_sha256=before,owning_capture_unchanged=True,
        source_sha256={p.relative_to(capture.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
    print('Actual matched-clock/frame metadata pass; fourteen damaged copies rejected; owning evidence unchanged')


if __name__=='__main__':main()
