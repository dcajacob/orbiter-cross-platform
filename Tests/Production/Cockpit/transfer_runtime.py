#!/usr/bin/env python3
"""Check complete lunar-transfer scenes with baseline, repaired and instrumented builds."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'StockScenarios'),str(HERE.parent/'WaylandInput'),str(HERE.parent/'Client')]
from inventory import digest,require,ships
from run import inspect
from compositor import Compositor
from compare_client import image_ssim

MARKERS=('runtime error:','ERROR: AddressSanitizer','ERROR: LeakSanitizer',
         'LeakSanitizer has encountered','AddressSanitizer:DEADLYSIGNAL')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','fixed','sanitized','assets','data','planets','dependencies','output'):
        parser.add_argument('--'+name,type=lambda p:Path(p).resolve(),required=True)
    parser.add_argument('--sanitizer-library-path',type=lambda p:Path(p).resolve(),action='append',required=True)
    args=parser.parse_args()
    require(not args.output.exists(),'Transfer runtime output exists; replacement forbidden')
    builds={name:getattr(args,name) for name in ('baseline','fixed','sanitized')}
    files=[ROOT/name for name in json.loads((HERE.parent/'phase3-extraction.lock.json').read_text())['files']]
    files += [Path(__file__),HERE.parent/'StockScenarios/run.py',HERE.parent/'StockScenarios/inventory.py']
    for build in builds.values():
        files += [build/'orbiter-production',build/'CMakeCache.txt',*sorted(build.rglob('*.so'))]
    before={str(p):digest(p) for p in files}
    args.output.mkdir(parents=True)
    report=dict(status='running',phase6_complete=False,source_commit=subprocess.check_output(
        ['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),files_sha256=before,runs={},cases={},failures={})
    manifest=args.output/'verification.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        with Compositor(args.dependencies,args.output/'compositor') as display:
            for number in (1,2):
                scenario='Navigation/Lunar transfer/Lunar transfer '+str(number)+'.scn'
                source=(ROOT/'Scenarios'/scenario).read_bytes()
                require((args.assets/'Scenarios'/scenario).read_bytes()==source,'Staged scenario changed')
                case=dict(ships=ships(source.decode('cp1252')),dependency_problems=[])
                for label,build in builds.items():
                    name=label+'-'+str(number);out=args.output/name;out.mkdir()
                    (out/'flight.scn').write_bytes(source)
                    (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\nInstrumentUpdateInterval = 0.25\n')
                    (out/'replay.csv').write_text('tick,phase,action,value\n')
                    env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                             LD_LIBRARY_PATH=str(build))
                    for key in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(key,None)
                    if label=='sanitized':
                        env.update(LD_LIBRARY_PATH=':'.join(map(str,[build,*args.sanitizer_library_path])),
                            ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    argv=[str(build/'orbiter-production'),'--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'flight.scn'),
                          '--evidence',str(out),'--save',str(out/'saved.scn'),'--replay',str(out/'replay.csv'),
                          '--frames','60','--fixed-step','.25','--capture-time','12.5','--frame-delay-ms','120','--run']
                    for key in ('assets','data','planets'):argv+=['--'+key,str(getattr(args,key))]
                    argv+=['--modules',str(build/'NativeModules')]
                    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
                    try:
                        with (out/'console.log').open('w') as log:
                            completed=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                        result=inspect(out,case,completed.returncode)
                        # Record the real process result before subsequent validation.
                        report['runs'][name]=result;save()
                        require(result['status']=='passed',str(result['problems']))
                        text=(out/'console.log').read_text(errors='replace')
                        require(not any(marker in text for marker in MARKERS),'Sanitizer diagnostic in '+name)
                        require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Incomplete full frame')
                        result['frame_sha256']=digest(out/'scene.rgba')
                        result['status']='passed'
                        print(name,'passed: all ships, sixty presents, normal teardown',flush=True)
                    except Exception as error:
                        report['failures'][name]=str(error)
                        print(name,'failed:',error,flush=True)
                    save()
                baseline=args.output/('baseline-'+str(number));fixed=args.output/('fixed-'+str(number))
                if all(label+'-'+str(number) not in report['failures'] for label in ('baseline','fixed')):
                    try:
                        require((baseline/'flight-state.csv').read_bytes()==(fixed/'flight-state.csv').read_bytes(),
                                'Repaired all-vessel physical trajectory changed')
                        a,b=[(p/'scene.rgba').read_bytes() for p in (baseline,fixed)]
                        score=image_ssim(a,b,1280,720)
                        require(score>=.98,'Unmasked frame exceeds unchanged SSIM budget')
                        report['cases'][scenario]=dict(all_vessel_states_byte_identical=True,ssim=score,frames_byte_identical=a==b)
                    except Exception as error:report['failures'][scenario]=str(error)
                    save()
        require(before=={str(p):digest(p) for p in files},'Sources or retained binaries changed during verification')
        report.update(sources_and_binaries_unchanged=True,
                      status='passed' if not report['failures'] and len(report['runs'])==6 and len(report['cases'])==2 else 'failed')
        save()
    except BaseException as error:
        report.update(status='interrupted-or-failed',error=str(error));save();raise
    require(report['status']=='passed','Transfer runtime validation incomplete')
    print('Six complete-scene processes passed; repaired trajectories equal baseline',flush=True)


if __name__=='__main__':main()
