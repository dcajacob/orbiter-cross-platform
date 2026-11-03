#!/usr/bin/env python3
"""Reject missing modules, foreign factories, generic fallbacks and class clones."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production/WaylandInput'))
from compositor import Compositor


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies','executable','assets','data','modules','planets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in vars(a):setattr(a,name,getattr(a,name).resolve())
    require(not a.output.exists(),'Shuttle-A policy-control output exists')
    a.output.mkdir(parents=True)
    suite=json.loads((ROOT/'Tests/Production/ShuttleA/cases.json').read_text())
    case=next(c for c in suite['cases'] if c['scenario']=='Shuttle-A/Shuttle-A Docked at ISS.scn')
    source=(ROOT/'Scenarios'/case['scenario']).read_bytes()
    require(hashlib.sha256(source.replace(b'\r\n',b'\n')).hexdigest()==case['sha256_lf'],
            'Original complete Shuttle-A scenario differs')
    names=('Config/Vessels/ShuttleA.cfg','Config/Vessels/ShuttleA_pl.cfg')
    original={name:(a.assets/name).read_bytes() for name in names}
    before={name:digest(a.assets/name) for name in names}
    assets=a.output/'assets'
    shutil.copytree(a.assets,assets,copy_function=os.link)

    def replace(name,data):
        target=assets/name
        if target.exists():target.unlink()
        target.write_bytes(data)

    for name,kind in (('Phase6ShuttleClone',0),('Phase6PayloadClone',1)):
        replace('Config/Vessels/'+name+'.cfg',original[names[kind]])
    report=dict(status='failed',phase6_complete=False,source_sha256=digest(Path(__file__)),
        executable_sha256=digest(a.executable),renderer_sha256=digest(a.modules/'Graphics/OGLClient.so'),
        original_config_sha256=before,cases=[])
    variants=[('missing_shuttle_module',0,b'MissingShuttleModule'),
              ('missing_payload_module',1,b'MissingPayloadModule'),
              ('foreign_shuttle_factory',0,b'DeltaGlider'),
              ('foreign_payload_factory',1,b'ShuttlePB'),
              ('generic_shuttle_fallback',0,None),('generic_payload_fallback',1,None),
              ('unqualified_shuttle_clone',0,b'Phase6ShuttleClone'),
              ('unqualified_payload_clone',1,b'Phase6PayloadClone')]
    try:
        with Compositor(a.dependencies,a.output/'compositor') as compositor:
            env=dict(compositor.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',
                     LP_NUM_THREADS='2',LD_LIBRARY_PATH=str(a.executable.parent))
            for name in ('LD_PRELOAD','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS'):env.pop(name,None)
            for key,kind,module in variants:
                for name,data in original.items():replace(name,data)
                scenario=source
                class_name=b'ShuttleA' if kind==0 else b'ShuttleA_pl'
                lines=[line for line in original[names[kind]].splitlines(keepends=True)
                       if line.split(b'=',1)[0].strip()==b'Module']
                require(len(lines)==1,'Original module declaration differs')
                old=lines[0]
                expected=b'Unsupported stock vessel class or capabilities: '+class_name
                if key.startswith('unqualified_'):
                    require(b':'+class_name+b'\n' in source,'Original vessel declaration differs')
                    scenario=source.replace(b':'+class_name+b'\n',b':'+module+b'\n')
                    expected=b'Unsupported stock vessel class or capabilities: '+module
                else:
                    replacement=b'' if module is None else b'Module = '+module+b'\n'
                    replace(names[kind],original[names[kind]].replace(old,replacement,1))
                    if key.startswith('missing_'):expected=module
                out=a.output/key;out.mkdir()
                (out/'flight.scn').write_bytes(scenario)
                argv=[str(a.executable)]
                for name in ('data','modules','planets'):argv+=['--'+name,str(getattr(a,name))]
                argv+=['--assets',str(assets),'--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),
                       '--scenario',str(out/'flight.scn'),'--evidence',str(out),
                       '--save',str(out/'saved.scn'),'--frames','1','--run']
                (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
                with (out/'console.log').open('w') as log:
                    result=subprocess.run(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                text=(out/'console.log').read_bytes()
                require(result.returncode==1 and expected.lower() in text.lower(),
                        'Shuttle-A policy did not reject the intended condition: '+key)
                life=json.loads((out/'graphics-lifecycle.json').read_text())
                require(life==dict(rendered_frames=0,successful_presents=0,context_deleted=True),
                        'Shuttle-A policy failure presented a scene or failed context cleanup')
                report['cases'].append(dict(id=key,status='rejected',returncode=result.returncode,
                    lifecycle=life,console_sha256=digest(out/'console.log')))
        require(before=={name:digest(a.assets/name) for name in names},'Protected source configs changed')
        require(digest(a.executable)==report['executable_sha256'] and
                digest(a.modules/'Graphics/OGLClient.so')==report['renderer_sha256'],
                'Shuttle-A policy runtime changed during controls')
        report.update(status='passed',original_configs_unchanged=True)
    finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Eight Shuttle-A module/capability policy failures rejected before presentation')


if __name__=='__main__':main()
