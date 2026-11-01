#!/usr/bin/env python3
"""Read-only verification of explicitly accepted original Windows archives."""
import argparse
import json
from pathlib import Path, PurePosixPath
import zipfile

from observations import HERE, ROOT, protocol, require, sha


def observations(report):
    lock = protocol()
    require(report['status']=='passed' and report['automatic_refresh'] is False,
            'archive capture did not pass')
    require(report['protocol']==lock and report['protocol_sha256']==sha((HERE/'protocol.json').read_bytes()),
            'archive capture protocol differs')
    stock = json.loads((ROOT/'Tests/Production/standard-planets.lock.json').read_text())['data_files']
    rows = report['observations']
    require(set(rows)==set(stock)|{'fixture/records','fixture/sparse64'}, 'archive coverage differs')
    for name, row in rows.items():
        require(row['nodes']>0 and len(row['queries'])==lock['queries_per_archive'], 'archive node/query count differs')
        require(len(row['toc_sha256'])==64 and len(row['observation_sha256'])==64, 'archive hashes missing')
        if name in stock:
            require(row['inputs']==stock[name], 'stock archive identity differs: '+name)
        elif name=='fixture/sparse64':
            require(row['inputs']['bytes']>1<<32, '64-bit file-offset fixture is absent')
        for query in row['queries']:
            require(query['decoded']==query['inflated'] and len(query['payload_sha256'])==64,
                    'incomplete archive decode')
    return rows


def compare(left, right):
    require(observations(left)==observations(right), 'archive indices, TOC, input or decoded bytes differ')
    return dict(status='passed',archives=len(left['observations']),queries=1200,
                comparison='exact integer identities and decoded bytes')


def load(directory=HERE/'Reference'):
    directory = directory.resolve()
    provenance = json.loads((directory/'provenance.json').read_text())
    require(provenance['status']=='accepted' and provenance['automatic_refresh'] is False,
            'original Windows archive reference is not accepted')
    require(provenance['protocol_sha256']==sha((HERE/'protocol.json').read_bytes()), 'accepted archive protocol changed')
    captures = []
    configurations = set()
    for item in provenance['evidence']:
        relative = PurePosixPath(item['file'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'invalid archive evidence path')
        path = (directory/relative).resolve()
        require(path.is_relative_to(directory), 'archive evidence escaped the reference directory')
        require(sha(path.read_bytes())==item['sha256'], 'accepted Windows artifact changed')
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'accepted Windows artifact is corrupt')
            require(set(archive.namelist())==set(item['members_sha256']) and
                    len(archive.namelist())==len(item['members_sha256']), 'archive evidence contains undeclared members')
            for name, checksum in item['members_sha256'].items():
                require(sha(archive.read(name))==checksum, 'archive evidence member changed: '+name)
            capture = json.loads(archive.read(item['capture_member']))
        require(capture['source']==item['source'] and capture['configuration']==item['configuration'] and
                capture['host'].startswith('Windows'), 'original Windows capture provenance differs')
        observations(capture)
        require(item['configuration'] not in configurations, 'duplicate archive configuration')
        configurations.add(item['configuration'])
        captures.append(capture)
    require(configurations=={'Debug','Release'} and len(captures)==2, 'both original Windows builds are required')
    compare(*captures)
    return provenance, captures[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=HERE/'Reference')
    parser.add_argument('--left', type=Path)
    parser.add_argument('--candidate', type=Path)
    args = parser.parse_args()
    if args.left:
        require(args.candidate is not None, '--left requires --candidate')
        result = compare(json.loads(args.left.read_text()),json.loads(args.candidate.read_text()))
    else:
        _, golden = load(args.reference)
        result = compare(golden,json.loads(args.candidate.read_text())) if args.candidate else dict(status='passed')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
