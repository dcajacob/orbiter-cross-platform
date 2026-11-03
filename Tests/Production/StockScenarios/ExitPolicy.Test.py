#!/usr/bin/env python3
"""Damage copied real corpus evidence; reject generic or forged early exits."""
import argparse
import copy
import csv
import io
import json
from pathlib import Path
import tempfile

from inventory import digest,require
import intentional_exit
from run import inspect,rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','reference','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Stock exit policy control output exists')
    report=json.loads((a.capture/'stock-scenarios.json').read_text())
    name='Tests/VesselApiTest.scn';case=report['cases'][name]
    require(case['status']=='passed','Controls require a complete real corpus stock-exit capture')
    source=a.capture/case['output'];profile=report['runtime_identity']['profile']
    before={p.name:digest(p) for p in source.iterdir() if p.is_file()}
    require(inspect(source,case,0,name,a.reference,profile)['status']=='passed','Positive stock exit was rejected')
    result=dict(status='failed',source_sha256=digest(Path(__file__)),capture_sha256=digest(a.capture/'stock-scenarios.json'),controls=[])
    with tempfile.TemporaryDirectory(prefix='orbiter-stock-exit-policy-') as temporary:
        base=Path(temporary)
        controls=['ordinary_partial_exit','missing_policy_identity','wrong_scenario_hash','missing_reference',
            'wrong_profile','wrong_raw_math','missing_assertion','forged_completion','missing_core_background_ship',
            'missing_sdk_background_ship','missing_docking_port','missing_final_tick','wrong_exit_code',
            'incomplete_teardown','overwritten_save','changed_staged_script']
        for control in controls:
            out=base/control;out.mkdir()
            for file in source.iterdir():
                if file.is_file():(out/file.name).symlink_to(file)
            def replace(file,data):
                target=out/file;target.unlink();target.write_bytes(data)
            def csv_remove(file,predicate):
                values=rows(out/file);columns=list(values[0]);removed=False;retained=[]
                for row in values:
                    if not removed and predicate(row):removed=True
                    else:retained.append(row)
                require(removed,'Control did not remove a real observation')
                stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns)
                writer.writeheader();writer.writerows(retained);replace(file,stream.getvalue().encode())
            selected=copy.deepcopy(case);scenario=name;reference=a.reference;math_profile=profile;code=0
            if control=='ordinary_partial_exit':scenario='2024 Edition/Spotlights.scn'
            elif control=='missing_policy_identity':scenario=None
            elif control=='wrong_scenario_hash':selected['sha256_lf']='0'*64
            elif control=='missing_reference':reference=None
            elif control=='wrong_profile':math_profile='Release-sse2' if profile!='Release-sse2' else 'Debug-automatic'
            elif control=='wrong_raw_math':
                data=json.loads((out/'numerics.json').read_text());data['math']='forged-other-math'
                replace('numerics.json',(json.dumps(data)+'\n').encode())
            elif control in ('missing_assertion','forged_completion'):
                text=(out/'console.log').read_text()
                if control=='missing_assertion':
                    lines=text.splitlines(keepends=True);index=next(i for i,line in enumerate(lines) if line.rstrip().endswith(' - passed'))
                    del lines[index];text=''.join(lines)
                else:text='=== All tests passed ===\n'
                for file in ('console.log','console.txt'):replace(file,text.encode())
            elif control=='missing_core_background_ship':csv_remove('flight-state.csv',lambda r:r['tick']=='3' and r['object']!=r['focus'])
            elif control=='missing_sdk_background_ship':csv_remove('stock-vessel-state.csv',lambda r:r['tick']=='3' and r['focus']=='0')
            elif control=='missing_docking_port':csv_remove('stock-vessel-docks.csv',lambda r:r['tick']=='3')
            elif control=='missing_final_tick':
                values=rows(out/'stock-vessel-state.csv');last=max(int(r['tick']) for r in values)
                csv_remove('stock-vessel-state.csv',lambda r:int(r['tick'])==last)
            elif control=='wrong_exit_code':code=7
            elif control=='incomplete_teardown':
                data=json.loads((out/'graphics-lifecycle.json').read_text());data['context_deleted']=False
                replace('graphics-lifecycle.json',(json.dumps(data)+'\n').encode())
            elif control=='overwritten_save':replace('saved.scn',b'Replaced save after explicit exit\n')
            elif control=='changed_staged_script':
                assets=base/'assets';script=intentional_exit.settings()['script'];target=assets/script
                target.parent.mkdir(parents=True);target.write_bytes((intentional_exit.ROOT/script).read_bytes()+b'\n-- changed\n')
                try:intentional_exit.policy(name,selected,assets)
                except ValueError as error:
                    result['controls'].append(dict(control=control,problems=[str(error)]));continue
                raise ValueError('Changed staged script was accepted')
            observed=inspect(out,selected,code,scenario,reference,math_profile)
            require(observed['status']=='failed' and observed['problems'],'Damaged stock exit was accepted: '+control)
            result['controls'].append(dict(control=control,problems=observed['problems']))
    require(before=={p.name:digest(p) for p in source.iterdir() if p.is_file()},'Owning stock capture changed')
    result.update(status='passed',rejected_controls=len(result['controls']),original_capture_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Sixteen strict stock exit policy controls rejected; original capture unchanged')


if __name__=='__main__':main()
