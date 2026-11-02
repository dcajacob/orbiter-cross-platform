#!/usr/bin/env python3
"""Stage the locked Mesa DLLs using Python 3.14's in-process Zstandard reader.

The original mesa_runtime.py is a frozen reference input. Its WGL execution and
loaded-module audit remain authoritative; this replaces only archive staging.
"""
import argparse
from compression import zstd
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import urllib.request

sys.dont_write_bytecode = True
from mesa_runtime import digest, require


def stage(lock_path, cache, destination):
    lock = json.loads(lock_path.read_text())
    destination.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    files, packages = {}, []
    for package in lock['packages']:
        filename = package['filename']
        require(PurePosixPath(filename).name == filename and '\\' not in filename
                and ':' not in filename, 'invalid package filename')
        require(package['url'] == lock['mirror'] + filename, 'unexpected package origin')
        archive = cache / filename
        if not archive.is_file() or digest(archive) != package['sha256']:
            partial = archive.with_suffix('.partial')
            with urllib.request.urlopen(package['url'], timeout=120) as source, partial.open('wb') as output:
                shutil.copyfileobj(source, output)
            require(digest(partial) == package['sha256'], 'package hash mismatch: ' + filename)
            partial.replace(archive)
        # Stream only regular DLL and license contents. No archive paths or links
        # are passed to an extractor, and unused developer files stay compressed.
        with tarfile.open(archive, mode='r|zst') as contents:
            for member in contents:
                relative = PurePosixPath(member.name)
                is_dll = relative.parts[:2] == ('ucrt64', 'bin') and relative.suffix.lower() == '.dll'
                is_license = relative.parts[:3] == ('ucrt64', 'share', 'licenses')
                if member.isdir() or not (is_dll or is_license):
                    continue
                require(not relative.is_absolute() and '..' not in relative.parts
                        and '\\' not in member.name and ':' not in member.name,
                        'invalid runtime archive path: ' + member.name)
                require(member.isfile(), 'runtime links and special files are unsupported: ' + member.name)
                target = (destination / relative.name if is_dll else
                          destination / 'licenses' / Path(*relative.parts[3:]))
                require(destination.resolve() in target.resolve().parents,
                        'runtime path escapes destination: ' + member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_name(target.name + '.partial')
                with contents.extractfile(member) as source, partial.open('wb') as output:
                    shutil.copyfileobj(source, output)
                require(partial.stat().st_size == member.size, 'incomplete runtime file: ' + member.name)
                checksum = digest(partial)
                if target.exists():
                    require(digest(target) == checksum, 'conflicting runtime files: ' + str(target))
                    partial.unlink()
                else:
                    partial.replace(target)
                files[target.relative_to(destination).as_posix()] = dict(sha256=checksum, package=package['name'])
        packages.append(dict(name=package['name'], sha256=digest(archive)))
    require('opengl32.dll' in files and 'libgallium_wgl.dll' in files, 'WGL Mesa driver is missing')
    manifest = dict(lock_sha256=digest(lock_path), packages=packages, files=files)
    (destination / 'mesa-runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
    metadata = dict(python=sys.version, executable=sys.executable, zstandard=zstd.zstd_version,
                    stager_sha256=digest(Path(__file__).resolve()), reader='tarfile r|zst (in process)')
    (destination / 'mesa-extractor.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata), flush=True)
    print(f"Staged {len(packages)} locked packages and {len(files)} runtime/license files", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage'])
    parser.add_argument('--lock', type=Path, default=Path(__file__).with_name('mesa-ucrt64.lock.json'))
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    stage(args.lock, args.cache, args.destination)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, tarfile.TarError, zstd.ZstdError) as error:
        raise SystemExit(str(error)) from error
