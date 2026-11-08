#!/usr/bin/env python3
"""Prepare locked official data for production tests; never stage release DLLs.

This is test provisioning, not the final user-facing asset installer. No mutable
latest release lookup or silent version substitution occurs. Existing downloads
are verified against the published release digest before extraction.
"""
import argparse
import json
import os
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
    parser.add_argument('--container-lock', type=Path,
                        default=Path(os.environ['ORBITER_DATA_CONTAINER_LOCK']) if os.environ.get('ORBITER_DATA_CONTAINER_LOCK') else None,
                        help='Explicitly versioned official container; every original locked input remains required')
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    containers = [lock]
    if args.container_lock:
        variant = json.loads(args.container_lock.read_text())
        require(variant['protocol'] == 'production-stock-container-v1' and
                variant['original_profile_sha256'] == digest(args.lock) and
                variant['repository'] == lock['repository'] and
                variant['url'].startswith('https://github.com/' + lock['repository'] + '/releases/download/'),
                'versioned container does not bind the unchanged official input profile')
        containers.append(variant)
    actual_container = None
    if not args.verify_only:
        require(args.archive is not None, '--archive is required for provisioning')
        archive = args.archive
        if not archive.is_file():
            archive.parent.mkdir(parents=True, exist_ok=True)
            temporary = archive.with_suffix('.partial')
            download = containers[-1]
            with urllib.request.urlopen(download['url'], timeout=180) as stream, temporary.open('wb') as output:
                shutil.copyfileobj(stream, output)
            require(temporary.stat().st_size == download['bytes'] and digest(temporary) == download['sha256'],
                    'official stock package does not match frozen release; obtain the recorded asset, do not update the lock')
            temporary.replace(archive)
        checksum = digest(archive)
        matches = [record for record in containers if archive.stat().st_size == record['bytes'] and checksum == record['sha256']]
        require(len(matches) == 1,
                'stock package SHA256 mismatch')
        actual_container = matches[0]
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
    print(f"Verified {len(lock['data_files'])} production data files; original profile package {lock['sha256']}")
    if actual_container:
        print(json.dumps(dict(provisioning_protocol='production-stock-container-v1',
            original_profile_sha256=digest(args.lock), original_package_sha256=lock['sha256'],
            actual_container_sha256=actual_container['sha256'], actual_container_bytes=actual_container['bytes'],
            official_asset_id=actual_container.get('asset_id'),
            versioned_container_lock_sha256=digest(args.container_lock) if args.container_lock else None,
            locked_input_files=len(lock['data_files']), every_original_input_hash_and_length_preserved=True)))


if __name__ == '__main__':
    main()
