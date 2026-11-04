#!/usr/bin/env python3
"""Validate actual begin/finalized SDK clocks for the matched-clock v2 fixture."""
import math
from clock_observation import FIELDS,inspect_clock,require,rows

PROTOCOL='remaining-stock-matched-clock-v2'


def inspect_matched_clock(out,config):
    require(config['protocol']==PROTOCOL and config['frames']==960 and config['fixed_step']==1/64 and
            config['system_elapsed_input']==.1 and config['system_startup_steps']==[.01,.01,.01] and
            config['capture_tick']==800,'Matched-clock v2 parameters differ')
    basic=inspect_clock(out,config['frames'])
    require(basic['system_start']==0 and basic['simulation_start']==0,'Matched SDK clocks did not start at zero')
    end=rows(out/'stock-clock.csv',FIELDS);begin=rows(out/'stock-step-clock.csv',FIELDS)
    require([row['tick'] for row in begin]==[str(tick) for tick in range(1,config['frames']+1)],
            'Incomplete or unordered SDK begin-step clocks')
    def values(records):
        result=[{key:float(row[key]) for key in FIELDS[1:]} for row in records]
        require(all(math.isfinite(v) for row in result for v in row.values()),'Nonfinite matched SDK clock')
        return result
    final=values(end);starting=values(begin)
    # Mirror the conserved TimeData clock accumulator, including its 1e6-second
    # split. Checking a rounded total+step instead would reject valid large warp.
    simulation_offset=0.;simulation_increment=0.
    for tick,(before,after) in enumerate(zip(starting,final[1:]),1):
        previous=final[tick-1]
        elapsed=config['system_startup_steps'][tick-1] if tick<=3 else config['system_elapsed_input']
        require(before['system_seconds']==previous['system_seconds'] and
                before['simulation_seconds']==previous['simulation_seconds'],
                'SDK begin clock is not associated with the previous finalized tick')
        require(before['system_step']==after['system_step']==elapsed,
                'Actual SDK system elapsed input differs from matched startup/clamp policy')
        require(before['time_acceleration']>0 and
                before['simulation_step']==config['fixed_step']*before['time_acceleration'] and
                after['simulation_step']==before['simulation_step'],
                'Actual physical step differs from fixed input and pre-callback warp')
        simulation_increment+=before['simulation_step']
        if simulation_increment>1e6:
            simulation_offset+=1e6;simulation_increment-=1e6
        require(after['system_seconds']==before['system_seconds']+before['system_step'] and
                after['simulation_seconds']==simulation_offset+simulation_increment,
                'Finalized SDK clock does not contain the observed physical/system step')
    def changes(records,key,first):
        return [dict(tick=index+first,value=row[key]) for index,row in enumerate(records)
                if index==0 or row[key]!=records[index-1][key]]
    summary=dict(protocol=PROTOCOL,frames=config['frames'],fixed_step=config['fixed_step'],
        system_elapsed_input=config['system_elapsed_input'],startup_system_steps=config['system_startup_steps'],
        begin_samples=len(starting),finalized_samples=basic['samples'],
        system_start=final[0]['system_seconds'],system_end=final[-1]['system_seconds'],
        simulation_start=final[0]['simulation_seconds'],simulation_end=final[-1]['simulation_seconds'],
        capture_tick=config['capture_tick'],capture_simulation_seconds=final[config['capture_tick']]['simulation_seconds'],
        begin_warp_changes=changes(starting,'time_acceleration',1),finalized_warp_changes=changes(final,'time_acceleration',0),
        physical_step_changes=changes(starting,'simulation_step',1),
        scope='Actual public SDK clocks before module callbacks and after finalization. Original fixed-step times pre-callback warp and exact clock advancement verified; scripts retain control of warp.')
    return summary,{str(tick):row['simulation_seconds'] for tick,row in enumerate(final)}
