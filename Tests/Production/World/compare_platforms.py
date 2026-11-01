#!/usr/bin/env python3
"""Require four clean builds and compare all actual celestial world states."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
from verify import compare,quaternion,distance,quaternion_angle,LIMITS,require

def rotations(row):
    return quaternion({f'm{i}{j}':row[f'r{i}{j}'] for i in range(1,4) for j in range(1,4)})

def difference(first,second):
    a=list(csv.DictReader(io.StringIO(first.decode('ascii'))));b=list(csv.DictReader(io.StringIO(second.decode('ascii'))))
    require(len(a)==len(b)==601*41,'Missing cross-platform world rows')
    maximum=dict(position_m=0.,velocity_m_s=0.,orientation_rad=0.,mjd_days=0.)
    for x,y in zip(a,b):
        require(all(x[key]==y[key] for key in ('step','seconds','index','body','mass')),'Cross-platform world identity/time/mass differs')
        errors=dict(position_m=distance([float(x[k]) for k in ('px','py','pz')],[float(y[k]) for k in ('px','py','pz')]),
            velocity_m_s=distance([float(x[k]) for k in ('vx','vy','vz')],[float(y[k]) for k in ('vx','vy','vz')]),
            orientation_rad=quaternion_angle(rotations(x),rotations(y)),mjd_days=abs(float(x['mjd'])-float(y['mjd'])))
        for key,error in errors.items():
            require(math.isfinite(error) and error<=LIMITS[key],f"{x['body']} step {x['step']}: cross-platform {key} exceeds original budget")
            maximum[key]=max(maximum[key],error)
    return maximum

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();builds={};sources=set();inputs=[]
    for path in args.evidence.rglob('world-comparison.json'):
        report=json.loads(path.read_text());key=(report['host'].split('-')[0],report['configuration'])
        require(key not in builds and report['status']=='passed' and not report['working_tree_dirty'],'Invalid or duplicate production world build')
        first=(path.parent/'trace-1.csv').read_bytes()
        require(first==(path.parent/'trace-2.csv').read_bytes(),'Hosted world repeats differ')
        compare(first);builds[key]=first;sources.add(report['source']);inputs.append(report['data_inputs'])
    require(set(builds)=={(host,configuration) for host in ('Linux','Windows') for configuration in ('Debug','Release')} and len(sources)==1,'Four same-source native world builds are required')
    require(all(value==inputs[0] for value in inputs),'Cross-platform world data differs')
    reference=next(iter(builds.values()))
    results=[dict(host=key[0],configuration=key[1],maximum=difference(reference,trace)) for key,trace in sorted(builds.items())]
    args.report.write_text(json.dumps(dict(status='passed',source=next(iter(sources)),results=results,
        scope='Actual celestial production world and finalized states; not native vessels/camera/renderer'),indent=2)+'\n')
    print('All four production celestial worlds and repeats agree within unchanged budgets')

if __name__=='__main__':main()
