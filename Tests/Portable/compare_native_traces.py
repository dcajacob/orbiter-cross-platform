#!/usr/bin/env python3
"""Compare the four hosted native runners with each other and the frozen engine."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from trace_tools import load_trace, compare, validate_orbit, require


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
    args.report.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError) as error:
        raise SystemExit(str(error)) from error
