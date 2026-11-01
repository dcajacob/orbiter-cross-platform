#!/usr/bin/env python3
"""Read accepted Windows gravity evidence; never create or refresh a golden."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from capture import HERE, compare, protocol, require, trace


def digest(data):
    return hashlib.sha256(data).hexdigest()


def member_path(directory, name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'invalid frozen evidence path')
    result = (directory/relative).resolve()
    require(result.is_relative_to(directory.resolve()), 'evidence escapes the reference directory')
    return result


def load(directory):
    metadata = json.loads((directory/'provenance.json').read_text())
    require(metadata['status'] == 'accepted' and metadata['automatic_refresh'] is False,
            'accepted Windows gravity reference is missing')
    require(digest((HERE/'protocol.json').read_bytes()) == metadata['protocol_sha256'],
            'accepted gravity protocol changed')
    require(protocol()['budgets'] == metadata['budgets'], 'accepted gravity budgets changed')
    golden = member_path(directory, metadata['trace']['file'])
    require(digest(golden.read_bytes()) == metadata['trace']['sha256'], 'frozen gravity trace changed')
    trace(golden)
    for item in metadata['evidence']:
        path = member_path(directory, item['file'])
        require(digest(path.read_bytes()) == item['sha256'], 'frozen gravity evidence changed')
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'frozen evidence ZIP is corrupt')
            require(set(archive.namelist()) == set(item['members_sha256']) and
                    len(archive.namelist()) == len(item['members_sha256']), 'unmanifested evidence members')
            for name, expected in item['members_sha256'].items():
                require(digest(archive.read(name)) == expected, 'frozen evidence member changed: '+name)
            capture = json.loads(archive.read(item['capture_member']))
            require(capture['status'] == 'passed' and capture['source'] == item['source'] and
                    capture['configuration'] == item['configuration'] and
                    capture['protocol_sha256'] == metadata['protocol_sha256'], 'capture provenance differs')
            first, second = (archive.read(name) for name in item['trace_members'])
            require(first == second, 'accepted Windows repeats differ')
            with tempfile.TemporaryDirectory(prefix='orbiter-gravity-verify-') as temporary:
                candidate = Path(temporary)/'trace.csv'
                candidate.write_bytes(first)
                compare(golden, candidate)
    require({(item['configuration'], item['build']) for item in metadata['evidence']} ==
            {(config, kind) for config in ('Debug', 'Release') for kind in ('standalone', 'application')},
            'both Windows configurations and both build paths are required')
    require(len(metadata['evidence']) == 4, 'expected four accepted Windows builds')
    for item in metadata.get('preparation_failure', {}).get('evidence', []):
        path = member_path(directory, item['file'])
        require(digest(path.read_bytes()) == item['sha256'], 'preparation failure evidence changed')
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'preparation failure ZIP is corrupt')
    return metadata, golden


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=HERE/'Reference')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    metadata, golden = load(args.reference.resolve())
    report = compare(golden, args.candidate) if args.candidate else dict(status='passed')
    report['capture_sources'] = metadata['capture_sources']
    if args.report:
        require(args.reference.resolve() not in args.report.resolve().parents and
                args.report.resolve() != args.reference.resolve(), 'report cannot overwrite accepted evidence')
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
