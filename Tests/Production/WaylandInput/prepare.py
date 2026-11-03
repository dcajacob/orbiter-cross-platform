#!/usr/bin/env python3
"""Extract locked compositor packages privately and build only the owned test tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'cache', 'glfw-build'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    out, cache, glfw = a.output.resolve(), a.cache.resolve(), a.glfw_build.resolve()
    lock_path = HERE/'dependencies.lock.json'
    lock = json.loads(lock_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    cache.mkdir(parents=True, exist_ok=True)
    manifest = dict(status='failed', lock_sha256=digest(lock_path), packages=[],
                    weston_version=lock['weston_version'], scope=lock['scope'])
    try:
        for entry in lock['packages']+[lock['source']]:
            filename = entry['filename']
            if Path(filename).name!=filename or not entry['url'].startswith('https://archive.ubuntu.com/ubuntu/pool/'):
                raise ValueError('Unexpected locked package origin')
            archive = cache/filename
            if not archive.exists():
                partial = cache/(filename+'.partial')
                with urllib.request.urlopen(entry['url'], timeout=120) as source, partial.open('xb') as target:
                    shutil.copyfileobj(source, target)
                if partial.stat().st_size!=entry['size'] or digest(partial)!=entry['sha256']:
                    raise ValueError('Downloaded package differs: '+filename)
                partial.rename(archive)
            if archive.stat().st_size!=entry['size'] or digest(archive)!=entry['sha256']:
                raise ValueError('Cached package differs: '+filename)
            if entry is lock['source']:
                with tarfile.open(archive) as source:
                    source.extractall(out/'source', filter='data')
            else:
                subprocess.run(['dpkg-deb', '-x', str(archive), str(out/'root')], check=True)
                manifest['packages'].append(entry)
        lib = out/'root/usr/lib/x86_64-linux-gnu'
        cflags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', 'wayland-server', 'xkbcommon'], text=True))
        libs = shlex.split(subprocess.check_output(['pkg-config', '--libs', 'wayland-server', 'xkbcommon'], text=True))
        commands = [
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
             '-I'+str(out/'root/usr/include/libweston-14'), '-I'+str(out/'root/usr/include/pixman-1'),
             *cflags, str(HERE/'CompositorInput.c'), '-L'+str(lib), '-lweston-14', *libs,
             '-Wl,--no-undefined', '-o', str(out/'compositor-input.so')],
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I'+str(glfw/'_deps/glfw-src/include'),
             str(HERE/'FocusSink.c'), str(glfw/'_deps/glfw-build/src/libglfw3.a'),
             '-ldl', '-lm', '-lrt', '-pthread', '-o', str(out/'focus-sink')]]
        with (out/'build.log').open('w') as log:
            for command in commands:
                subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        manifest.update(status='passed', commands=commands,
            compiler=subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
            host_dependencies={name:subprocess.check_output(['pkg-config', '--modversion', name], text=True).strip()
                               for name in ('wayland-server', 'xkbcommon')},
            source_sha256={name:digest(HERE/name) for name in ('CompositorInput.c', 'FocusSink.c', 'prepare.py')},
            glfw_sha256=digest(glfw/'_deps/glfw-build/src/libglfw3.a'),
            outputs_sha256={name:digest(out/name) for name in ('compositor-input.so', 'focus-sink',
                'root/usr/bin/weston', 'root/usr/lib/x86_64-linux-gnu/libweston-14.so.0')},
            source_archive=lock['source'])
    finally:
        (out/'test-tools.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Prepared private Weston '+lock['weston_version']+' and owned input tools: '+str(out))


if __name__=='__main__':
    main()
