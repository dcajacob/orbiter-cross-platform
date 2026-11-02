#!/usr/bin/env python3
"""Compare current Windows window-routed controls with frozen original captures."""
import argparse,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from capture import settings,validate
from reference import fixture,inspect,stage,git,mesa_files,require,rows,image_ssim,digest
from compare import compare
from regression import mfd_images
from frozen_controls import metadata

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','frozen','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    a=p.parse_args();config=settings();pins=metadata()
    require(sys.platform=='win32','Current window control regression requires native Windows')
    require(json.loads((a.frozen/'provenance.json').read_text())==pins,'Staged original control reference differs')
    for name,checksum in pins['reference_files_sha256'][a.configuration].items():
        require(digest(a.frozen/a.configuration/name)==checksum,'Frozen original control file differs: '+name)
    current=git('rev-parse','HEAD').decode().strip()
    runtime=json.loads((a.orbiter.parent/'test-runtime.json').read_text())
    require(runtime['source_commit']==current,'Current application/SDK must use this exact source')
    require(not a.output.exists(),'Current control output exists; replacement is forbidden');a.output.mkdir(parents=True)
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    report=dict(status='pending',source=current,reference_run=pins['run_id'],configuration=a.configuration,cases={},failures={})
    for case in config['cases']:
        try:
            directories=[];observations=[]
            for repeat in (1,2):
                directory=a.output.resolve()/(case['id']+'-'+str(repeat))
                def configure(directory):
                    cfg=directory/'Orbiter.cfg';cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    text=fixture(case)
                    if case['cockpit']==1:
                        start=text.index('PB:ShuttlePB\n');end=text.index('\nEND\n',start);text=text[:end]+'\n  RCSMODE 1'+text[end:]
                    (directory/'Scenarios/Behavior.scn').write_text(text)
                    (directory/'cockpit-case.txt').write_text(f"{case['target']} 60 {case['cockpit']} 1 2 1\n")
                    schedule=['4']+[f"{v['tick']} {v['event']} {v['coordinates']} "+' '.join(format(x,'.17g') for x in v['point']) for v in case['actions']]
                    (directory/'control-schedule.txt').write_text('\n'.join(schedule)+'\n')
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):(directory/name).write_text('Current production window control comparison\n')
                    require((directory/'Modules/Plugin/ProductionCockpitDriver.dll').is_file(),'Same-SDK control driver missing')
                    mesa_files(a.mesa.resolve(),directory)
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,{**case,'frames':60,'fixed_step':.25,'epoch':config['epoch']},configure)
                observation=inspect(directory,case,config);observation['controls']=validate(directory,case)
                observations.append(observation);directories.append(directory)
            for name in ('cockpit-state.csv','control-inputs.csv','control-landmarks.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Current control repeat differs: '+case['id']+'/'+name)
            for frame in (20,50):
                for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                    width,height=1280,720
                    if stem.startswith('mfd-'):
                        sizes=[json.loads((d/(stem+'.json')).read_text()) for d in directories]
                        require((sizes[0]['width'],sizes[0]['height'])==(sizes[1]['width'],sizes[1]['height']),'Current MFD repeat dimensions differ')
                        width,height=sizes[0]['width'],sizes[0]['height']
                    similarity=image_ssim((directories[0]/(stem+'.rgba')).read_bytes(),(directories[1]/(stem+'.rgba')).read_bytes(),width,height)
                    require(similarity>=config['image_ssim_minimum'],'Current control image repeat exceeds unchanged budget')
            one={**config,'cases':[case]};original=a.frozen/a.configuration/(case['id']+'-1')
            for name in ('control-inputs.csv','control-landmarks.csv'):
                require((original/name).read_bytes()==(directories[0]/name).read_bytes(),'Current actual control input/landmark differs: '+name)
            require([r['rcs_mode'] for r in rows(original/'cockpit-state.csv')]==[r['rcs_mode'] for r in rows(directories[0]/'cockpit-state.csv')],'Current actual vessel RCS mode differs')
            report['cases'][case['id']]=dict(runs=observations,comparison=compare(a.frozen/a.configuration,a.output,one)[case['id']],
                mfd_images=mfd_images(a.frozen/a.configuration,a.output,one)[case['id']],identical_repeats=True)
        except Exception as error:report['failures'][case['id']]=str(error)
    report['status']='failed' if report['failures'] else 'passed'
    (a.output/'control-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],cases=list(report['cases']),failures=report['failures']),indent=2))
    require(report['status']=='passed','Current production controls differ from frozen Windows')
if __name__=='__main__':main()
