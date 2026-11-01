#!/usr/bin/env python3
"""Compare the four hosted native runners with each other and the frozen engine."""
import argparse
import json
from pathlib import Path
import sys
import csv
import hashlib

sys.dont_write_bytecode = True
from trace_tools import load_trace, compare, validate_orbit, require
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Production/Gravity'))
from frozen_reference import load as load_gravity_reference
from capture import compare as compare_gravity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    platforms = [f"portable-{os}-{config}-x64" for os in ("ubuntu-24.04","windows-2022")
                 for config in ("Debug","Release")]
    result = {}
    for name,dt,steps,spin,frozen in (("orbit",1,6000,0,"Orbit.csv"),
            ("orbit-half",.5,12000,0,"Orbit.HalfStep.csv"),("spin",1,6000,1e-4,"Spin.csv")):
        reference = load_trace(args.reference/frozen,dt=dt,steps=steps)
        baseline = None
        result[name] = {}
        for platform in platforms:
            root = args.artifacts/platform/"out/portable/traces"
            rows = load_trace(root/(name+".csv"),dt=dt,steps=steps)
            repeat = root/(name+"-repeat.csv")
            if name != "orbit-half":
                require((root/(name+".csv")).read_bytes() == repeat.read_bytes(),
                        "nonrepeatable hosted trace: " + platform)
            if baseline is None: baseline = rows
            result[name][platform] = dict(analytical=validate_orbit(rows,spin=spin),
                frozen_reference=compare(reference,rows),cross_platform=compare(baseline,rows))
    # The actual production RigidBody class, independently checked against
    # inertial/free-spin analytical solutions by each executable. These are
    # distinct fixtures; the historical two-body goldens above stay unchanged.
    result['production_rigid_body']={}
    for mode in range(10):
        name=f'production-rigid-{mode}'
        baseline=None;result['production_rigid_body'][name]={}
        for platform in platforms:
            root=args.artifacts/platform/'out/portable/traces'
            rows=load_trace(root/(name+'.csv'),dt=.25,steps=6000)
            require((root/(name+'.csv')).read_bytes()==(root/(name+'-repeat.csv')).read_bytes(),
                    'nonrepeatable production RigidBody trace: '+platform)
            if baseline is None:baseline=rows
            result['production_rigid_body'][name][platform]=compare(baseline,rows)
    metadata=None
    for platform in platforms:
        data=(args.artifacts/platform/'out/portable/traces/production-scenario-metadata.csv').read_bytes()
        if metadata is None:metadata=data
        require(data==metadata,'production scenario metadata differs: '+platform)
    rows=list(csv.DictReader(metadata.decode('utf-8').splitlines()))
    require(len(rows)==157 and len({r['scenario'] for r in rows})==157,'incomplete stock scenario metadata')
    result['production_scenario_metadata']={'scenarios':157,'identical_platforms':platforms,
        'sha256':hashlib.sha256(metadata).hexdigest(),'coverage':'environment/focus parsing only; no world initialization'}
    reference, golden = load_gravity_reference(Path(__file__).resolve().parents[1]/'Production/Gravity/Reference')
    result['production_pines']={'capture_sources':reference['capture_sources'],'platforms':{}}
    baseline = None
    for platform in platforms:
        root = args.artifacts/platform/'out/portable/traces/production-gravity'
        current = root/'trace-1.csv'
        require(current.read_bytes() == (root/'trace-2.csv').read_bytes(), 'nonrepeatable production Pines trace: '+platform)
        if baseline is None: baseline = current
        result['production_pines']['platforms'][platform] = {
            'frozen_windows':compare_gravity(golden,current), 'cross_platform':compare_gravity(baseline,current)}
    args.report.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError) as error:
        raise SystemExit(str(error)) from error
