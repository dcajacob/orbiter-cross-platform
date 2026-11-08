#!/usr/bin/env python3
"""Reject missing, reordered, mistimed or incomplete EndPlayback/Save witnesses."""
import argparse
import copy
import csv
import json
from pathlib import Path
import tempfile

from capture_native import inspect_save_boundary,replay_bytes
from saved_inputs import protocol


def rejected(action):
    try:
        action()
    except ValueError:
        return True
    return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists()
    contract=protocol()
    expected=b'tick,phase,action,value\n959,after,endplayback,0\n959,after,save,0\n'
    assert replay_bytes(contract)==expected
    controls=[]
    for field,value in (('input_tick',958),('phase','before'),('action','pause'),('value',1),('finalized_tick',959)):
        changed=copy.deepcopy(contract);changed['native_before_save_command'][field]=value
        assert rejected(lambda:replay_bytes(changed)),field
        controls.append('changed_preparation_'+field)
    with tempfile.TemporaryDirectory(prefix='orbiter-save-boundary-') as folder:
        out=Path(folder)
        fields=('frame','tick','seconds','mjd','phase','object','detail')
        def row(event,detail=''):
            return dict(zip(fields,('959','960','15','57462.4915610001',event,'',detail)))
        active=[row('input.endplayback','active'),row('playback.ended'),row('input.save')]
        idle=[row('input.endplayback','idle'),row('input.save')]
        def inspect(rows):
            with (out/'lifetime-events.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
            return inspect_save_boundary(out,contract)
        assert inspect(active)['playback_was_active'] is True
        assert inspect(idle)['playback_was_active'] is False
        early=row('playback.ended');early.update(frame='50',tick='50')
        assert inspect([early,*idle])['playback_was_active'] is False
        damaged=[('missing_preparation',active[1:]),('save_before_completion',[active[0],active[2],active[1]]),
                 ('missing_actual_completion',[active[0],active[2]]),('duplicate_save',[*active,active[2]]),
                 ('idle_with_completion',[dict(active[0],detail='idle'),*active[1:]]),
                 ('wrong_input_tick',[dict(active[0],frame='958'),*active[1:]]),
                 ('wrong_finalized_tick',[active[0],dict(active[1],tick='959'),active[2]]),
                 ('advanced_save_clock',[*active[:2],dict(active[2],seconds='15.015625')]),
                 ('nonfinite_clock',[dict(r,mjd='nan') for r in active]),
                 ('unknown_playback_witness',[dict(active[0],detail='unknown'),*active[1:]])]
        for name,rows in damaged:
            assert rejected(lambda:inspect(rows)),name
            controls.append(name)
    result=dict(status='passed',native_save_boundary=contract['native_save_boundary'],
                replay_bytes=expected.decode(),positive_witnesses=['active','idle','earlier_natural_end'],
                rejected_controls=controls,scope='Controlled reader fixtures only; no simulator execution or runtime qualification.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Three boundary witness positives and fifteen damaged controls passed')


if __name__=='__main__':main()
