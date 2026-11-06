#!/usr/bin/env python3
"""Independently restore and hash a closed local ZIP before planning duplicate reclamation."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from contracts import atomic_json, load, require, sha


def safe_name(name):
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and '..' not in path.parts and
            '\\' not in name and ':' not in name and str(path) == name,
            'Unsafe archive member')
    return path


def verify_archive(archive, expected_sha, expected_members, scratch):
    require(sha(archive) == expected_sha, 'Archive digest differs')
    restored = {}
    total = 0
    with tempfile.TemporaryDirectory(prefix='phase6-restore-', dir=scratch) as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(archive) as source:
            members = source.infolist()
            require(len(members) == len({item.filename for item in members}) == len(expected_members),
                    'Archive member closure differs')
            require(set(source.namelist()) == set(expected_members), 'Archive file inventory differs')
            for item in members:
                name = safe_name(item.filename)
                require(not item.is_dir() and (item.external_attr >> 16) & 0o170000 != 0o120000,
                        'Archive must contain regular byte files')
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as src, target.open('xb') as dst:
                    for chunk in iter(lambda: src.read(1024 * 1024), b''):
                        dst.write(chunk)
                # Separate restored-file read: do not treat ZIP CRC as SHA proof.
                digest = sha(target)
                require(digest == expected_members[item.filename] and target.stat().st_size == item.file_size,
                        'Restored archive bytes differ: ' + item.filename)
                restored[item.filename] = dict(sha256=digest, bytes=item.file_size)
                total += item.file_size
    require(sha(archive) == expected_sha, 'Archive changed during restoration')
    return dict(status='passed-independent-full-archive-restoration', archive=str(archive.resolve()),
                archive_sha256=expected_sha, archive_bytes=archive.stat().st_size,
                restored_files=restored, restored_bytes=total, temporary_restoration_removed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Fresh storage audit output required')
    manifest_sha = sha(args.manifest)
    manifest = load(args.manifest)
    result = dict(status='running', manifest_sha256=manifest_sha, profiles={},
                  raw_evidence_uploaded=False, phase6_complete=False)
    try:
        for profile, record in manifest['profiles'].items():
            archive = args.archives / safe_name(record['archive'])
            result['profiles'][profile] = verify_archive(archive, record['sha256'], record['files_sha256'], args.scratch)
            atomic_json(args.output, result)
        require(sha(args.manifest) == manifest_sha, 'Preservation manifest changed')
        result['status'] = 'passed-independent-all-archive-restorations'
    except BaseException as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        atomic_json(args.output, result)


if __name__ == '__main__':
    main()
