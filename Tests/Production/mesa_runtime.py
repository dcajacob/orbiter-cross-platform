#!/usr/bin/env python3
"""Stage the pinned official UCRT64 Mesa dependency closure, then audit real WGL.

No package resolution occurs in CI. Update the reviewed lock explicitly using
official MSYS2 metadata; never overwrite a Windows or system installation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import subprocess
import sys
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def stage(lock_path, cache, destination):
    lock = json.loads(lock_path.read_text())
    destination.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    files = {}
    packages = []
    for package in lock['packages']:
        archive = cache / package['filename']
        require(Path(package['filename']).name == package['filename'], 'invalid package filename')
        if not archive.is_file() or digest(archive) != package['sha256']:
            require(package['url'] == lock['mirror'] + package['filename'], 'unexpected package origin')
            partial = archive.with_suffix('.partial')
            with urllib.request.urlopen(package['url'], timeout=120) as source, partial.open('wb') as output:
                shutil.copyfileobj(source, output)
            require(digest(partial) == package['sha256'], 'package hash mismatch: ' + package['filename'])
            partial.replace(archive)
        directory = cache / (package['name'] + '-extracted')
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()
        # Windows bsdtar and GNU tar with zstd both understand .pkg.tar.zst.
        members=subprocess.check_output(['tar','-tf',str(archive.resolve())],text=True,encoding='utf-8').splitlines()
        selected=[]
        for member in members:
            if member.endswith('/'):continue
            relative=PurePosixPath(member)
            if ((relative.parts[:2]==('ucrt64','bin') and relative.suffix.lower()=='.dll') or
                    relative.parts[:3]==('ucrt64','share','licenses')):
                require(not relative.is_absolute() and '..' not in relative.parts,'invalid runtime archive path')
                selected.append(member)
        # Do not expand unused headers, static archives and development tools.
        # The complete pinned package is still hashed before extraction.
        if selected:
            subprocess.run(['tar','-xf',str(archive.resolve()),'-C',str(directory.resolve()),*selected],check=True)
        for source in sorted(directory.rglob('*')):
            if not source.is_file():
                continue
            relative = source.relative_to(directory)
            if source.suffix.lower() == '.dll' and relative.parts[:2] == ('ucrt64', 'bin'):
                target = destination / source.name
            elif relative.parts[:3] == ('ucrt64', 'share', 'licenses'):
                target = destination / 'licenses' / Path(*relative.parts[3:])
            else:
                continue
            require(not source.is_symlink(), 'runtime symlinks are unsupported: ' + str(relative))
            if target.exists():
                require(digest(target) == digest(source), 'conflicting runtime files: ' + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            key = target.relative_to(destination).as_posix()
            files[key] = dict(sha256=digest(target), package=package['name'])
        packages.append(dict(name=package['name'], sha256=digest(archive)))
    require('opengl32.dll' in files and 'libgallium_wgl.dll' in files, 'WGL Mesa driver is missing')
    manifest = dict(lock_sha256=digest(lock_path), packages=packages, files=files)
    (destination / 'mesa-runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Staged {len(packages)} locked packages and {len(files)} runtime/license files")


def probe(executable, output):
    require(sys.platform == 'win32', 'WGL execution requires native Windows')
    executable = executable.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runtime = json.loads((executable.parent / 'mesa-runtime.json').read_text())
    report = dict(status='pending', executable_sha256=digest(executable),
                  runtime_lock_sha256=runtime['lock_sha256'], loaded_modules=[], python=sys.version)
    try:
        environment = dict(os.environ, LIBGL_ALWAYS_SOFTWARE='true', GALLIUM_DRIVER='llvmpipe')
        with (output / 'probe.log').open('w') as log:
            subprocess.run([str(executable), str((output / 'readback').resolve())], cwd=output,
                           env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        lines = (output / 'probe.log').read_text()
        require(sum(line.startswith('cycle=') and line.endswith(' passed') for line in lines.splitlines()) == 3
                and 'WGL bootstrap passed' in lines, 'incomplete WGL execution')
        require('llvmpipe' in lines, 'reported renderer is not llvmpipe')
        system = Path(os.environ['SystemRoot']).resolve()
        for cycle in range(3):
            names = set()
            for line in (output / f'readback-{cycle}-modules.txt').read_text(encoding='utf-8').splitlines():
                path = Path(line).resolve()
                names.add(path.name.lower())
                if path.suffix.lower() != '.dll':
                    continue
                entry = dict(cycle=cycle, path=str(path), sha256=digest(path))
                if path.parent == executable.parent:
                    expected = {name.casefold(): value for name, value in runtime['files'].items()}.get(path.name.casefold())
                    require(expected is not None and expected['sha256'] == entry['sha256'],
                            'unlocked application-local DLL: ' + str(path))
                    entry['package'] = expected['package']
                else:
                    require(system in path.parents, 'unexpected non-system DLL: ' + str(path))
                    entry['origin'] = 'Windows runner system image'
                if path.name.lower() in ('opengl32.dll', 'libgallium_wgl.dll'):
                    require(path.parent == executable.parent, 'Mesa was not loaded application-local')
                report['loaded_modules'].append(entry)
            require({'opengl32.dll', 'libgallium_wgl.dll'} <= names, 'required Mesa DLLs were not loaded')
            pixels = (output / f'readback-{cycle}.rgba').read_bytes()
            require(len(pixels) == 4096, 'incomplete FBO readback')
        report['status'] = 'passed'
        report['driver_output'] = lines.splitlines()
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (output / 'wgl-report.json').write_text(json.dumps(report, indent=2) + '\n')
        shutil.copy2(executable.parent / 'mesa-runtime.json', output / 'mesa-runtime.json')
    print('Native Windows WGL/shader/FBO/present/resize/shutdown and loaded-DLL audit passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    install = commands.add_parser('stage')
    install.add_argument('--lock', type=Path, default=Path(__file__).with_name('mesa-ucrt64.lock.json'))
    install.add_argument('--cache', type=Path, required=True)
    install.add_argument('--destination', type=Path, required=True)
    run = commands.add_parser('probe')
    run.add_argument('--executable', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'stage':
        stage(args.lock, args.cache, args.destination)
    else:
        probe(args.executable, args.output)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
