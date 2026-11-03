#!/usr/bin/env python3
"""Check clean rejection of unchanged stock scenes with unavailable dependencies.

These are failure-path regressions. The scenarios remain failed stock cases;
their required vessels are never removed or replaced.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from inventory import ROOT,corpus,digest,require
sys.path.insert(0,str(ROOT/'Tests/Production/WaylandInput'))
from compositor import Compositor


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies','build','assets','data','planets','baseline-report','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--library-directory',type=Path,action='append',required=True)
    p.add_argument('--scenario',action='append',help='Select a previously crashing scene; default is every recorded crash')
    a=p.parse_args()
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name,value.resolve())
    libraries=[path.resolve(strict=True) for path in a.library_directory]
    require(len(set(libraries))==len(libraries) and all(path.is_dir() and ':' not in str(path) for path in libraries),
            'Invalid or duplicate runtime library directory')
    baseline=json.loads(a.baseline_report.read_text())
    current=corpus(a.assets,a.build/'NativeModules')
    require(baseline['lock_sha256']==current['lock_sha256'],'Baseline scenario corpus differs')
    cases={name:case for name,case in baseline['cases'].items() if case.get('returncode',0)<0}
    require(cases and (not a.scenario or set(a.scenario)<=set(cases)),'No matching previously crashing scenes')
    if a.scenario:cases={name:case for name,case in cases.items() if name in a.scenario}
    for name,case in cases.items():
        require(current['cases'][name]['sha256_raw']==case['sha256_raw'],'Scenario changed: '+name)
        require(current['cases'][name]['dependency_problems'],'Negative fixture now has complete dependencies: '+name)
    cache=(a.build/'CMakeCache.txt').read_text()
    for language in ('C','CXX'):
        require('CMAKE_'+language+'_FLAGS:STRING=-fsanitize=address,undefined -fno-omit-frame-pointer' in cache,
                'Instrument both engine C and C++ sources')
    tools=json.loads((a.dependencies/'test-tools.json').read_text())
    wayland=ROOT/'Tests/Production/WaylandInput'
    require(tools['status']=='passed' and tools['lock_sha256']==digest(wayland/'dependencies.lock.json'),
            'Unverified private compositor tools')
    for name,checksum in tools['source_sha256'].items():require(digest(wayland/name)==checksum,'Compositor source drift')
    for name,checksum in tools['outputs_sha256'].items():require(digest(a.dependencies/name)==checksum,'Compositor binary drift')
    inputs=[a.build/'orbiter-production',*sorted(a.build.rglob('*.so')),Path(__file__),
            ROOT/'Src/Orbiter/Vessel.cpp',a.baseline_report]
    inputs += sorted({path.resolve() for directory in libraries for path in directory.glob('*.so*') if path.is_file()})
    before={str(path):digest(path) for path in inputs}
    a.output.mkdir(parents=True,exist_ok=False)
    report=dict(status='failed',phase6_complete=False,cases={},constructor_cases={},files_sha256=before,
                scenario_lock_sha256=current['lock_sha256'],stock_scenarios_qualified=False)
    jobs=[dict(name=name,scenario=a.assets/'Scenarios'/name,original=case,category='cases') for name,case in cases.items()]
    for action in ('create','create_legacy'):
        jobs.append(dict(name=action,scenario=ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn',
                         original=None,category='constructor_cases'))
    try:
        with Compositor(a.dependencies,a.output/'compositor') as compositor:
            for index,job in enumerate(jobs):
                name=job['name'];target=a.output/f'{index:03d}';target.mkdir()
                argv=[a.build/'orbiter-production','--assets',a.assets,'--data',a.data,
                    '--modules',a.build/'NativeModules','--planets',a.planets,
                    '--config',ROOT/'Tests/Production/NativeScene/Orbiter.cfg',
                    '--scenario',job['scenario'],'--evidence',target,
                    '--save',target/'saved.scn','--frames','60','--fixed-step','.25','--run']
                if job['category']=='constructor_cases':
                    tape=target/'replay.csv'
                    tape.write_text('tick,phase,action,value\n0,pre,'+name+',Missing Phase6UnavailableVessel\n')
                    argv += ['--replay',tape]
                (target/'invocation.json').write_text(json.dumps(list(map(str,argv)),indent=2)+'\n')
                environment=dict(compositor.environment,LD_LIBRARY_PATH=':'.join(map(str,[a.build,*libraries])),
                    ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                    UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LIBGL_ALWAYS_SOFTWARE='1',
                    GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2')
                environment.pop('LD_PRELOAD',None)
                with (target/'console.log').open('w') as log:
                    result=subprocess.run(argv,cwd=target,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                text=(target/'console.log').read_text()
                require(result.returncode==1 and 'Orbiter native production: Vessel initialization failed' in text,
                        'Wrong stock dependency rejection: '+name)
                require(not any(marker in text for marker in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:')),
                        'Sanitizer finding during stock rejection: '+name)
                lifecycle=json.loads((target/'graphics-lifecycle.json').read_text())
                require(lifecycle==dict(rendered_frames=0,successful_presents=0,context_deleted=True),
                        'Partial session retained its window or rendered an incomplete scenario: '+name)
                report[job['category']][name]=dict(rejection_status='passed',
                    original_returncode=job['original']['returncode'] if job['original'] else None,
                    returncode=1,scenario_sha256=digest(job['scenario']),
                    context_deleted=True,console_sha256=digest(target/'console.log'),output=target.name)
                if job['category']=='cases':report['cases'][name]['stock_scenario_status']='failed'
                (a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
                print('Clean dependency rejection:',name,flush=True)
        require(before=={str(path):digest(path) for path in inputs},'Sources or binaries changed during rejection tests')
        report.update(status='rejection-regressions-passed',sources_and_binaries_unchanged=True)
    finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
