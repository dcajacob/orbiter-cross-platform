#!/usr/bin/env python3
"""Reject wrong station capabilities, required missing modules and generic clones."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from original import HERE,ROOT,digest,require,settings
sys.path.insert(0,str(HERE.parent/'WaylandInput'))
from compositor import Compositor


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies','executable','assets','data','modules','planets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in ('dependencies','executable','assets','data','modules','planets','output'):
        setattr(a,name,getattr(a,name).resolve())
    require(not a.output.exists(),'Station policy control output exists');a.output.mkdir(parents=True)
    config=settings();case=next(c for c in config['cases'] if c['id']=='stations_3')
    source=(ROOT/'Scenarios'/case['scenario']).read_bytes()
    paths=('Config/Vessels/Mir.cfg','Config/Vessels/Wheel.cfg')
    original={name:(a.assets/name).read_bytes() for name in paths}
    before={name:digest(a.assets/name) for name in paths}
    # Hard-link immutable data once; unlink each changed config before writing
    # so no source asset or running application's resource can be modified.
    assets=a.output/'assets';shutil.copytree(a.assets,assets,copy_function=os.link)
    def replace(name,data):
        target=assets/name
        if target.exists():target.unlink()
        target.write_bytes(data)
    def reset():
        for name,data in original.items():replace(name,data)
    report=dict(status='failed',phase6_complete=False,source_sha256=digest(Path(__file__)),
        executable_sha256=digest(a.executable),renderer_sha256=digest(a.modules/'Graphics/OGLClient.so'),
        original_config_sha256=before,cases=[])
    try:
        with Compositor(a.dependencies,a.output/'compositor') as compositor:
            environment=dict(compositor.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',
                             LP_NUM_THREADS='2',LD_LIBRARY_PATH=str(a.executable.parent))
            for name in ('changed_mass','changed_cross_sections','required_missing_module','unqualified_clone','wrong_declared_module'):
                reset();scenario=source
                expected='Unsupported stock vessel class or capabilities: Mir'
                if name=='changed_mass':
                    require(b'Mass = 124340' in original[paths[0]],'Original Mir mass source differs')
                    replace(paths[0],original[paths[0]].replace(b'Mass = 124340',b'Mass = 124341'))
                elif name=='changed_cross_sections':
                    replace(paths[1],original[paths[1]]+b'\nCrossSections = 20 20 21\n')
                    expected='Unsupported stock vessel class or capabilities: Wheel'
                elif name=='required_missing_module':
                    replace(paths[0],original[paths[0]]+b'\nModule = MissingStationModule\n')
                    expected='vessel/missingstationmodule.so'
                elif name=='unqualified_clone':
                    replace('Config/Vessels/UnqualifiedWheel.cfg',original[paths[1]])
                    require(b':Wheel' in source,'Original station fixture lacks Wheel class header')
                    scenario=source.replace(b':Wheel',b':UnqualifiedWheel')
                    expected='Unsupported stock vessel class or capabilities: UnqualifiedWheel'
                else:replace(paths[0],original[paths[0]]+b'\nModule = ShuttlePB\n')
                out=a.output/name;out.mkdir()
                (out/'flight.scn').write_bytes(scenario)
                (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text())
                args=[str(a.executable)]
                for key,value in [('assets',assets),('data',a.data),('modules',a.modules),('planets',a.planets)]:
                    args+=['--'+key,str(value)]
                args+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'flight.scn'),'--evidence',str(out),
                       '--save',str(out/'saved.scn'),'--frames','1','--fixed-step','.25','--run']
                (out/'invocation.json').write_text(json.dumps(args,indent=2)+'\n')
                with (out/'console.log').open('w') as log:
                    process=subprocess.run(args,cwd=out,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=60)
                console=(out/'console.log').read_text(errors='replace')
                require(process.returncode!=0 and 'Orbiter native production:' in console and
                        expected.casefold() in console.casefold(),'Station policy did not reject '+name+' for its actual cause')
                if name=='required_missing_module':
                    require('Unsupported stock vessel class or capabilities:' not in console,
                            'Required missing module reached generic capability classification')
                life=json.loads((out/'graphics-lifecycle.json').read_text())
                require(life==dict(rendered_frames=0,successful_presents=0,context_deleted=True),
                        'Rejected station configuration presented a scene or failed teardown')
                report['cases'].append(dict(name=name,returncode=process.returncode,expected=expected,
                    lifecycle=life,console_sha256=digest(out/'console.log'),scenario_sha256=digest(out/'flight.scn')))
        require(before=={name:digest(a.assets/name) for name in paths},'Original station configurations changed')
        require(report['executable_sha256']==digest(a.executable) and
                report['renderer_sha256']==digest(a.modules/'Graphics/OGLClient.so'),'Station policy runtime changed')
        report.update(status='passed',original_assets_unchanged=True,missing_module_fallback_rejected=True,
                      arbitrary_config_only_vessel_rejected=True,capability_mismatch_rejected=True)
    except BaseException as error:
        report['error']=str(error);raise
    finally:(a.output/'policy-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print('All five real startup controls rejected; no scene substitution or source asset changes')


if __name__=='__main__':main()
