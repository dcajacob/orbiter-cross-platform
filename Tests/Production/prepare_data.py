#!/usr/bin/env python3
"""Prepare locked official data for production tests; never stage release DLLs.

This is test provisioning, not the final user-facing asset installer. No mutable
latest release lookup or silent version substitution occurs. Existing downloads
are verified against the published release digest before extraction.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import urllib.request
import zipfile

from mesa_runtime import digest, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=Path(__file__).with_name('stock-data.lock.json'))
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    if not args.verify_only:
        require(args.archive is not None, '--archive is required for provisioning')
        archive = args.archive
        if not archive.is_file():
            archive.parent.mkdir(parents=True, exist_ok=True)
            temporary = archive.with_suffix('.partial')
            with urllib.request.urlopen(lock['url'], timeout=180) as stream, temporary.open('wb') as output:
                shutil.copyfileobj(stream, output)
            require(temporary.stat().st_size == lock['bytes'] and digest(temporary) == lock['sha256'],
                    'official stock package does not match frozen release; obtain the recorded asset, do not update the lock')
            temporary.replace(archive)
        require(archive.stat().st_size == lock['bytes'] and digest(archive) == lock['sha256'],
                'stock package SHA256 mismatch')
        args.destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            for name in lock['data_files']:
                path = PurePosixPath(name)
                require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
                        'invalid locked data path')
                destination = args.destination.joinpath(*path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source.open(name) as stream, destination.open('wb') as output:
                    shutil.copyfileobj(stream, output)
    for name, entry in lock['data_files'].items():
        path = args.destination / name
        require(path.is_file() and path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'],
                'missing or incompatible production data: ' + name)
    for name in lock.get('required_files', ['Kernels/orbiter.bsp']):
        require((args.destination/name).is_file(), 'required data file is missing: '+name)
    print(f"Verified {len(lock['data_files'])} production data files; package {lock['sha256']}")


if __name__ == '__main__':
    main()
