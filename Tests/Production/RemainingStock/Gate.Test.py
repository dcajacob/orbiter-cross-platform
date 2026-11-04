#!/usr/bin/env python3
"""Reject damaged copies of an actual complete launch-stack observation."""
import argparse
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('remaining_control_original',HERE/'original.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();original.require(not a.output.exists(),'Remaining-stock control output exists')
    config=original.settings();case=next(c for c in config['cases'] if c['id']=='remaining_stock_003')
    positive=original.inspect_artifacts(a.capture,case,config)
    before={str(p.relative_to(a.capture)):original.digest(p) for p in a.capture.rglob('*') if p.is_file()}
    controls=[]
    names=('missing_background_vessel','missing_thruster','missing_tank','unknown_tank_owner','missing_attachment',
        'missing_mesh_slot','false_initial_playback','missing_position_recording','wrong_windows_entry_point',
        'changed_class_input','shifted_clock','missing_population_tick')
    with tempfile.TemporaryDirectory(prefix='orbiter-remaining-stock-control-') as temporary:
        for name in names:
            out=Path(temporary)/name;out.mkdir()
            for path in a.capture.rglob('*'):
                if path.is_file():
                    target=out/path.relative_to(a.capture);target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(path)
            def replace(file,data):
                target=out/file;target.unlink();target.write_bytes(data)
            def rewrite(file,values):
                stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values);replace(file,stream.getvalue().encode())
            if name=='missing_position_recording':
                first=case['playback_vessels'][0]
                (out/('Flights/'+case['recording_directory']+'/'+first+'.pos')).unlink()
            elif name in ('wrong_windows_entry_point','changed_class_input'):
                invocation=json.loads((out/'invocation.json').read_text())
                if name=='wrong_windows_entry_point':
                    invocation['argv']=[v.replace('\\','/') if v.startswith('--scenariox=') else v for v in invocation['argv']]
                else:invocation['input_sha256'][config['classes']['Atlantis']['target']]='0'*64
                replace('invocation.json',(json.dumps(invocation,indent=2)+'\n').encode())
            else:
                file={'missing_background_vessel':'stock-vessel-state.csv','missing_thruster':'stock-vessel-thrusters.csv',
                    'missing_tank':'stock-vessel-propellants.csv','unknown_tank_owner':'stock-vessel-thrusters.csv',
                    'missing_attachment':'stock-vessel-attachments.csv','missing_mesh_slot':'stock-vessel-meshes.csv',
                    'false_initial_playback':'stock-playback.csv','shifted_clock':'stock-vessel-state.csv',
                    'missing_population_tick':'stock-population.csv'}[name]
                values=original.rows(out/file);original.require(values,'Real control trace has no observations: '+file)
                if name=='missing_background_vessel':
                    target=next(v for v in values if v['tick']=='30' and v['focus']=='0');values.remove(target)
                elif name=='unknown_tank_owner':
                    target=next(v for v in values if v['resource_object']);target['resource_object']='OmittedExternalTank'
                elif name=='false_initial_playback':
                    target=next(v for v in values if v['tick']=='0' and v['object'] in case['playback_vessels']);target['playback']='0'
                elif name=='shifted_clock':values[0]['seconds']='0.25'
                else:del values[0]
                rewrite(file,values)
            try:original.inspect_artifacts(out,case,config)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged remaining-stock capture accepted: '+name)
    original.require(before=={str(p.relative_to(a.capture)):original.digest(p) for p in a.capture.rglob('*') if p.is_file()},
                     'Original owning capture changed during controls')
    a.output.write_text(json.dumps(dict(status='passed',controls=controls,positive=positive,
        original_capture_unchanged=True,source_sha256=original.digest(Path(__file__))),indent=2)+'\n')
    print('Twelve damaged complete launch-stack captures rejected; owning original unchanged')


if __name__=='__main__':main()
