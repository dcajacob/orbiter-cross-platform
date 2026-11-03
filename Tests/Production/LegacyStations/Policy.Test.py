#!/usr/bin/env python3
"""Reject wrong factories, class clones and altered legacy capabilities or ports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'WaylandInput'),str(HERE.parent/'StockScenarios')]
from compositor import Compositor
from inventory import digest,require
from intentional_exit import build_identity


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','build-record','assets','data','planets','dependencies','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--runtime-source-commit',required=True)
    p.add_argument('--sanitize',action='store_true')
    p.add_argument('--library-directory',type=lambda v:Path(v).resolve(),action='append',default=[])
    a=p.parse_args();require(not a.output.exists(),'Legacy policy controls require fresh output')
    identity=build_identity(a.build/'orbiter-production',a.build/'NativeModules',a.build_record,a.runtime_source_commit)
    require(identity['sanitizer_linked']==a.sanitize,'Legacy policy-control instrumentation misidentified')
    require(not a.sanitize or len(a.library_directory)==3,'Instrumented legacy controls require three qualified private libraries')
    a.output.mkdir(parents=True);assets=a.output/'assets'
    shutil.copytree(a.assets,assets,copy_function=os.link)
    paths={'ISS':'Config/Vessels/ISS.cfg','Module1':'Config/Vessels/Module1.cfg'}
    original={name:(a.assets/path).read_bytes() for name,path in paths.items()}
    configs_before={name:digest(a.assets/path) for name,path in paths.items()}
    runtime_files=[a.build/'orbiter-production',a.build/'CMakeCache.txt',*sorted(a.build.rglob('*.so'))]
    runtime_before={str(p):digest(p) for p in runtime_files}
    source=(ROOT/'Scenarios/Navigation/Space Physics/DG dumbbell.scn').read_bytes()
    report=dict(status='failed',phase6_complete=False,runtime_identity=identity,
        runtime_source_commit=a.runtime_source_commit,source_sha256=digest(Path(__file__)),
        scenario_sha256=hashlib.sha256(source).hexdigest(),original_config_sha256=configs_before,cases=[])
    def replace(name,data):
        path=assets/name
        if path.exists():path.unlink()
        path.write_bytes(data)
    def item(data,name,value):
        pattern=rb'(?im)^'+re.escape(name.encode())+rb'\s*=.*$'
        if re.search(pattern,data):return re.sub(pattern,name.encode()+b' = '+value,data,count=1)
        return data+b'\n'+name.encode()+b' = '+value+b'\n'
    variants=('missing_module','foreign_factory','unqualified_clone','changed_mass','changed_focus',
              'changed_transponder','changed_port_position','changed_port_direction')
    try:
        with Compositor(a.dependencies,a.output/'compositor') as display:
            env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                LD_LIBRARY_PATH=':'.join(map(str,[a.build,*a.library_directory])))
            for key in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(key,None)
            if a.sanitize:env.update(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            for kind in ('ISS','Module1'):
                for variant in variants:
                    for name,path in paths.items():replace(path,original[name])
                    data=original[kind];scenario=source;expected=b'Unsupported stock vessel class or capabilities: '+kind.encode()
                    if variant=='missing_module':
                        data=item(data,'Module',b'MissingLegacyModule');expected=b'MissingLegacyModule'
                    elif variant=='foreign_factory':data=item(data,'Module',b'ShuttlePB')
                    elif variant=='unqualified_clone':
                        clone='Phase6Legacy'+kind
                        replace('Config/Vessels/'+clone+'.cfg',data)
                        pattern=rb'(?m)^([^:\r\n]+:)'+re.escape(kind.encode())+rb'([ \t]*\r?$)'
                        scenario,count=re.subn(pattern,rb'\g<1>'+clone.encode()+rb'\g<2>',source,count=1)
                        require(count==1,'Original complete legacy scenario declaration missing')
                        expected=b'Unsupported stock vessel class or capabilities: '+clone.encode()
                    elif variant=='changed_mass':data=item(data,'Mass',b'450001' if kind=='ISS' else b'8001')
                    elif variant=='changed_focus':data=item(data,'EnableFocus',b'TRUE' if kind=='ISS' else b'FALSE')
                    elif variant=='changed_transponder':
                        data=item(data,'EnableXPDR',b'FALSE' if kind=='ISS' else b'TRUE')
                        if kind=='Module1':data=item(data,'XPDR',b'466')
                    elif variant=='changed_port_position':
                        if kind=='ISS':
                            require(b'13.67 5.56 0' in data,'Original ISS port position missing')
                            data=data.replace(b'13.67 5.56 0',b'13.68 5.56 0',1)
                        else:
                            require(b'0 0  5' in data,'Original Module1 port position missing')
                            data=data.replace(b'0 0  5',b'0 0  5.25',1)
                    else:
                        old=b'13.67 5.56 0   1 0 0' if kind=='ISS' else b'0 0  5   0 0  1'
                        new=b'13.67 5.56 0   0 0 1' if kind=='ISS' else b'0 0  5   1 0  0'
                        require(old in data,'Original legacy port direction missing');data=data.replace(old,new,1)
                    if variant!='unqualified_clone':replace(paths[kind],data)
                    out=a.output/(kind+'-'+variant);out.mkdir();(out/'flight.scn').write_bytes(scenario)
                    argv=[str(a.build/'orbiter-production'),'--assets',str(assets),'--data',str(a.data),
                        '--planets',str(a.planets),'--modules',str(a.build/'NativeModules'),
                        '--scenario',str(out/'flight.scn'),'--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),
                        '--evidence',str(out),'--save',str(out/'saved.scn'),'--frames','1','--run']
                    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
                    with (out/'console.log').open('w') as log:
                        process=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                    text=(out/'console.log').read_bytes()
                    require(process.returncode==1 and expected.lower() in text.lower(),'Legacy policy did not reject intended condition: '+out.name)
                    require(not any(marker in text for marker in (b'runtime error:',b'ERROR: AddressSanitizer',b'ERROR: LeakSanitizer',
                        b'AddressSanitizer:DEADLYSIGNAL',b'LeakSanitizer has encountered')),'Legacy policy rejection has sanitizer diagnostic')
                    life=json.loads((out/'graphics-lifecycle.json').read_text())
                    require(life==dict(rendered_frames=0,successful_presents=0,context_deleted=True),'Legacy policy rejection presented or leaked its context')
                    report['cases'].append(dict(id=out.name,status='rejected',returncode=process.returncode,lifecycle=life,
                        console_sha256=digest(out/'console.log'),scenario_sha256=digest(out/'flight.scn')))
                    print(out.name,'rejected cleanly',flush=True)
        require(configs_before=={name:digest(a.assets/path) for name,path in paths.items()},'Original legacy configurations changed')
        require(runtime_before=={str(p):digest(p) for p in runtime_files},'Retained legacy runtime changed during policy controls')
        report.update(status='passed',original_configs_and_runtime_unchanged=True,rejected_controls=16)
    finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
