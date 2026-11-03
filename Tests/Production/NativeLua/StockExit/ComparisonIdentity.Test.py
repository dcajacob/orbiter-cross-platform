#!/usr/bin/env python3
"""Reject copied reports with forged observer or CRT identities; retain real captures unchanged."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from contract import HERE, digest, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'original-audit', 'native', 'build-record', 'runtime-root', 'output'):
        parser.add_argument('--'+name, required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--profile', required=True)
    parser.add_argument('--runtime-source-commit', required=True)
    args = parser.parse_args(); require(not args.output.exists(), 'Comparison identity output exists')
    before = {str(p.relative_to(args.native)): digest(p) for p in args.native.rglob('*') if p.is_file()}
    rejected = []
    for control in ('forged_observer_source', 'forged_CRT_record', 'forged_CRT_raw'):
        with tempfile.TemporaryDirectory(prefix='orbiter-stock-exit-identity-') as temporary:
            root = Path(temporary); view = root/'native'; view.mkdir()
            for p in args.native.iterdir():
                if p.name == 'capture.json': continue
                if p.is_file(): (view/p.name).symlink_to(p)
                elif p.is_dir() and p.name.startswith('run-'):
                    (view/p.name).mkdir()
                    for q in p.iterdir():
                        if q.is_file(): (view/p.name/q.name).symlink_to(q)
            report = copy.deepcopy(json.loads((args.native/'capture.json').read_text()))
            first = report['runs'][0]
            other = 'amd-6121d02-sse2' if first['actual_math'].endswith('fma3') else 'amd-6121d02-fma3'
            if control == 'forged_observer_source':
                key = next(name for name in report['source_sha256_lf'] if name.endswith('NativeProbe.cpp'))
                report['source_sha256_lf'][key] = '0'*64
            elif control == 'forged_CRT_record': first['actual_math'] = other
            else:
                path = view/'run-1/numerics.json'; data = json.loads(path.read_text()); data['math'] = other
                path.unlink(); path.write_text(json.dumps(data)+'\n')
                first['files_sha256']['numerics.json'] = digest(path)
            (view/'capture.json').write_text(json.dumps(report, indent=2)+'\n')
            command = [sys.executable, '-B', str(HERE/'compare.py'), '--profile', args.profile,
                       '--runtime-source-commit', args.runtime_source_commit]
            for name in ('original', 'original_audit', 'build_record', 'runtime_root'):
                command += ['--'+name.replace('_', '-'), str(getattr(args, name))]
            command += ['--native', str(view), '--output', str(root/'comparison.json')]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            expected = 'Native observer producer source differs' if control == 'forged_observer_source' else 'Recorded native CRT differs'
            require(result.returncode != 0 and expected in result.stdout, 'Forged identity was accepted or failed for another reason: '+control)
            rejected.append(control)
    require(before == {str(p.relative_to(args.native)): digest(p) for p in args.native.rglob('*') if p.is_file()},
            'Actual native capture changed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(status='passed', rejected=rejected, original_capture_unchanged=True), indent=2)+'\n')
    print('Forged observer source and both inconsistent CRT identities rejected; actual capture unchanged')


if __name__ == '__main__': main()
