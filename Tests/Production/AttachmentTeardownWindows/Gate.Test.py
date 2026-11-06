#!/usr/bin/env python3
"""Reject damaged copies of real normal-cleanup Windows lifetime evidence."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32' and not args.output.exists()
    args.output.mkdir()
    spec = importlib.util.spec_from_file_location('actual_windows_lifetime_reader', args.reader)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    source = args.capture.resolve()
    cfg = json.loads((source / 'invocation.json').read_text())
    before = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
    built = json.loads(args.build.read_text())
    bindings = json.loads((source / 'mesa-bindings.json').read_text())
    expected = {}
    for name, checksum in built['configurations'][cfg['configuration']]['runtime_files_sha256'].items():
        if name.lower().endswith(('.dll', '.exe')):
            expected.setdefault(Path(name).name.lower(), set()).add(checksum)
    for name, item in bindings['runtime']['files'].items():
        if name.lower().endswith(('.dll', '.exe')):
            expected.setdefault(Path(name).name.lower(), set()).add(item['sha256'])
    positive = reader.inspect(source, cfg['worlds'], cfg['math_profile'], expected)
    report = dict(status='running', actual_positive=positive, controls={}, simulator_processes_launched=0,
                  reader_sha256=sha(args.reader), source_capture_unchanged=False)

    def fixture(name):
        target = args.output / name
        target.mkdir()
        # Only immutable DLL/asset inputs are linked. Every mutable witness is
        # an independent copy, so mutation cannot alter the actual capture.
        for path in source.rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            outgoing = target / relative
            outgoing.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in ('.json', '.csv', '.txt', '.log', '.cfg'):
                shutil.copy2(path, outgoing)
            else:
                os.link(path, outgoing)
        invocation = json.loads((target / 'invocation.json').read_text())
        invocation['argv'][0] = str(target / 'Orbiter.exe')
        (target / 'invocation.json').write_text(json.dumps(invocation, indent=2) + '\n')
        for path in target.glob('attachment-loaded-modules-world-*.txt'):
            lines = []
            for line in path.read_text().splitlines():
                incoming = Path(line)
                lines.append(str(target / incoming.relative_to(source)) if source in incoming.parents else line)
            path.write_text('\n'.join(lines) + '\n')
        reader.inspect(target, cfg['worlds'], cfg['math_profile'], expected)
        return target

    def json_change(folder, name, change):
        path = folder / name
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data, indent=2) + '\n')

    def startup(folder, before, after):
        path = folder / 'staged-Orbiter.cfg'
        path.write_text(path.read_text().replace(before, after))
        json_change(folder, 'invocation.json', lambda value: value.update(startup_configuration_sha256=sha(path)))

    def row_change(folder, field, value):
        path = folder / 'attachment-vessels.csv'
        lines = path.read_text().splitlines()
        keys = lines[0].split(',')
        values = lines[1].split(',')
        values[keys.index(field)] = value
        lines[1] = ','.join(values)
        path.write_text('\n'.join(lines) + '\n')

    controls = {
        'fast-exit-argument': lambda p: json_change(p, 'invocation.json', lambda d: d['argv'].__setitem__(1, d['argv'][1].replace('--scenario=', '--scenariox='))),
        'initial-physics-checkbox': lambda p: startup(p, 'StartPaused = FALSE', 'StartPaused = TRUE'),
        'fast-cleanup-configuration': lambda p: startup(p, 'ShutdownMode = 0', 'ShutdownMode = 2'),
        'missing-world-completion': lambda p: (p / 'attachment-completed-worlds.txt').write_text('1\n'),
        'nonfinite-physical-state': lambda p: row_change(p, 'x', 'nan'),
        'advanced-physics-clock': lambda p: row_change(p, 'seconds', '0.015625'),
        'broken-reciprocal-link': lambda p: row_change(p, 'payload_parent', '0'),
        'missing-context-deletion': lambda p: json_change(p, 'attachment-world-1/graphics-lifecycle.json', lambda d: d.update(context_deleted=False)),
        'fast-process-shutdown-log': lambda p: (p / 'Orbiter.log').write_text((p / 'Orbiter.log').read_text() + '\n**** Fast process shutdown\n'),
        'wrong-actual-math': lambda p: (p / 'attachment-math.txt').write_text('unknown\n'),
    }
    for name, damage in controls.items():
        target = fixture(name)
        damage(target)
        try:
            reader.inspect(target, cfg['worlds'], cfg['math_profile'], expected)
        except (ValueError, AssertionError, FileNotFoundError) as error:
            report['controls'][name] = str(error)
        else:
            raise AssertionError('Damaged actual lifetime evidence accepted: ' + name)
    assert before == {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
    report.update(status='passed', source_capture_unchanged=True)
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], controls=len(report['controls']), simulator_processes_launched=0)))


if __name__ == '__main__':
    main()
