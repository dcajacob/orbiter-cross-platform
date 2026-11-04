#!/usr/bin/env python3
"""Exercise sampled SDK resource-history validation; these are reader controls, not captured evidence."""
import copy
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('remaining_resource_reader',HERE/'original.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)


def main():
    def resource(tick,identity,owner='Tank'):
        return dict(tick=str(tick),object=owner,index='0',resource_id=str(identity),mass='1',max_mass='2',efficiency='1')
    def thruster(tick,kind,identity=1,owner='Tank',seen=None,level='0'):
        return dict(tick=str(tick),object='Orbiter',index='0',resource_state=kind,resource_id=str(identity),
            resource_object=owner,resource_index='0' if owner else '-1',
            resource_seen_tick=str(tick if seen is None else seen),level=level)
    propellants={(r['tick'],r['object'],r['index']):r for r in (resource(0,1),resource(1,1),resource(3,2))}
    values=[thruster(0,'live'),thruster(1,'live'),thruster(2,'retired',seen=1),
            thruster(3,'live',identity=2),thruster(4,'none',identity=0,owner='',seen=-1)]
    def indexed(values):return {(r['tick'],r['object'],r['index']):r for r in values}
    positive=reader.inspect_resources(propellants,indexed(values))
    assert positive==dict(external_tank_bindings=3,retired_resource_bindings=1,retired_resource_nonzero_levels=0)
    # Nonzero original levels are evidence to report, not a lifetime waiver.
    nonzero=copy.deepcopy(values);nonzero[2]['level']='0.5'
    assert reader.inspect_resources(propellants,indexed(nonzero))['retired_resource_nonzero_levels']==1
    controls={
        'unknown_retired_id':(2,'resource_id','99'),
        'unknown_retired_owner':(2,'resource_object','OmittedTank'),
        'unknown_retired_slot':(2,'resource_index','1'),
        'live_marked_retired':(1,'resource_state','retired'),
        'retired_marked_live':(2,'resource_state','live'),
        'future_last_seen':(2,'resource_seen_tick','2'),
        'stale_last_seen':(2,'resource_seen_tick','0'),
        'absent_with_identity':(4,'resource_id','1'),
        'unknown_resource_state':(2,'resource_state','unknown'),
    }
    rejected=[]
    for name,(index,key,value) in controls.items():
        damaged=copy.deepcopy(values);damaged[index][key]=value
        try:reader.inspect_resources(propellants,indexed(damaged))
        except ValueError:rejected.append(name)
        else:raise AssertionError('Damaged resource history accepted: '+name)
    for name,change in (
        ('resource_id_owner_changes',resource(3,1,'DifferentTank')),
        ('resource_id_resurrected',resource(3,1)),
    ):
        damaged=copy.deepcopy(propellants);damaged[(change['tick'],change['object'],change['index'])]=change
        try:reader.inspect_resources(damaged,indexed(values))
        except ValueError:rejected.append(name)
        else:raise AssertionError('Damaged public resource samples accepted: '+name)
    assert len(rejected)==11
    print('Sampled resource-history reader: two positives and eleven damaged histories checked; no runtime evidence created')


if __name__=='__main__':main()
