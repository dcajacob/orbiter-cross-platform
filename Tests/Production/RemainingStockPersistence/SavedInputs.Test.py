#!/usr/bin/env python3
"""Verify exact derived inputs and reject changed real Windows saves and parents."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'RemainingStockRepaired'))
import capture as original
import protocols
from saved_inputs import derived_case
from saved_state import parse_saved,require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent-capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh saved-input controls required')
    config=original.settings(protocols.V2);parent=json.loads((a.parent_capture/'capture.json').read_text())
    require(parent['protocol']==protocols.V2 and parent['cases'],'Actual matched-clock Windows observations required')
    controls=[];positives=[];guarded={};sha=original.sha
    cases={c['id']:c for c in config['cases']}
    with tempfile.TemporaryDirectory(prefix='orbiter-saved-input-controls-') as temporary:
        root=Path(temporary)
        for identity,observation in parent['cases'].items():
            require(identity in cases and len(observation['runs'])==2,'Actual original parent repetitions differ')
            case=cases[identity]
            for repeat in (1,2):
                path=a.parent_capture/(identity+'-'+str(repeat))/'Scenarios/(Current state).scn'
                checksum=sha(path);guarded[str(path)]=checksum
                derived,provenance=derived_case(case,config,path,checksum);saved=parse_saved(path)
                require(derived['declared_vessels']=={name:s['class_name'] for name,s in saved['ships'].items()} and
                        provenance['saved_input_sha256']==checksum and provenance['original_recording_basename_preserved'] and
                        derived['scenario_entry_point']!='Scenarios/'+case['scenario'],'Exact derived saved vessels/path/hash were discarded')
                positives.append(dict(parent=identity,repeat=repeat,saved_input_sha256=checksum,
                    vessels=len(saved['ships']),playback_vessels=len(derived['playback_vessels'])))
                for damage in ('changed_parent_entry','changed_parent_identity','changed_saved_class','changed_saved_field','changed_line_endings'):
                    damaged_case=copy.deepcopy(case);target=path
                    if damage=='changed_parent_entry':damaged_case['scenario_entry_point']='Scenarios/Wrong.scn'
                    elif damage=='changed_parent_identity':damaged_case['id']='unknown_saved_parent'
                    else:
                        body=path.read_bytes();text=body.decode('cp1252')
                        if damage=='changed_line_endings':
                            modified=body.replace(b'\r\n',b'\n') if b'\r\n' in body else body.replace(b'\n',b'\r\n')
                        else:
                            lines=text.splitlines();first=lines.index('BEGIN_SHIPS')+1
                            if damage=='changed_saved_class':lines[first]=lines[first].split(':',1)[0]+':MissingSavedClass'
                            else:
                                row=lines[first+1].split();row[-1]+='_changed';lines[first+1]='  '+' '.join(row)
                            modified=('\n'.join(lines)+'\n').encode('cp1252')
                        target=root/'damaged.scn';target.write_bytes(modified)
                    try:derived_case(damaged_case,config,target,checksum)
                    except (ValueError,OSError,KeyError) as error:
                        controls.append(dict(parent=identity,repeat=repeat,control=damage,reason=str(error)))
                    else:raise ValueError('Changed actual saved input or frozen parent accepted: '+damage)
    require(all(sha(Path(name))==value for name,value in guarded.items()),'Owning exact Windows saves changed')
    reader=HERE/'saved_inputs.py'
    a.output.write_text(json.dumps(dict(status='passed-exact-saved-input-controls',positive_inputs=positives,controls=controls,
        actual_saved_inputs_sha256=guarded,test_sha256=sha(Path(__file__)),reader_sha256=sha(reader),
        saved_state_reader_sha256=sha(HERE/'saved_state.py'),owning_inputs_unchanged=True,
        native_admission_qualified=False,phase6_complete=False,
        scope='Exact real Windows derived-input and frozen-parent controls only. No save/reload physical, visual or full-corpus qualification inferred.'),indent=2)+'\n')
    print(len(positives),'actual Windows saved inputs retained;',len(controls),'damaged exact-input/parent controls rejected')


if __name__=='__main__':main()
