#!/usr/bin/env python3
"""Check the actual stock Sol bodies at every pinned stock scenario epoch.

This exercises CSPICE directly, not Orbiter's production object graph or its
interpolation. It cannot substitute for Windows application/graphics references.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from inventory import ROOT, SOURCE, git
from mesa_runtime import digest, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--default-mjd', type=float, required=True,
                        help='explicit coverage epoch for scenarios that default to wall clock; does not alter them')
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name('production-source.lock.json').read_text())
    epochs = {51982.5, args.default_mjd}
    wall_clock = []
    for scenario in lock['scenarios']:
        text = git('show', SOURCE+':'+scenario['path']).decode('cp1252')
        date = re.search(r'^\s*Date\s+MJD\s+([-+\d.eE]+)', text, re.M | re.I)
        if date:
            epochs.add(float(date[1]))
        else:
            wall_clock.append(scenario['path'])
    config = 'Src/Celbody/SPICE/Config/'
    sol = git('show', SOURCE+':'+config+'Sol.cfg').decode()
    names = re.findall(r'^\s*(?:Star\d+|Planet\d+|\w+:Moon\d+)\s*=\s*(\S+)', sol, re.M)
    queries = []
    for name in names:
        text = git('show', SOURCE+':'+config+name+'.cfg').decode()
        fields = dict(re.findall(r'^\s*(Body|Origin|Barycenter|ParentBarycenter)\s*=\s*([^;\r\n]+)', text, re.M))
        require('Body' in fields and 'Origin' in fields, 'missing SPICE configuration: '+name)
        for epoch in sorted(epochs):
            for body in dict.fromkeys(fields[key].strip() for key in ('Body','Barycenter','ParentBarycenter') if key in fields):
                queries.append(f"{body}\t{fields['Origin'].strip()}\t{epoch:.17g}\n")
    data_lock = json.loads(Path(__file__).with_name('stock-data.lock.json').read_text())
    for name in ('Kernels/naif0012.tls','Kernels/pck00011.tpc','Kernels/orbiter.bsp'):
        require(digest(args.data/name) == data_lock['data_files'][name]['sha256'], 'wrong kernel: '+name)
    query = ''.join(queries)
    result = subprocess.run([str(args.executable.resolve()), str(args.data.resolve())], input=query,
                            text=True, capture_output=True, timeout=120)
    require(result.returncode == 0, result.stderr)
    require(len(result.stdout.splitlines()) == len(queries)+1, 'incomplete SPICE coverage result')
    # An unsupported epoch must fail explicitly with coverage diagnostics.
    invalid = subprocess.run([str(args.executable.resolve()), str(args.data.resolve())],
                             input='EARTH\tSUN\t-100000\n', text=True, capture_output=True, timeout=30)
    require(invalid.returncode != 0 and 'kernel coverage' in invalid.stderr, 'out-of-coverage epoch accepted')
    report = dict(status='passed', scope='direct CSPICE data coverage; not a production Orbiter execution',
                  source_commit=SOURCE, bodies=len(names), stock_scenarios=len(lock['scenarios']),
                  unique_epochs=len(epochs), queries=len(queries), executable_sha256=digest(args.executable),
                  default_coverage_mjd=args.default_mjd, wall_clock_scenarios=wall_clock,
                  query_sha256=hashlib.sha256(query.encode()).hexdigest(),
                  states_sha256=hashlib.sha256(result.stdout.replace('\r\n','\n').encode()).hexdigest(),
                  toolkit=result.stderr.strip(), invalid_epoch_rejected=True,
                  kernel_sha256={name:digest(args.data/name) for name in data_lock['data_files']
                                 if name in ('Kernels/naif0012.tls','Kernels/pck00011.tpc','Kernels/orbiter.bsp')})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
