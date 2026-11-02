#!/usr/bin/env python3
"""Capture real original window-routed stock controls before native input extraction."""
import argparse,json,math,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from reference import fixture,inspect,stage,git,mesa_files,image_ssim,require,rows
from frozen import metadata

def settings():
    value=json.loads((HERE/'cases.json').read_text());pins=metadata(HERE.parent/'Cockpit/Reference/provenance.json')
    require(value['application_source']==pins['application_source'] and value['budgets']==pins['budgets'] and value['image_ssim_minimum']==pins['image_ssim_minimum'],'Original control reference budgets or source changed')
    require(value['frames']==60 and value['fixed_step']==.25 and value['epoch']==51982.5,'Original control clock differs')
    require(value['expected_rcs']==dict(initial=1,after_tick_10=2,after_tick_30=1),'Original control outcomes changed')
    require({c['id'] for c in value['cases']}=={'controls_generic_orbit_surface','controls_dg_panel','controls_dg_vc','controls_dgs_panel','controls_dgs_vc'},'Original control case coverage differs')
    for case in value['cases']:
        require([(v['tick'],v['event']) for v in case['actions']]==[(10,'left_down'),(11,'left_up'),(30,'left_down'),(31,'left_up')],'Original discrete input timing differs')
        for action in case['actions']:
            require(action['coordinates'] in ('pixel','local') and len(action['point'])==3 and all(math.isfinite(float(x)) for x in action['point']),'Invalid declared original control point')
    return value

def validate(directory,case):
    state=rows(directory/'cockpit-state.csv');inputs=rows(directory/'control-inputs.csv');landmarks=rows(directory/'control-landmarks.csv')
    require(len(inputs)==8 and len(landmarks)==4,'Actual original mouse schedule is incomplete')
    for index,action in enumerate(case['actions']):
        for event,row in zip(('move',action['event']),inputs[2*index:2*index+2]):
            require(int(row['tick'])==action['tick'] and row['event']==event,'Actual recorded discrete input differs')
            require(0<=int(row['x'])<1280 and 0<=int(row['y'])<720,'Actual control click outside viewport')
            if action['coordinates']=='pixel':require((int(row['x']),int(row['y']))==tuple(action['point'][:2]),'Recorded 2D input coordinates differ')
        row=landmarks[index];require(int(row['tick'])==action['tick'] and row['coordinates']==action['coordinates'],'Original actual control landmark differs')
    for row in state:require(int(row['rcs_mode'])==(2 if 11<=int(row['tick'])<=30 else 1),'Window/panel/VC input did not change actual vessel RCS mode as declared')
    environment=json.loads((directory/'control-environment.json').read_text())
    require(environment['desktop_height']>0 and environment['viewport_width']==1280 and environment['viewport_height']==720,'Missing actual original display environment')
    return dict(actual_inputs=len(inputs),rcs_modes_verified=True,window_procedure_routing=True,environment=environment)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args();config=settings()
    require(sys.platform=='win32','Original cockpit control capture requires native Windows')
    require(not a.output.exists(),'Original control output exists; replacement is forbidden');a.output.mkdir(parents=True)
    runtime=json.loads((a.orbiter.parent/'control-reference-runtime.json').read_text());require(runtime['application_source']==config['application_source'],'Wrong original runtime')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    report=dict(status='pending',source=git('rev-parse','HEAD').decode().strip(),configuration=a.configuration,application_source=config['application_source'],runtime=runtime,cases={},failures={})
    for case in config['cases']:
        try:
            directories=[];observed=[]
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
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):(directory/name).write_text('Additional original window-routed control observation\n')
                    mesa_files(a.mesa.resolve(),directory)
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,{**case,'frames':60,'fixed_step':.25,'epoch':config['epoch']},configure)
                observation=inspect(directory,case,config);observation['controls']=validate(directory,case);observed.append(observation);directories.append(directory)
            for name in ('cockpit-state.csv','control-inputs.csv','control-landmarks.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original control repeat differs: '+name)
            similarity={str(f):image_ssim((directories[0]/f'instrument-{f}.rgba').read_bytes(),(directories[1]/f'instrument-{f}.rgba').read_bytes(),1280,720) for f in (20,50)}
            require(min(similarity.values())>=config['image_ssim_minimum'],'Original control image repeat exceeds unchanged budget')
            # Include direct MFD texture captures in repeat validation too.
            for frame in (20,50):
                for index in (0,1):
                    stem=f'mfd-{index}-{frame}'
                    sizes=[json.loads((directory/(stem+'.json')).read_text()) for directory in directories]
                    require((sizes[0]['width'],sizes[0]['height'])==(sizes[1]['width'],sizes[1]['height']),'Original control MFD dimensions differ on repeat')
                    similarity_mfd=image_ssim((directories[0]/(stem+'.rgba')).read_bytes(),(directories[1]/(stem+'.rgba')).read_bytes(),sizes[0]['width'],sizes[0]['height'])
                    require(similarity_mfd>=config['image_ssim_minimum'],'Original control MFD repeat exceeds unchanged budget')
            report['cases'][case['id']]=dict(runs=observed,repeat_ssim=similarity,identical_state_text_geometry_and_inputs=True)
        except Exception as error:
            detail=str(error);failure=directory/'cockpit-failure.txt'
            if failure.is_file():detail+=': '+failure.read_text().strip()
            report['failures'][case['id']]=detail
    report['status']='failed' if report['failures'] else 'passed';(a.output/'control-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],cases=list(report['cases']),failures=report['failures']),indent=2))
    require(report['status']=='passed','Original control reference failed; native cockpit input extraction is blocked')
if __name__=='__main__':main()
