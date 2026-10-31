#!/usr/bin/env python3
"""Read immutable production evidence and compare current application outputs.

This module never writes to the accepted reference or changes its budgets.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from mesa_runtime import digest, require


def load_reference(directory):
    directory = directory.resolve()
    metadata = json.loads((directory/'provenance.json').read_text())
    require(metadata['schema'] == 1 and metadata['status'] == 'accepted' and
            metadata['automatic_refresh'] is False, 'accepted production reference is missing')
    root = Path(__file__).resolve().parent
    require(digest(root/'stock-data.lock.json') == metadata['data_lock_sha256'], 'frozen data profile changed')
    for name, expected in metadata['fixture_source_sha256'].items():
        actual = hashlib.sha256((root/'Fixtures'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        require(actual == expected, 'frozen production fixture changed: '+name)
    for config, artifact in metadata['artifacts'].items():
        path = (directory/artifact['path']).resolve()
        require(directory.parent in path.parents, 'reference archive must remain inside production tests')
        require(digest(path) == artifact['sha256'], 'frozen evidence archive changed: '+config)
        with zipfile.ZipFile(path) as archive:
            for member, expected in artifact['members_sha256'].items():
                require(hashlib.sha256(archive.read(member)).hexdigest() == expected,
                        'frozen evidence member changed: '+member)
    return metadata


def compare_capture(directory, candidate):
    from capture_reference import physics_trace
    from compare_references import states
    from trace_tools import compare, LIMITS
    metadata = load_reference(directory)
    for key, budget in LIMITS.items():
        require(metadata['budgets'][key] == budget, 'frozen numerical budget changed: '+key)
    require(metadata['budgets']['mass_relative'] == 1e-8 and metadata['budgets']['mass_absolute_kg'] == 1e-8,
            'frozen propulsion budgets changed')
    artifact = metadata['artifacts']['Release']
    report = dict(capture_commit=metadata['capture_commit'], cases={})
    with tempfile.TemporaryDirectory(prefix='orbiter-frozen-') as temporary:
        base = Path(temporary)
        with zipfile.ZipFile(directory.resolve()/artifact['path']) as archive:
            for member in artifact['members_sha256']:
                name = PurePosixPath(member)
                require(not name.is_absolute() and '..' not in name.parts, 'invalid reference member path')
                path = base.joinpath(*name.parts)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(archive.read(member))
        for name in metadata['cases']:
            reference, current = base/'production-reference'/name, candidate/name
            for filename in ('production-events.csv','production-objects.txt'):
                require((reference/filename).read_bytes() == (current/filename).read_bytes(),
                        'frozen lifecycle/object identity differs: '+name+'/'+filename)
            report['cases'][name] = dict(vessel=compare(physics_trace(reference/'trace.csv'),
                physics_trace(current/'trace.csv')),
                world=states(reference/'production-state.csv',current/'production-state.csv'))
    report['status'] = 'passed'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=Path(__file__).with_name('Reference'))
    parser.add_argument('--candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare_capture(args.reference,args.candidate) if args.candidate else
                     dict(status='passed',capture_commit=load_reference(args.reference)['capture_commit']),indent=2))
