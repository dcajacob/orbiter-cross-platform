#!/usr/bin/env python3
"""Run current production Windows cockpits against immutable pre-extraction captures."""
import argparse
import json
import os
from pathlib import Path
import sys
from reference import fixture,inspect,stage,git,mesa_files,image_ssim,require
from compare import compare
from frozen import metadata

HERE=Path(__file__).resolve().parent

def mfd_images(reference,candidate,settings):
    results={}
    for case in settings['cases']:
        name=case['id'];left=reference/(name+'-1');right=candidate/(name+'-1');values={}
        for frame in (20,50):
            for index in (0,1):
                stem=f'mfd-{index}-{frame}'
                a=json.loads((left/(stem+'.json')).read_text());b=json.loads((right/(stem+'.json')).read_text())
                require((a['width'],a['height'])==(b['width'],b['height']),'Actual MFD texture dimensions differ: '+name)
                similarity=image_ssim((left/(stem+'.rgba')).read_bytes(),(right/(stem+'.rgba')).read_bytes(),a['width'],a['height'])
                require(similarity>=settings['image_ssim_minimum'],'Actual MFD texture image exceeds its unchanged budget: '+name)
                values[stem]=similarity
        results[name]=values
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','frozen','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args()
    require(sys.platform=='win32','Current Windows cockpit regression requires native Windows')
    pins=metadata(HERE/'Reference/provenance.json');settings=json.loads((HERE/'cases.json').read_text())
    require(json.loads((a.frozen/'provenance.json').read_text())==pins,'Staged cockpit reference identity differs')
    current=git('rev-parse','HEAD').decode().strip()
    require(json.loads((a.orbiter.parent/'test-runtime.json').read_text())['source_commit']==current,'Current application/SDK must be built from this exact source')
    require(not a.output.exists(),'Candidate output exists; replacement is forbidden');a.output.mkdir(parents=True)
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    report=dict(status='pending',source=current,reference_run=pins['run_id'],configuration=a.configuration,cases={},failures={})
    for case in settings['cases']:
        try:
            directories=[];observations=[]
            for repeat in (1,2):
                directory=a.output.resolve()/(case['id']+'-'+str(repeat))
                def configure(directory):
                    config=directory/'Orbiter.cfg'
                    config.write_text(config.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (directory/'Scenarios/Behavior.scn').write_text(fixture(case))
                    (directory/'cockpit-case.txt').write_text(f"{case['target']} 60 {case['cockpit']} {case['left']} {case['right']} {case['hud']}\n")
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):(directory/name).write_text('Current production cockpit parity observation\n')
                    require((directory/'Modules/Plugin/ProductionCockpitDriver.dll').is_file(),'Same-build cockpit observation driver missing')
                    mesa_files(a.mesa.resolve(),directory)
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,{**case,'frames':60,'fixed_step':settings['fixed_step'],'epoch':settings['epoch']},configure)
                observations.append(inspect(directory,case,settings));directories.append(directory)
            for name in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Current production cockpit repeat differs: '+name)
            similarity={str(f):image_ssim((directories[0]/f'instrument-{f}.rgba').read_bytes(),(directories[1]/f'instrument-{f}.rgba').read_bytes(),1280,720) for f in (20,50)}
            require(min(similarity.values())>=settings['image_ssim_minimum'],'Current cockpit image repeat exceeds its unchanged budget')
            report['cases'][case['id']]=dict(runs=observations,repeat_ssim=similarity,identical_state_and_display_text=True)
        except Exception as error:report['failures'][case['id']]=str(error)
    report['status']='failed' if report['failures'] else 'passed'
    if not report['failures']:
        try:
            report['frozen_comparison']=compare(a.frozen/a.configuration,a.output,settings)
            report['mfd_texture_comparison']=mfd_images(a.frozen/a.configuration,a.output,settings)
        except Exception as error:report['status']='failed';report['failures']['frozen_comparison']=str(error)
    (a.output/'cockpit-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],source=current,cases=list(report['cases']),failures=report['failures']),indent=2))
    require(report['status']=='passed','Current production cockpit failed its immutable Windows reference')
if __name__=='__main__':main()
