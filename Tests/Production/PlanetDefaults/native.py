#!/usr/bin/env python3
"""Check actual default/explicit cloud flags through read-only SDK observations."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def cache(build):
    return dict(line.split('=',1) for line in (build/'CMakeCache.txt').read_text().splitlines()
                if '=' in line and not line.startswith(('#','//')))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','renderer-build','assets','data','planets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sanitizers',action='store_true')
    a=p.parse_args()
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name.replace('-','_'),value.resolve())
    a.output.mkdir(parents=True,exist_ok=False)
    caches=[cache(a.build),cache(a.renderer_build)]
    flags=['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if a.sanitizers else []
    if a.sanitizers:
        for c in caches:
            for language in ('C','CXX'):
                if not all(flag in c['CMAKE_'+language+'_FLAGS:STRING'].split() for flag in flags):
                    raise ValueError('Both engine and renderer must instrument C and C++')
    compiler=caches[0]['CMAKE_CXX_COMPILER:FILEPATH']
    probe=a.output/'planet-defaults-probe.so'
    subprocess.run([compiler,'-std=c++17','-fPIC','-shared','-Wl,--no-undefined',*flags,
        '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(HERE/'NativeProbe.cpp'),
        '-L'+str(a.build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)],check=True)
    environment=dict(os.environ,LD_PRELOAD=str(probe),LD_LIBRARY_PATH=str(a.build)+
        (':'+os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else ''))
    if a.sanitizers:
        runtime=subprocess.check_output([compiler,'-print-file-name=libasan.so'],text=True).strip()
        if not Path(runtime).is_file():raise ValueError('ASan runtime missing')
        environment.update(LD_PRELOAD=runtime+':'+str(probe),
            ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    sources=[HERE/'native.py',HERE/'NativeProbe.cpp',ROOT/'Src/Orbiter/Planet.cpp',ROOT/'OVP/OGLClient/Scene.cpp']
    inputs=[a.build/'orbiter-production',*sorted(a.build.rglob('*.so')),*sources,
        *(a.assets/'Config'/(name+'.cfg') for name in ('Earth','Venus','Triton','Moon')),
        ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn']
    before={str(path):digest(path) for path in inputs}
    argv=[a.build/'orbiter-production','--scenario',ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn',
        '--config',ROOT/'Tests/Production/NativeScene/Orbiter.cfg','--assets',a.assets,'--data',a.data,
        '--modules',a.build/'NativeModules','--planets',a.planets,'--evidence',a.output,
        '--frames','60','--fixed-step','0.25','--run']
    (a.output/'invocation.json').write_text(json.dumps(list(map(str,argv)),indent=2)+'\n')
    with (a.output/'console.log').open('w') as log:
        subprocess.run(argv,cwd=a.output,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    rows=list(csv.DictReader((a.output/'planet-defaults.csv').read_text().splitlines()))
    expected={'Earth':'1','Venus':'1','Triton':'0','Moon':'0'}
    if len(rows)!=240 or any(row!=dict(tick=str(tick),planet=name,cloud_microtexture=value)
        for row,(tick,(name,value)) in zip(rows,((tick,item) for tick in range(60) for item in expected.items()))):
        raise ValueError('Actual configured planet flags differ or observations are incomplete')
    lifecycle=json.loads((a.output/'graphics-lifecycle.json').read_text())
    if lifecycle!=dict(rendered_frames=60,successful_presents=60,context_deleted=True):
        raise ValueError('Planet-property session did not finish normally')
    if before!={str(path):digest(path) for path in inputs}:raise ValueError('Sources or runtime changed during capture')
    report=dict(status='passed',phase6_complete=False,sanitizers=a.sanitizers,
        actual_planet_flags=expected,observations=len(rows),lifecycle=lifecycle,files_sha256=before,
        c_flags=[c['CMAKE_C_FLAGS:STRING'] for c in caches],cxx_flags=[c['CMAKE_CXX_FLAGS:STRING'] for c in caches])
    (a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Actual planet defaults and explicit settings passed 240 observations and 60 complete presentations')


if __name__=='__main__':main()
