#!/usr/bin/env python3
"""Reject invalid configured framebuffer dimensions before creating a scene."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
from run import digest, require
sys.path.insert(0,str(HERE.parent/'WaylandInput'))
from compositor import Compositor


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies','executable','assets','data','modules','planets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    report=dict(status='failed',source_sha256=digest(Path(__file__)),cases=[],
                executable_sha256=digest(a.executable),renderer_sha256=digest(a.modules/'Graphics/OGLClient.so'))
    try:
        with Compositor(a.dependencies,out/'compositor') as compositor:
            env=dict(compositor.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',
                     LP_NUM_THREADS='2',LD_LIBRARY_PATH=str(a.executable.resolve().parent))
            for width,height in ((0,1080),(1920,20000)):
                case=out/(str(width)+'x'+str(height));case.mkdir()
                config=case/'Orbiter.cfg'
                config.write_text((HERE/'medium.cfg').read_text().replace('WindowWidth = 1920',f'WindowWidth = {width}')
                                  .replace('WindowHeight = 1080',f'WindowHeight = {height}'))
                argv=[str(a.executable.resolve())]
                for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
                argv+=['--config',str(config),'--scenario',str(a.assets.resolve()/'Scenarios/Antelope Valley scenery/DG at Edwards AFB.scn'),
                       '--evidence',str(case),'--frames','1','--run']
                (case/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
                with (case/'console.log').open('w') as log:
                    result=subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=30)
                error=(case/'console.log').read_text()
                require(result.returncode!=0 and 'Native window dimensions are outside the supported range' in error,
                        'Invalid dimensions were not rejected explicitly')
                require(not (case/'native-window.json').exists() and not (case/'renderer-info.json').exists(),
                        'Invalid dimensions reached window/scene creation')
                report['cases'].append(dict(width=width,height=height,returncode=result.returncode,
                    config_sha256=digest(config),log_sha256=digest(case/'console.log'),rejected_before_window=True))
        report['status']='passed'
    except BaseException as error:
        report['error']=str(error);raise
    finally:
        (out/'window-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Zero and oversized framebuffer requests rejected before window/scene creation')


if __name__=='__main__':main()
