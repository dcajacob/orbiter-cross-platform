#!/usr/bin/env python3
"""Create a Launchpad profile using the private Mesa software renderer."""

import argparse
import hashlib
import json
from pathlib import Path


MESA_SOURCE_LOCK = (Path(__file__).resolve().parents[2] / 'Tests/Production'
                    / 'GraphicsDriverLifetime/mesa-source.lock.json')
PROFILE_PATHS = ('executable', 'assets', 'data', 'modules', 'planets', 'config',
                 'keymap', 'saves', 'help', 'xrsoundAssets')


def private_driver(build):
    manifest = json.loads((build / 'driver-build.json').read_text())
    lock = json.loads(MESA_SOURCE_LOCK.read_text())
    if (manifest['status'] != 'built' or manifest['source_lock'] != lock
            or 'x11' not in manifest.get('platforms', ['x11'])):
        raise ValueError('Expected an X11 build of the locked Mesa cleanup candidate')

    prefix = build / 'install'
    libraries = prefix / 'lib/x86_64-linux-gnu'
    egl = prefix / 'share/glvnd/egl_vendor.d/50_mesa.json'
    version = lock['source_directory'].removeprefix('mesa-')
    for name in (f'libgallium-{version}.so', 'libGLX_mesa.so.0.0.0', 'libEGL_mesa.so.0.0.0'):
        with (libraries / name).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != manifest['libraries'].get(name):
            raise ValueError(f'Mesa library does not match its build manifest: {name}')
    for name in ('libGLX_mesa.so.0', 'libEGL_mesa.so.0'):
        if (libraries / name).resolve(strict=True) != libraries / (name + '.0.0'):
            raise ValueError(f'Mesa runtime alias does not select the verified library: {name}')
    if json.loads(egl.read_text())['ICD']['library_path'] != 'libEGL_mesa.so.0':
        raise ValueError('Mesa EGL manifest does not select the verified library')
    return libraries, egl


def make_profile(source, build, output):
    profile = json.loads(source.read_text())
    if not isinstance(profile, dict) or profile.get('mode') != 'native':
        raise ValueError('Expected a native Linux simulator profile')
    libraries, egl = private_driver(build)
    for key in PROFILE_PATHS:
        if path := profile.get(key):
            profile[key] = str(source.parent / path)

    environment = profile.setdefault('environment', {})
    unset = profile.setdefault('unsetEnvironment', [])
    if not isinstance(environment, dict) or not isinstance(unset, list):
        raise ValueError('Expected a profile environment object and unsetEnvironment array')
    library_path = ':'.join(filter(None, (str(libraries), environment.get('LD_LIBRARY_PATH'))))
    environment.update(LD_LIBRARY_PATH=library_path, LIBGL_ALWAYS_SOFTWARE='1',
                       GALLIUM_DRIVER='llvmpipe', XDG_SESSION_TYPE='x11', LP_NUM_THREADS='2',
                       __GLX_VENDOR_LIBRARY_NAME='mesa', __EGL_VENDOR_LIBRARY_FILENAMES=str(egl),
                       MESA_SHADER_CACHE_DIR=str(output.with_suffix('.shader-cache')))
    # Launchpad applies overrides after removals, so remove conflicts in both places.
    for key in ('WAYLAND_DISPLAY', 'MESA_LOADER_DRIVER_OVERRIDE', 'LIBGL_DRIVERS_PATH'):
        environment.pop(key, None)
        if key not in unset:
            unset.append(key)
    with output.open('x') as stream:
        json.dump(profile, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'mesa-build', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        make_profile(args.profile.absolute(), args.mesa_build.resolve(), args.output.absolute())
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f'{parser.prog}: {error}\n')


if __name__ == '__main__':
    main()
