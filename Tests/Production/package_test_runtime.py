#!/usr/bin/env python3
"""Archive this build's application/SDK for isolated Windows integration tests.

This is a test artifact, not a distributable release or a frozen reference.
Data packages remain separate. A per-file manifest prevents stale/mixed builds.
"""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

from mesa_runtime import digest, require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require((args.build/'Orbiter.exe').is_file(),'source-built Orbiter.exe is missing')
    files=[p for p in args.build.iterdir() if p.is_file() and p.suffix.lower() in ('.exe','.dll','.lib')]
    for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2','Orbitersdk'):
        if (args.build/name).is_dir():files.extend(p for p in (args.build/name).rglob('*') if p.is_file())
    manifest=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
                  purpose='source-built Windows test runtime; not acceptance evidence',
                  files={p.relative_to(args.build).as_posix():digest(p) for p in sorted(files)})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files:archive.write(p,p.relative_to(args.build).as_posix())
        archive.writestr('test-runtime.json',json.dumps(manifest,indent=2)+'\n')
    print('Archived',len(files),'source-built application/SDK files;',args.output.stat().st_size,'bytes')


if __name__=='__main__':main()
