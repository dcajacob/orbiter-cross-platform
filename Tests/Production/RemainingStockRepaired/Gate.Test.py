#!/usr/bin/env python3
"""Reject damaged copies of a real complete repaired-reference observation."""
import argparse
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile

import capture


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();capture.require(not a.output.exists(),'Fresh repaired gate output required')
    config=capture.settings();case=next(c for c in config['cases'] if c['id']=='remaining_stock_003')
    positive=capture.inspect_artifacts(a.capture,case,config)
    def hashes(root):return {p.relative_to(root).as_posix():capture.sha(p) for p in root.rglob('*') if p.is_file()}
    before=hashes(a.capture);controls=[]
    names=('missing_background_vessel','missing_thruster','missing_tank','unknown_tank_owner','missing_attachment',
        'missing_mesh_slot','false_initial_playback','missing_position_recording','wrong_windows_entry_point',
        'changed_class_input','shifted_clock','missing_population_tick','missing_mesh_delivery_repair',
        'changed_mesh_delivery_provenance','forced_single_step_propagators','wrong_full_frame_tick',
        'incomplete_presentations','wrong_reference_variant')
    with tempfile.TemporaryDirectory(prefix='orbiter-repaired-stock-control-') as temporary:
        for name in names:
            out=Path(temporary)/name;out.mkdir()
            # Copy only the complete reader-input closure. Never link a mutable
            # control to an owning capture or duplicate the complete planet data.
            for relative in positive['files_sha256']:
                target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.capture/relative,target)
            def replace(file,data):(out/file).write_bytes(data)
            def rewrite(file,values):
                stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values);replace(file,stream.getvalue().encode())
            if name=='missing_position_recording':
                (out/('Flights/'+case['recording_directory']+'/'+case['playback_vessels'][0]+'.pos')).unlink()
            elif name=='missing_mesh_delivery_repair':(out/config['delivery_repairs'][0]['target']).unlink()
            elif name=='forced_single_step_propagators':
                path=out/'Orbiter.cfg';path.write_text(path.read_text()+'\nPropStages = 1\nPropStage0 = 1 1 1\n')
            elif name in ('wrong_full_frame_tick','incomplete_presentations','wrong_reference_variant'):
                file={'wrong_full_frame_tick':'scene-summary.json','incomplete_presentations':'graphics-lifecycle.json',
                      'wrong_reference_variant':'reference-variant.json'}[name]
                value=json.loads((out/file).read_text())
                if name=='wrong_full_frame_tick':value['frames']=50
                elif name=='incomplete_presentations':value['successful_presents']-=1
                else:value['fixed_step']=.25
                replace(file,(json.dumps(value,indent=2)+'\n').encode())
            elif name in ('wrong_windows_entry_point','changed_class_input','changed_mesh_delivery_provenance'):
                value=json.loads((out/'invocation.json').read_text())
                if name=='wrong_windows_entry_point':
                    value['argv']=[v.replace('\\','/') if v.startswith('--scenariox=') else v for v in value['argv']]
                elif name=='changed_class_input':value['input_sha256'][config['classes']['Atlantis']['target']]='0'*64
                else:value['delivery_repairs'][config['delivery_repairs'][0]['target']]['install_rule_sha256_lf']='0'*64
                replace('invocation.json',(json.dumps(value,indent=2)+'\n').encode())
            else:
                file={'missing_background_vessel':'stock-vessel-state.csv','missing_thruster':'stock-vessel-thrusters.csv',
                    'missing_tank':'stock-vessel-propellants.csv','unknown_tank_owner':'stock-vessel-thrusters.csv',
                    'missing_attachment':'stock-vessel-attachments.csv','missing_mesh_slot':'stock-vessel-meshes.csv',
                    'false_initial_playback':'stock-playback.csv','shifted_clock':'stock-vessel-state.csv',
                    'missing_population_tick':'stock-population.csv'}[name]
                values=capture.shared.rows(out/file);capture.require(values,'Real control trace has no observations: '+file)
                if name=='missing_background_vessel':
                    values.remove(next(v for v in values if v['tick']=='480' and v['focus']=='0'))
                elif name=='unknown_tank_owner':
                    next(v for v in values if v['resource_object'])['resource_object']='OmittedExternalTank'
                elif name=='false_initial_playback':
                    next(v for v in values if v['tick']=='0' and v['object'] in case['playback_vessels'])['playback']='0'
                elif name=='shifted_clock':values[0]['seconds']='0.25'
                else:del values[0]
                rewrite(file,values)
            try:capture.inspect_artifacts(out,case,config)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged repaired reference accepted: '+name)
    capture.require(before==hashes(a.capture),'Owning capture changed during controls')
    a.output.write_text(json.dumps(dict(status='passed',protocol=config['protocol'],controls=controls,positive=positive,
        owning_capture_unchanged=True,source_sha256=capture.sha(Path(__file__))),indent=2)+'\n')
    print('Eighteen damaged complete-scene/input/clock/graphics/variant captures rejected; owning evidence unchanged')


if __name__=='__main__':main()
