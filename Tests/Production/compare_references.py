#!/usr/bin/env python3
"""Compare production reference candidates within predeclared budgets."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from capture_reference import physics_trace
from trace_tools import compare, distance, quaternion_angle, require, LIMITS


def quaternion(row):
    m = [float(row['m'+str(i)+str(j)]) for i in range(1,4) for j in range(1,4)]
    # Largest component conversion stays well-conditioned near 180 degrees.
    terms = [1+m[0]-m[4]-m[8], 1-m[0]+m[4]-m[8], 1-m[0]-m[4]+m[8], 1+m[0]+m[4]+m[8]]
    index = max(range(4), key=terms.__getitem__)
    scale = 2*math.sqrt(max(terms[index], 0))
    require(scale > 0, 'invalid production rotation matrix')
    if index == 0: return (scale/4,(m[1]+m[3])/scale,(m[2]+m[6])/scale,(m[7]-m[5])/scale)
    if index == 1: return ((m[1]+m[3])/scale,scale/4,(m[5]+m[7])/scale,(m[2]-m[6])/scale)
    if index == 2: return ((m[2]+m[6])/scale,(m[5]+m[7])/scale,scale/4,(m[3]-m[1])/scale)
    return ((m[7]-m[5])/scale,(m[2]-m[6])/scale,(m[3]-m[1])/scale,scale/4)


def states(reference, candidate):
    with reference.open(newline='') as stream: a = list(csv.DictReader(stream))
    with candidate.open(newline='') as stream: b = list(csv.DictReader(stream))
    require(len(a) == len(b) == 601*5, 'production state count mismatch')
    maxima = dict.fromkeys([*LIMITS, 'mass_error_fraction_of_budget', 'fuel_error_fraction_of_budget'], 0.0)
    for ref, got in zip(a,b):
        for field in ('step','seconds','object','ground'):
            require(ref[field] == got[field], 'production discrete state differs: '+field)
        values = lambda row, names: [float(row[name]) for name in names]
        errors = dict(position_m=distance(values(ref,('x','y','z')),values(got,('x','y','z'))),
                      velocity_m_s=distance(values(ref,('vx','vy','vz')),values(got,('vx','vy','vz'))),
                      orientation_rad=quaternion_angle(quaternion(ref),quaternion(got)),
                      angular_velocity_rad_s=distance(values(ref,('wx','wy','wz')),values(got,('wx','wy','wz'))),
                      mjd_days=abs(float(ref['mjd'])-float(got['mjd'])))
        require(all(math.isfinite(x) for x in errors.values()), 'nonfinite production comparison')
        for key, error in errors.items():
            require(error <= LIMITS[key], f"{ref['object']} step {ref['step']}: {key} {error} exceeds {LIMITS[key]}")
            maxima[key] = max(maxima[key], error)
        for field in ('mass','fuel'):
            budget = max(1e-8, abs(float(ref[field]))*1e-8)
            fraction = abs(float(ref[field])-float(got[field]))/budget
            require(math.isfinite(fraction) and fraction <= 1, f'production {field} budget exceeded')
            key = field+'_error_fraction_of_budget'
            maxima[key] = max(maxima[key],fraction)
    return maxima


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = dict(status='pending', cases={})
    try:
        a = json.loads((args.reference/'production-reference.json').read_text())
        b = json.loads((args.candidate/'production-reference.json').read_text())
        for key in ('source_commit','production_source_commit','data_lock_sha256'):
            require(a[key] == b[key], 'production input provenance differs: '+key)
        a_inputs = args.reference.parent/'production-app/build-inputs.json'
        b_inputs = args.candidate.parent/'production-app/build-inputs.json'
        require(a_inputs.is_file() and b_inputs.is_file(), 'actual toolchain/dependency metadata missing')
        ai, bi = json.loads(a_inputs.read_text()), json.loads(b_inputs.read_text())
        require(ai['dependencies'] == bi['dependencies'], 'compiled dependency revisions differ')
        for key in ('VCToolsVersion','WindowsSDKVersion'):
            require(ai['environment'][key] and ai['environment'][key] == bi['environment'][key],
                    'compiler/SDK versions differ or are missing: '+key)
        require(a['status'].startswith('repeatable-candidate') and b['status'].startswith('repeatable-candidate'),
                'production candidates must pass repeat checks first')
        for name in ('orbit','controls'):
            reference, candidate = args.reference/name, args.candidate/name
            for filename in ('production-events.csv','production-objects.txt'):
                require((reference/filename).read_bytes() == (candidate/filename).read_bytes(),
                        'production discrete evidence differs: '+filename)
            report['cases'][name] = dict(
                vessel=compare(physics_trace(reference/'trace.csv'), physics_trace(candidate/'trace.csv')),
                world=states(reference/'production-state.csv', candidate/'production-state.csv'))
        report['status'] = 'passed; orbit/propulsion candidates eligible for explicit frozen-reference acceptance'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
