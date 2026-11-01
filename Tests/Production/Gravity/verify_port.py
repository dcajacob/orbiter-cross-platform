#!/usr/bin/env python3
"""Exercise the shared production Pines implementation against frozen Windows."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

from capture import HERE, ROOT, compare, require
from frozen_reference import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--configuration', required=True)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    output = args.output.resolve()
    reference = HERE/'Reference'
    require(output != reference and reference not in output.parents, 'cannot overwrite accepted evidence')
    metadata, golden = load(reference)
    output.mkdir(parents=True, exist_ok=True)
    for repeat in (1, 2):
        command = [str(executable), '--data-root', str(ROOT), '--output', str(output/f'trace-{repeat}.csv')]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        (output/f'run-{repeat}.log').write_bytes(result.stdout)
        require(result.returncode == 0, 'shared production gravity observer failed; see run log')
    first, second = output/'trace-1.csv', output/'trace-2.csv'
    require(first.read_bytes() == second.read_bytes(), 'shared production gravity repeats differ')
    report = compare(golden, first)
    report.update(configuration=args.configuration, host=platform.platform(),
        capture_sources=metadata['capture_sources'], source=subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        scope='Actual shared production Pines queries and independent J2 check; not world initialization')
    report['working_tree_dirty'] = bool(subprocess.check_output(
        ['git', '-C', str(ROOT), 'diff', '--name-only', '--', 'Src', 'Orbitersdk', 'CMakeLists.txt']))
    (output/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
