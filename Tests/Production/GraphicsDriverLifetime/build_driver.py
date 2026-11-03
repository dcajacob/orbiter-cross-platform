#!/usr/bin/env python3
"""Build the locked Mesa software driver with explicit executable-heap cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--meson', default='meson')
    parser.add_argument('--wayland', action='store_true',
                        help='Build Wayland EGL support alongside X11; requires Wayland development dependencies')
    args = parser.parse_args()
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise ValueError('This qualification driver targets native Linux x86-64')
    if args.jobs < 1:
        raise ValueError('A positive build job count is required')
    meson = shutil.which(args.meson)
    if not meson:
        raise ValueError('Mesa requires Meson >= 1.4.0 and its documented development dependencies')
    lock = json.loads((HERE / 'mesa-source.lock.json').read_text())
    patch = HERE / lock['cleanup_patch']
    if digest(patch) != lock['cleanup_patch_sha256']:
        raise ValueError('Cleanup patch differs from the source lock')
    cache, output = args.cache.resolve(), args.output.resolve()
    if output.exists():
        raise ValueError('Build output already exists; replacement is forbidden')
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True)
    platforms = ['x11', 'wayland'] if args.wayland else ['x11']
    report = dict(status='building', source_lock=lock, platforms=platforms, commands=[])
    try:
        archives = []
        for entry in lock['sources']:
            archive = cache / entry['name']
            if not archive.exists():
                temporary = archive.with_suffix(archive.suffix + '.download')
                with urllib.request.urlopen(entry['url'], timeout=60) as source, temporary.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
                if digest(temporary) != entry['sha256']:
                    raise ValueError('Downloaded source checksum differs: ' + entry['name'])
                temporary.replace(archive)
            if digest(archive) != entry['sha256']:
                raise ValueError('Cached source checksum differs: ' + entry['name'])
            archives.append(archive)
        with tarfile.open(archives[0]) as archive:
            archive.extractall(output, filter='data')
        source = output / lock['source_directory']
        with tarfile.open(archives[1]) as archive:
            archive.extractall(source, filter='data')

        def run(command, name, cwd=None):
            report['commands'].append(dict(command=command, cwd=str(cwd) if cwd else None))
            with (output / (name + '.log')).open('w') as log:
                subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)

        report['distribution_patches'] = []
        for line in (source / 'debian/patches/series').read_text().splitlines():
            name = line.split('#')[0].strip()
            if not name:
                continue
            distribution_patch = (source / 'debian/patches' / name).resolve()
            if not distribution_patch.is_relative_to(source / 'debian/patches'):
                raise ValueError('Distribution patch is outside the source tree')
            run(['patch', '--batch', '-p1', '-i', str(distribution_patch)],
                'distribution-patch-' + str(len(report['distribution_patches'])), source)
            report['distribution_patches'].append(dict(name=name, sha256=digest(distribution_patch)))
        run(['patch', '--batch', '-p1', '-i', str(patch)], 'cleanup-patch', source)
        build, prefix = output / 'build', output / 'install'
        run([meson, 'setup', str(build), str(source), '--prefix', str(prefix),
             '--libdir', 'lib/x86_64-linux-gnu', '--buildtype=debugoptimized',
             '-Dplatforms='+','.join(platforms), '-Dgallium-drivers=llvmpipe', '-Dvulkan-drivers=[]',
             '-Dglx=dri', '-Degl=enabled', '-Dgbm=disabled', '-Dglvnd=enabled',
             '-Dgles1=disabled', '-Dgles2=enabled', '-Dgallium-va=disabled',
             '-Dllvm=enabled', '-Dshared-llvm=enabled', '-Dvalgrind=disabled',
             '-Dlibunwind=disabled', '-Dbuild-tests=false'], 'configure')
        run([meson, 'compile', '-C', str(build), '-j', str(args.jobs)], 'build')
        run([meson, 'install', '-C', str(build), '--no-rebuild'], 'install')
        notices = prefix / 'share/orbiter-mesa'
        notices.mkdir(parents=True)
        shutil.copy2(source / 'docs/license.rst', notices / 'Mesa-license.rst')
        shutil.copy2(HERE / 'mesa-source.lock.json', notices)
        shutil.copy2(patch, notices)
        libraries = prefix / 'lib/x86_64-linux-gnu'
        report['libraries'] = {p.name: digest(p) for p in sorted(libraries.glob('*.so*')) if not p.is_symlink()}
        if set(report['libraries']) != {'libgallium-26.0.8.so', 'libEGL_mesa.so.0.0.0', 'libGLX_mesa.so.0.0.0'}:
            raise ValueError('Unexpected Mesa driver library set')
        report['runtime_environment'] = dict(LD_LIBRARY_PATH=str(libraries),
            __EGL_VENDOR_LIBRARY_FILENAMES=str(prefix / 'share/glvnd/egl_vendor.d/50_mesa.json'),
            LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
            MESA_SHADER_CACHE_DIR=str(output / 'shader-cache'))
        report['status'] = 'built'
        print(json.dumps(report['runtime_environment'], indent=2))
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (output / 'driver-build.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
