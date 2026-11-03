#!/usr/bin/env python3
"""Capture complete unchanged station scenarios with the real native host."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from original import HERE,ROOT,digest,inspect_trace,require,rows,settings,source_digest,png


def build_probe(build,out):
    compiler=next(line.split('=',1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                  if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    probe=out/'stock-vessels-probe.so'
    subprocess.run([compiler,'-std=c++17','-fPIC','-shared','-Wl,--no-undefined',
        '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(HERE/'NativeProbe.cpp'),
        '-L'+str(build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)],check=True)
    return probe


def inspect(out,case,config):
    state,stations,groups=inspect_trace(out,case,config)
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),
            'Native stock graphics presentation/teardown incomplete')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Native station comparison requires the declared software renderer and viewport')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Native station graphics error')
    log=(out/'console.log').read_text(errors='replace')
    for marker in ('Lua error:','LuaCall (','runtime error:','ERROR: AddressSanitizer','ERROR: LeakSanitizer',
                   'Orbiter native production:'):
        require(marker not in log,'Native station runtime failure: '+marker)
    require(source_digest(out/'flight.scn')==case['sha256_lf'],'Native station scenario bytes differ')
    scene=rows(out/'scene.csv');declared={r['object'] for r in groups[0]}
    require(declared<={r['object'] for r in scene if r['type']=='vessel'},'Native complete stock mesh inventory missing')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4,'Incomplete native station framebuffer')
    math=json.loads((out/'numerics.json').read_text())['math']
    files=('stock-vessel-state.csv','stock-vessel-docks.csv','flight-state.csv',
           'scene.csv','scene.rgba','camera.csv','renderer-info.json','graphics-lifecycle.json',
           'renderer-modules.txt','invocation.json','numerics.json','console.log','flight.scn','Orbiter.cfg')
    return dict(status='passed',declared_vessels=len(declared),finalized_ticks=len(groups),actual_math=math,
        renderer=renderer,lifecycle=life,station_initial_capabilities=[r for r in stations if r['tick']=='0'],
        files_sha256={name:digest(out/name) for name in files})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    a=p.parse_args()
    for name in ('executable','assets','data','modules','planets','output'):setattr(a,name,getattr(a,name).resolve())
    config=settings();require(not a.output.exists(),'Native station output exists; replacement is forbidden')
    a.output.mkdir(parents=True)
    binaries=dict(executable=digest(a.executable),engine=digest(a.executable.parent/'liborbiter_production_vessels.so'),
                  renderer=digest(a.modules/'Graphics/OGLClient.so'))
    probe=build_probe(a.executable.parent,a.output)
    sources=[Path(__file__),HERE/'NativeProbe.cpp',HERE/'Observation.h',HERE/'cases.json',HERE/'original.py',
             HERE.parent/'StockScenarios/inventory.py',HERE.parent/'NativeScene/Orbiter.cfg',
             ROOT/'Src/Orbiter/Production/NativeApplication.cpp']
    runtime_files=[a.executable,*a.executable.parent.rglob('*.so')]
    report=dict(status='running',phase6_complete=False,host='native-linux',configuration=a.configuration,
        math_profile=a.math_profile,original_application_source=config['application_source'],
        binary_sha256=binaries,producer_sha256=digest(probe),settings_sha256_lf=source_digest(HERE/'cases.json'),
        runtime_files_sha256={str(path.relative_to(ROOT)):digest(path) for path in runtime_files},
        source_sha256={str(path.relative_to(ROOT)):digest(path) for path in sources},cases={},failures={})
    manifest=a.output/'stock-vessels.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for case in config['cases']:
        try:
            runs=[];observed=[]
            for repeat in (1,2):
                out=a.output/(case['id']+'-'+str(repeat));out.mkdir();runs.append(out)
                source=(ROOT/'Scenarios'/case['scenario']).read_bytes()
                require((a.assets/'Scenarios'/case['scenario']).read_bytes()==source,'Staged stock scenario bytes differ')
                (out/'flight.scn').write_bytes(source)
                (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                    '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                args=[str(a.executable)]
                for name in ('assets','data','modules','planets'):args+=['--'+name,str(getattr(a,name))]
                args+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'flight.scn'),'--evidence',str(out),
                       '--save',str(out/'saved.scn'),'--frames','60','--fixed-step','.25','--capture-time','12.5','--run']
                (out/'invocation.json').write_text(json.dumps(args,indent=2)+'\n')
                environment=dict(os.environ,LD_LIBRARY_PATH=str(a.executable.parent),LD_PRELOAD=str(probe))
                with (out/'console.log').open('w') as log:
                    subprocess.run(args,cwd=out,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
                recorded=inspect(out,case,config);observed.append(recorded)
                require(recorded['actual_math'] in ('amd-6121d02-fma3','amd-6121d02-sse2'),
                        'Unknown native station numerical implementation')
                if a.math_profile=='sse2':require(recorded['actual_math'].endswith('sse2'),'Native station SSE2 profile differs')
                else:require(recorded['actual_math'].endswith('fma3'),'Native station automatic profile differs')
                png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
            for name in ('stock-vessel-state.csv','stock-vessel-docks.csv'):
                require((runs[0]/name).read_bytes()==(runs[1]/name).read_bytes(),'Native station repeat differs: '+name)
            report['cases'][case['id']]=dict(scenario=case['scenario'],runs=observed)
            print(case['id'],'passed',flush=True)
        except Exception as error:
            report['failures'][case['id']]=str(error);print(case['id'],str(error),flush=True)
        save()
    require(binaries==dict(executable=digest(a.executable),engine=digest(a.executable.parent/'liborbiter_production_vessels.so'),
                           renderer=digest(a.modules/'Graphics/OGLClient.so')) and
            all(digest(ROOT/name)==checksum for name,checksum in report['source_sha256'].items()),
            'Native station binaries or sources changed while captures were live')
    require(all(digest(ROOT/name)==checksum for name,checksum in report['runtime_files_sha256'].items()),
            'Native station module/library changed during capture')
    report['status']='passed' if not report['failures'] and len(report['cases'])==7 else 'failed';save()
    require(report['status']=='passed','Native station capture failed; qualification is incomplete')


if __name__=='__main__':main()
