#!/usr/bin/env python3
"""Run the Windows synchronous/asynchronous command schedule on the real Linux interpreter."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import zipfile

from capture import lua_fixture, settings, validate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('assets','build','data','planets','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--original',type=Path,help='Original Windows capture ZIP for diagnostic comparison')
    parser.add_argument('--original-profile',choices=('original-default','diagnostic-sse2'),default='original-default')
    args=parser.parse_args()
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    original_directory='diagnostic-sse2' if args.original_profile=='diagnostic-sse2' else 'control-reference'
    if args.original:
        with zipfile.ZipFile(args.original) as archive:
            original_report=json.loads(archive.read('out/'+original_directory+'/lua-report.json'))
        if (original_report['status']!='passed' or original_report['math_profile']!=args.original_profile or
                original_report['runtime']['application_source']!=settings()['application_source']):
            raise ValueError('Original Lua capture failed, has the wrong profile, or uses a different application')
        (output/'original-capture.json').write_text(json.dumps({key:original_report[key] for key in
            ('status','source','configuration','math_profile','host')},indent=2)+'\n')
    build=args.build.resolve()
    compiler=next(line.split('=',1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                  if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    probe=output/'lua-schedule-probe.so'
    subprocess.run([compiler,'-std=c++17','-fPIC','-shared','-Wl,--no-undefined',
                    '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(HERE/'NativeProbe.cpp'),
                    '-L'+str(build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',probe],check=True)
    report={}
    for case in settings()['cases']:
        out=output/case['id'];out.mkdir()
        (out/'flight.scn').write_text(lua_fixture(case))
        (out/'lua-case.txt').write_text(case['target']+' '+('atmosphere' if 'stock_atmosphere' in case else 'orbit'))
        (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                                       '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
        (out/'replay.csv').write_text('tick,phase,action,value\n'+
            f"0,pre,mfd,0 {case['left']}\n0,pre,mfd,1 {case['right']}\n0,pre,hud,{case['hud']}\n")
        command=[build/'orbiter-production','--scenario',out/'flight.scn','--config',out/'Orbiter.cfg','--save',out/'saved.scn',
                 '--assets',args.assets.resolve(),'--data',args.data.resolve(),'--modules',build/'NativeModules',
                 '--planets',args.planets.resolve(),'--evidence',out,'--replay',out/'replay.csv',
                 '--frames','60','--fixed-step','0.25','--run']
        with (out/'console.txt').open('w') as log:
            subprocess.run(command,cwd=out,env=dict(os.environ,LD_PRELOAD=str(probe)),stdout=log,
                           stderr=subprocess.STDOUT,check=True,timeout=120)
        result=validate(out,case,original_intermediates=False)
        if args.original:
            with zipfile.ZipFile(args.original) as z:
                suffix='/'+case['id']+'-1/'
                def original(name):
                    key='out/'+original_directory+suffix+name
                    return z.read(key).decode().splitlines()
                if original('lua-events.csv')!=(out/'lua-events.csv').read_text().splitlines():
                    raise ValueError('Original Windows Lua event timing differs: '+case['id'])
                left=list(csv.DictReader(original('lua-controls.csv')))
                right=list(csv.DictReader((out/'lua-controls.csv').read_text().splitlines()))
                if len(left)!=61 or len(right)!=61:raise ValueError('Incomplete Lua controls')
                diffs=[dict(tick=x['tick'],control=k,windows=x[k],native=y[k]) for x,y in zip(left,right)
                       for k in ('elevator','aileron','main') if x[k]!=y[k]]
                matching={name:original(name)==(out/name).read_text().splitlines()
                          for name in ('lua-air.csv','cockpit-state.csv')}
                result.update(original_events_identical=True,original_controls_identical=not diffs,
                              original_air_identical=matching['lua-air.csv'],
                              original_state_identical=matching['cockpit-state.csv'],
                              first_control_difference=diffs[0] if diffs else None,control_differences=len(diffs))
        report[case['id']]=result
        print(case['id'],result,flush=True)
    (output/'lua-schedule-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.original and any(not all(v[k] for k in ('original_controls_identical','original_air_identical','original_state_identical'))
                             for v in report.values()):
        raise ValueError('Native Lua flight differs from the supplied Windows capture')

if __name__=='__main__':
    main()
