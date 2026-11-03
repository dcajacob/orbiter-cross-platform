#!/usr/bin/env python3
"""Reject invalid startup requests and release GLFW before any window exists."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from compositor import Compositor

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies','build','assets','data','planets','fontconfig-libraries','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--unsupported-egl-libraries',type=Path,
                   help='Optional verified X11-only Mesa prefix for a real Wayland EGL creation rejection')
    a=p.parse_args()
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name,value.resolve())
    a.output.mkdir(parents=True,exist_ok=False)
    tools=json.loads((a.dependencies/'test-tools.json').read_text())
    if tools['status']!='passed' or tools['lock_sha256']!=digest(HERE/'dependencies.lock.json'):
        raise ValueError('Unverified compositor tools')
    for name,checksum in tools['source_sha256'].items():
        if digest(HERE/name)!=checksum:raise ValueError('Compositor source differs')
    for name,checksum in tools['outputs_sha256'].items():
        if digest(a.dependencies/name)!=checksum:raise ValueError('Compositor binary differs')
    inputs=[a.build/'orbiter-production',*sorted(a.build.rglob('*.so')),Path(__file__),
            ROOT/'OVP/OGLClient/Native/LinuxAdapter.cpp']
    before={str(path):digest(path) for path in inputs}
    report=dict(status='failed',phase6_complete=False,cases={},files_sha256=before)
    try:
        with Compositor(a.dependencies,a.output/'compositor') as compositor:
            cases=[('width-zero',0),('width-too-large',20000)]
            if a.unsupported_egl_libraries:cases.append(('unsupported-egl',None))
            for name,value in cases:
                target=a.output/name;target.mkdir();config=target/'Orbiter.cfg'
                config.write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                                  (f'\nWindowWidth = {value}\n' if value is not None else ''))
                libraries=[a.build,a.fontconfig_libraries]
                if value is None:libraries.append(a.unsupported_egl_libraries)
                environment=dict(compositor.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',
                    LP_NUM_THREADS='2',LD_LIBRARY_PATH=':'.join(map(str,libraries)),
                    ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                    UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                environment.pop('LD_PRELOAD',None)
                argv=[a.build/'orbiter-production','--assets',a.assets,'--data',a.data,'--modules',a.build/'NativeModules',
                    '--planets',a.planets,'--scenario',ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn',
                    '--config',config,'--evidence',target,'--frames','1','--fixed-step','0.25','--run']
                with (target/'console.log').open('w') as log:
                    result=subprocess.run(argv,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=60)
                text=(target/'console.log').read_text()
                expected='Native OpenGL window creation failed' if value is None else 'Native window dimensions are outside the supported range'
                if result.returncode!=1 or expected not in text:raise ValueError('Wrong startup rejection: '+name)
                if any(marker in text for marker in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:')):
                    raise ValueError('Startup rejection did not release its resources: '+name)
                report['cases'][name]=dict(status='passed',returncode=result.returncode,
                    expected_rejection=expected,console_sha256=digest(target/'console.log'))
        if before!={str(path):digest(path) for path in inputs}:raise ValueError('Sources or runtime changed')
        report.update(status='passed',sources_and_binaries_unchanged=True)
    finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Startup rejection paths released GLFW without sanitizer findings')


if __name__=='__main__':main()
