#!/usr/bin/env python3
"""Reject missing recordings and false playback claims in copied real captures."""
import argparse
import csv
import io
import json
from pathlib import Path
import tempfile

from original import settings,rows,digest,require
from recording_inputs import inspect_inputs,recordings


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Playback control output exists')
    config=settings();case=next(c for c in config['cases'] if c['id']=='legacy_stations_4')
    positive=inspect_inputs(a.capture,case,config,rows)
    before={str(p.relative_to(a.capture)):digest(p) for p in a.capture.rglob('*') if p.is_file()}
    controls=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-legacy-playback-') as temporary:
        for control in ('missing_position_stream','changed_recording','false_playback_flag','missing_nonfocus_flag','wrong_entry_point'):
            out=Path(temporary)/control;out.mkdir()
            for file in a.capture.rglob('*'):
                if file.is_file():
                    target=out/file.relative_to(a.capture);target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(file)
            def replace(name,data):
                target=out/name;target.unlink();target.write_bytes(data)
            if control=='missing_position_stream':(out/'Flights/Smack! Rescue/ISS.pos').unlink()
            elif control=='changed_recording':
                name='Flights/Smack! Rescue/ISS.pos';replace(name,(out/name).read_bytes()+b'\n; altered\n')
            elif control=='wrong_entry_point':
                value=json.loads((out/'invocation.json').read_text());value['scenario_entry_point']='Scenarios/Behavior.scn'
                replace('invocation.json',(json.dumps(value)+'\n').encode())
            else:
                values=rows(out/'stock-playback.csv')
                target=next(r for r in values if r['tick']=='30' and r['object']=='PB-01')
                if control=='false_playback_flag':target['playback']='0'
                else:values.remove(target)
                stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values);replace('stock-playback.csv',stream.getvalue().encode())
            try:inspect_inputs(out,case,config,rows)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=control,reason=str(error)))
            else:raise ValueError('Invalid playback input accepted: '+control)
    require(before=={str(p.relative_to(a.capture)):digest(p) for p in a.capture.rglob('*') if p.is_file()},'Original playback capture changed')
    result=dict(status='passed',controls=controls,source_sha256=digest(Path(__file__)),positive=positive,
                original_capture_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Five recording/input/playback controls rejected')


if __name__=='__main__':main()
