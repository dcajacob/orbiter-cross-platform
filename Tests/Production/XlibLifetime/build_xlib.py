#!/usr/bin/env python3
"""Build a checksum-pinned Xlib unload-cleanup candidate into a new owned prefix."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cache', 'output'):
        parser.add_argument('--'+name, type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    require(1 <= args.jobs <= 128, 'Invalid parallel build count')
    require(not args.output.exists(), 'Xlib build output exists; replacement is forbidden')
    lock = json.loads((HERE/'source.lock.json').read_text())
    cleanup = HERE/lock['cleanup_patch']['file']
    require(digest(cleanup) == lock['cleanup_patch']['sha256'], 'Xlib cleanup patch differs from lock')
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True)
    report = dict(status='building', source_lock=lock, sanitizers=args.sanitize, commands=[])
    try:
        for name, entry in lock['archives'].items():
            require(Path(name).name == name, 'Invalid archive name')
            archive = args.cache/name
            if not archive.exists():
                require(not args.offline, 'Missing offline Xlib source archive: '+name)
                temporary = archive.with_suffix(archive.suffix+'.download')
                with urllib.request.urlopen(entry['url'], timeout=60) as source, temporary.open('wb') as target:
                    shutil.copyfileobj(source, target)
                require(digest(temporary) == entry['sha256'] and temporary.stat().st_size == entry['bytes'],
                        'Downloaded Xlib source differs: '+name)
                temporary.replace(archive)
            require(digest(archive) == entry['sha256'] and archive.stat().st_size == entry['bytes'],
                    'Cached Xlib source differs: '+name)
        source_parent = args.output/'source'
        source_parent.mkdir()
        with tarfile.open(args.cache/'libx11_1.8.13.orig.tar.gz') as archive:
            archive.extractall(source_parent, filter='data')
        source = source_parent/'libX11-1.8.13'

        def run(command, name, cwd):
            report['commands'].append(dict(command=command, cwd=str(cwd)))
            with (args.output/(name+'.log')).open('w') as log:
                subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)

        packaging = args.output/'ubuntu-packaging.patch'
        packaging.write_bytes(gzip.decompress((args.cache/'libx11_1.8.13-1ubuntu0.1.diff.gz').read_bytes()))
        run(['patch', '--batch', '--forward', '-p1', '-i', str(packaging)], 'packaging', source)
        series = [line.split('#', 1)[0].strip() for line in (source/'debian/patches/series').read_text().splitlines()]
        series = [line for line in series if line]
        require(series == [p['file'] for p in lock['distribution_patches']], 'Ubuntu Xlib patch queue differs')
        for index, entry in enumerate(lock['distribution_patches']):
            patch = source/'debian/patches'/entry['file']
            require(patch.resolve().is_relative_to(source/'debian/patches') and digest(patch) == entry['sha256'],
                    'Ubuntu Xlib patch differs: '+entry['file'])
            run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)], 'distribution-patch-'+str(index), source)
        run(['patch', '--batch', '--forward', '-p1', '-i', str(cleanup)], 'cleanup-patch', source)
        prefix = args.output/'install'
        build = args.output/'build'
        build.mkdir()
        flags = '-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined' if args.sanitize else '-O2 -g -fno-omit-frame-pointer'
        compiler = shutil.which('cc')
        require(compiler, 'A C compiler is required')
        report['compiler'] = subprocess.check_output([compiler, '--version'], text=True).splitlines()[0]
        configure = [str(source/'configure'), '--prefix='+str(prefix), '--libdir='+str(prefix/'lib'),
                     '--disable-static', '--disable-specs', '--without-xmlto', '--without-fop',
                     '--without-xsltproc', 'CC='+compiler, 'CFLAGS='+flags]
        if args.sanitize:
            configure.append('LDFLAGS=-fsanitize=address,undefined')
        run(configure, 'configure', build)
        configuration = (build/'src/config.h').read_text()
        for feature in ('USE_THREAD_SAFETY_CONSTRUCTOR', 'COMPOSECACHE', 'XLOCALE', 'XTHREADS'):
            require('#define '+feature+' 1' in configuration, 'Unsupported Xlib feature configuration: '+feature)
        run(['make', '-j'+str(args.jobs)], 'build', build)
        run(['make', 'install'], 'install', build)
        require((prefix/'lib/libX11.so.6.4.0').is_file(), 'Built Xlib shared library missing')
        notices = prefix/'share/orbiter-xlib-cleanup'
        notices.mkdir(parents=True)
        for path in (source/'COPYING', HERE/'source.lock.json', cleanup):
            shutil.copyfile(path, notices/path.name)
        report['installed_library_sha256'] = {p.relative_to(prefix).as_posix(): digest(p)
            for p in (prefix/'lib').glob('*.so*') if p.is_file()}
        report['changed_source_sha256'] = {name: digest(source/name) for name in lock['cleanup_patch']['changed_files']}
        report['status'] = 'built'
        print('Built isolated Xlib candidate:', prefix)
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (args.output/'xlib-build.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
