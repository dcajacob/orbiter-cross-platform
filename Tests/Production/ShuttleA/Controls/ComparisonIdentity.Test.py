#!/usr/bin/env python3
"""Reject forged math/source identities in copied reports without touching captures."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

import capture as controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('native', 'original', 'reference-audit', 'runtime-root', 'output'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.native/'controls-report.json'
    before = controls.digest(source)
    native = json.loads(source.read_text())
    result = dict(status='failed', rejected={}, original_report_sha256=before)
    def run(directory, label):
        command = [sys.executable, '-B', str(controls.HERE/'compare.py'), '--native', str(directory),
                   '--original', str(args.original), '--reference-audit', str(args.reference_audit),
                   '--runtime-root', str(args.runtime_root), '--output', str(args.output/(label+'.json'))]
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        (args.output/(label+'.log')).write_text(completed.stdout)
        return completed
    try:
        baseline = run(args.native, 'baseline')
        controls.require(baseline.returncode == 0, 'Valid comparison baseline failed')
        for label, message in (('wrong_actual_math', 'Actual original/native CRT math profiles differ'),
                               ('forged_source', 'Native observer source differs from recorded producer')):
            view = args.output/label
            view.mkdir()
            for path in args.native.iterdir():
                if path.name != source.name:
                    (view/path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
            changed = copy.deepcopy(native)
            if label == 'wrong_actual_math':
                phase = changed['cases']['shuttle_a_panel']['runs'][0]['moving']
                pieces = phase['actual_math'].split('-')
                pieces[-1] = 'sse2' if pieces[-1] == 'fma3' else 'fma3'
                phase['actual_math'] = '-'.join(pieces)
            else:
                changed['source_sha256_lf']['Tests/Production/ShuttleA/Controls/capture.py'] = '0'*64
            (view/source.name).write_text(json.dumps(changed, indent=2)+'\n')
            completed = run(view, label)
            controls.require(completed.returncode != 0 and message in completed.stdout,
                             'Forged identity accepted or rejected for another reason: '+label)
            result['rejected'][label] = True
        controls.require(controls.digest(source) == before, 'Negative controls changed the original report')
        result.update(status='passed', original_report_unchanged=True)
    finally:
        (args.output/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Actual math and producer-source forgeries rejected; original capture unchanged')


if __name__ == '__main__':
    main()
