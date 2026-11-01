#!/usr/bin/env python3
"""Capture/compare Pines observations without replacing accepted references."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIELDS = 'model,degree,order,sample,loaded_terms,max_terms,x_km,y_km,z_km,ax_m_s2,ay_m_s2,az_m_s2'.split(',')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def protocol(original=False):
    lock = json.loads((HERE/'protocol.json').read_text())
    require(lock['automatic_refresh'] is False, 'automatic reference refresh is forbidden')
    for name, expected in lock['inputs_sha256'].items():
        require(sha((ROOT/name).read_bytes()) == expected, 'gravity input changed: '+name)
    if original:
        for name, expected in lock['production_source_sha256_lf'].items():
            require(sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) == expected,
                    'production gravity changed before Windows baseline capture: '+name)
    return lock


def trace(path):
    data = path.read_bytes()
    require(len(data) < 2_000_000, 'gravity observation is unexpectedly large')
    reader = csv.DictReader(io.StringIO(data.decode('ascii'), newline=''))
    require(reader.fieldnames == FIELDS, 'gravity observation columns differ')
    rows = list(reader)
    require(len(rows) == 864, 'expected 864 gravity queries')
    index = 0
    for model, maximum in (('Earth', 65340), ('Moon', 13860)):
        for degree in (2, 4, 12, 32):
            for order in (0, degree//2, degree):
                for _altitude in range(3):
                    for _direction in range(12):
                        row = rows[index]
                        require(set(row) == set(FIELDS), 'gravity observation row has extra fields')
                        require(row['model'] == model and [int(row[key]) for key in FIELDS[1:6]] ==
                                [degree, order, index, 560, maximum], 'gravity query identity differs')
                        require(all(math.isfinite(float(row[key])) for key in FIELDS[6:]),
                                'nonfinite gravity observation')
                        index += 1
    require(any(float(row['ax_m_s2']) != 0 for row in rows), 'empty gravity output')
    return rows


def compare(reference, candidate):
    lock = protocol()
    left, right = trace(reference), trace(candidate)
    absolute = lock['budgets']['acceleration_absolute_m_s2']
    relative = lock['budgets']['acceleration_relative']
    maximum_error = 0.
    for a, b in zip(left, right):
        require(all(a[key] == b[key] for key in FIELDS[:6]), 'gravity query identity differs')
        require(all(float(a[key]) == float(b[key]) for key in FIELDS[6:9]), 'gravity query position differs')
        av = [float(a[key]) for key in FIELDS[9:]]
        bv = [float(b[key]) for key in FIELDS[9:]]
        error = math.dist(av, bv)
        budget = absolute + relative*math.hypot(*av)
        require(error <= budget, f'gravity budget exceeded at query {a["sample"]}: {error} > {budget}')
        maximum_error = max(maximum_error, error)
    return dict(status='passed', samples=len(left), maximum_acceleration_error_m_s2=maximum_error,
                budgets=lock['budgets'], reference_sha256=sha(reference.read_bytes()),
                candidate_sha256=sha(candidate.read_bytes()))


def capture(args):
    lock = protocol(original=True)
    require(platform.system() == 'Windows', 'pre-extraction reference capture requires native Windows')
    executable = args.executable.resolve(strict=True)
    output = args.output.resolve()
    # Refuse to overwrite an earlier capture or anything under the golden folder.
    require(not output.exists() and HERE/'Reference' not in output.parents and output != HERE/'Reference',
            'capture requires a new output directory outside the accepted reference')
    output.mkdir(parents=True)
    for repeat in (1, 2):
        command = [str(executable), '--data-root', str(ROOT), '--output', str(output/f'trace-{repeat}.csv')]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        (output/f'run-{repeat}.log').write_bytes(result.stdout)
        require(result.returncode == 0, 'production gravity observer failed; see capture log')
    first, second = output/'trace-1.csv', output/'trace-2.csv'
    require(first.read_bytes() == second.read_bytes(), 'production gravity repeats differ')
    report = compare(first, second)
    report.update(configuration=args.configuration, source=subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(), host=platform.platform(),
        executable_sha256=sha(executable.read_bytes()), protocol_sha256=sha((HERE/'protocol.json').read_bytes()),
        inputs_sha256=lock['inputs_sha256'], production_source_sha256_lf=lock['production_source_sha256_lf'],
        scope='Unchanged production Pines queries; not a world/contact/scenario reference')
    (output/'capture.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('capture')
    run.add_argument('--executable', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--configuration', choices=('Debug', 'Release'), required=True)
    check = commands.add_parser('compare')
    check.add_argument('--reference', type=Path, required=True)
    check.add_argument('--candidate', type=Path, required=True)
    check.add_argument('--report', type=Path, required=True)
    commands.add_parser('verify-original')
    args = parser.parse_args()
    if args.command == 'capture':
        report = capture(args)
    elif args.command == 'compare':
        report = compare(args.reference, args.candidate)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    else:
        protocol(original=True)
        report = dict(status='passed', scope='original production Pines source and locked inputs')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
