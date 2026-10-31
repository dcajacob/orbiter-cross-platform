#!/usr/bin/env python3
"""Record the actual compiler, linker, SDK, dependencies and binary inputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from mesa_runtime import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    build = args.build.resolve()
    cache = {}
    for line in (build/'CMakeCache.txt').read_text(errors='replace').splitlines():
        if not line or line.startswith(('#','//')) or '=' not in line:
            continue
        key, value = line.split('=',1)
        cache[key] = value
    tools = {}
    for key, value in cache.items():
        if key.split(':')[0] in ('CMAKE_C_COMPILER','CMAKE_CXX_COMPILER','CMAKE_LINKER','CMAKE_MAKE_PROGRAM'):
            path = Path(value)
            tools[key] = dict(path=str(path), sha256=digest(path) if path.is_file() else None)
    dependencies = {}
    deps = build/'_deps'
    if deps.exists():
        for source in sorted(deps.glob('*-src')):
            if (source/'.git').exists():
                commit = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip()
                url = subprocess.check_output(['git','-C',str(source),'remote','get-url','origin']).decode().strip()
                dependencies[source.name] = dict(commit=commit, origin=url)
    binaries = {}
    for path in build.rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.dll','.exe') and '_deps' not in path.relative_to(build).parts:
            binaries[path.relative_to(build).as_posix()] = digest(path)
    record = dict(schema=1, tools=tools, dependencies=dependencies, binaries=binaries,
                  cache_sha256=digest(build/'CMakeCache.txt'),
                  environment={key:os.environ.get(key) for key in
                    ('VCToolsVersion','WindowsSDKVersion','VSCMD_VER','CL','_CL_','LINK','CXXFLAGS','CFLAGS','ImageOS','ImageVersion')},
                  cmake_cache=cache)
    lock = json.loads(Path(__file__).with_name('dependencies.lock.json').read_text())
    for name, entry in lock['dependencies'].items():
        if dependencies.get(name.lower()+'-src', {}).get('commit') != entry['commit']:
            raise ValueError('production dependency differs from locked reference: '+name)
    (build/'build-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f"Recorded {len(tools)} build tools, {len(dependencies)} source dependencies and {len(binaries)} binaries")


if __name__ == '__main__':
    main()
