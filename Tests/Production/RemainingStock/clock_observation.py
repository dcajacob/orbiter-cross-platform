#!/usr/bin/env python3
"""Read passive SDK clock samples without prescribing the runtime clock policy."""
import csv
import math

PROTOCOL='remaining-stock-sdk-clock-v1'
FIELDS=('tick','system_seconds','system_step','simulation_seconds','simulation_step','time_acceleration')


def require(value,message):
    if not value:raise ValueError(message)


def rows(path,fields=None):
    with path.open(newline='',encoding='ascii') as source:
        reader=csv.DictReader(source);result=list(reader)
    require(reader.fieldnames and (fields is None or tuple(reader.fieldnames)==fields) and
            all(None not in row and None not in row.values() for row in result),
            'Malformed SDK clock observation input: '+path.name)
    return result


def inspect_clock(out,frames):
    require(isinstance(frames,int) and frames>=0,'Invalid SDK clock frame count')
    observed=rows(out/'stock-clock.csv',FIELDS)
    ticks=[str(tick) for tick in range(frames+1)];tick_set=set(ticks)
    require([row['tick'] for row in observed]==ticks,
            'Incomplete or unordered SDK clock ticks')
    values=[{key:float(row[key]) for key in FIELDS[1:]} for row in observed]
    require(all(math.isfinite(value) for row in values for value in row.values()),
            'Nonfinite SDK clock observation')
    require(all(row['system_step']>0 and row['simulation_step']>=0 and row['time_acceleration']>0 for row in values),
            'Invalid SDK clock step or acceleration')
    require(all(after['system_seconds']>=before['system_seconds'] for before,after in zip(values,values[1:])),
            'SDK system clock regressed')
    state=rows(out/'stock-vessel-state.csv')
    require(state and {row['tick'] for row in state}==tick_set,
            'SDK clock and vessel observation ticks differ')
    for row in state:
        require(float(row['seconds'])==values[int(row['tick'])]['simulation_seconds'],
                'SDK clock is not associated with the same vessel snapshot')
    def changes(key):
        return [dict(tick=tick,value=row[key]) for tick,row in enumerate(values)
                if tick==0 or row[key]!=values[tick-1][key]]
    return dict(protocol=PROTOCOL,samples=len(values),system_start=values[0]['system_seconds'],
                system_end=values[-1]['system_seconds'],simulation_start=values[0]['simulation_seconds'],
                simulation_end=values[-1]['simulation_seconds'],system_step_changes=changes('system_step'),
                simulation_step_changes=changes('simulation_step'),time_acceleration_changes=changes('time_acceleration'),
                scope='Read-only public SDK samples at the initial and finalized vessel observation boundaries; no matched system-clock policy or cross-platform parity is asserted.')
