#!/usr/bin/env python3
"""Observe original Windows instruments; never overwrite an accepted reference."""
import argparse,hashlib,json,math,os,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'Tests/Production'),str(ROOT/'Tests/Production/Client')]
from behavior_suite import scenario,rows,git
from stage import run as stage
from mesa_runtime import require,digest
from run_client import mesa_files,png
from compare_client import image_ssim

def fixture(case):
    text=scenario(case['fixture']).replace('MODE Extern','MODE Cockpit')
    if case.get('class')=='DeltaGlider':
        text=text.replace('DG:DG-S','DG:DeltaGlider').replace('PRPLEVEL 0:0.8 1:1 2:1','PRPLEVEL 0:0.8 1:1').replace('  TANKCONFIG 1\n','')
    panel={1:'',2:'BEGIN_PANEL\nEND_PANEL\n',3:'BEGIN_VC\nEND_VC\n'}[case['cockpit']]
    instruments=''
    if case['id']=='generic_align_sync':
        instruments='BEGIN_MFD Left\n  TYPE OAlign\n  REF Earth\n  TARGET ISS\nEND_MFD\nBEGIN_MFD Right\n  TYPE OSync\n  TARGET ISS\nEND_MFD\n'
    return text.replace('BEGIN_SHIPS','BEGIN_HUD\n  TYPE '+{1:'Orbit',2:'Surface',3:'Docking'}[case['hud']]+'\nEND_HUD\n'+panel+instruments+'BEGIN_SHIPS')

def inspect(directory,case,settings):
    require(not (directory/'cockpit-failure.txt').exists(),'Original instrument/control driver failed')
    require((directory/'cockpit-complete.txt').read_text().strip()=='60','Original session did not complete normally')
    state=rows(directory/'cockpit-state.csv');text=rows(directory/'instrument-text.csv')
    require(len(state)==61 and [int(v['tick']) for v in state]==list(range(61)),'Incomplete original finalized instrument states')
    for row in state:
        require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','class')),'Nonfinite original instrument state')
        require(float(row['seconds'])==int(row['tick'])*settings['fixed_step'],'Wrong original fixed-step clock')
    require(text and len(text)>100,'Actual original instrument drawing was not observed')
    require(any(float(r['seconds'])>=12.5 for r in text),'Instrument updates stopped before the capture')
    require(any(any(48<=c<=57 for c in bytes.fromhex(r['text_hex'])) for r in text),'Original instruments drew no numerical values')
    life=json.loads((directory/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']==60,'Actual client lifecycle incomplete')
    renderer=json.loads((directory/'renderer-info.json').read_text());require('llvmpipe' in renderer['renderer'].lower(),'Original Windows software OpenGL was not loaded')
    errors=directory/'graphics-errors.txt';require(not errors.exists() or not errors.read_text().strip(),'Original client reported OpenGL errors')
    registrations=[r for r in rows(directory/'visual-events.csv') if r['event']=='register' and r['object']==case['target']]
    require(registrations and int(registrations[0]['frame'])==0,'Required real cockpit visual was not registered on the first frame')
    if case['cockpit']==3:
        require(any(r['object']==case['target'] and int(r['mesh_draw_calls'])>0 for r in rows(directory/'object-draws.csv')),'Actual stock virtual cockpit mesh was not drawn')
    bindings=json.loads((directory/'mesa-bindings.json').read_text());modules=[];names=set()
    expected={name.casefold():entry for name,entry in bindings['runtime']['files'].items()}
    effective={name.casefold():entry for name,entry in bindings['bindings'].items()};system=Path(os.environ['SystemRoot']).resolve()
    for line in (directory/'renderer-modules.txt').read_text().splitlines():
        path=Path(line).resolve();names.add(path.name.casefold())
        if path.suffix.lower()!='.dll':continue
        require(directory.resolve() in path.parents or system in path.parents,'Unrecorded external DLL: '+str(path))
        record=dict(path=str(path),sha256=digest(path));modules.append(record);entry=expected.get(path.name.casefold())
        if entry:require(path.parent==directory.resolve() and record['sha256']==effective.get(path.name.casefold(),{}).get('effective_sha256',entry['sha256']),'Actual loaded Mesa DLL differs: '+path.name)
    vessel_module='deltaglider.dll' if case['target']=='DG' else 'shuttlepb.dll'
    require({'opengl32.dll','libgallium_wgl.dll','oglclient.dll',vessel_module}<=names,'Required actual engine/client/vessel/driver DLL missing')
    assets={}
    for line in (directory/'loaded-assets.txt').read_text().splitlines():
        path=Path(line);path=path if path.is_absolute() else directory/path
        require(path.is_file(),'Recorded actual stock asset missing');assets[line]=digest(path)
    hashes={}
    for frame in (20,50):
        image=directory/f'instrument-{frame}.rgba';pixels=image.read_bytes();require(len(pixels)==1280*720*4,'Missing original cockpit capture')
        png(directory/f'instrument-{frame}.png',pixels,1280,720);hashes[str(frame)]=digest(image)
        for index in (0,1):
            stem=f'mfd-{index}-{frame}';mfd=json.loads((directory/(stem+'.json')).read_text())
            require(mfd['colored_pixels']>20 and mfd['nonwhite_pixels']>mfd['width']*mfd['height']//4,'Actual MFD display texture is blank')
            png(directory/(stem+'.png'),(directory/(stem+'.rgba')).read_bytes(),mfd['width'],mfd['height'])
    geometry=rows(directory/'instrument-geometry.csv');blits=rows(directory/'instrument-self-blits.csv')
    return dict(status='passed',samples=len(state),text_calls=len(text),overlay_vertices=len(geometry),self_blits=len(blits),images=hashes,renderer=renderer,lifecycle=life,loaded_modules=modules,asset_sha256=assets)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--case',action='append')
    a=p.parse_args();settings=json.loads((Path(__file__).with_name('cases.json')).read_text())
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    require(not a.output.exists(),'Reference output already exists; automatic replacement is forbidden')
    a.output.mkdir(parents=True);report=dict(status='pending',configuration=a.configuration,source=git('rev-parse','HEAD').decode().strip(),application_source=settings['application_source'],cases={},failures={})
    runtime=json.loads((a.orbiter.parent/'test-runtime.json').read_text());require(runtime['source_commit']==settings['application_source'],'Wrong pre-extraction application source')
    for case in settings['cases']:
        if a.case and case['id'] not in a.case:continue
        try:
            dirs=[];observed=[]
            for repeat in (1,2):
                directory=a.output.resolve()/(case['id']+'-'+str(repeat))
                def configure(directory):
                    config=directory/'Orbiter.cfg';config.write_text(config.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    (directory/'Scenarios/Behavior.scn').write_text(fixture(case))
                    (directory/'cockpit-case.txt').write_text(f"{case['target']} 60 {case['cockpit']} {case['left']} {case['right']} {case['hud']}\n")
                    (directory/'ogl-evidence.enabled').write_text('Real original production cockpit engineering capture\n')
                    (directory/'instrument-evidence.enabled').write_text('Original instruction text and frames 20/50; no rendering changes\n')
                    require((directory/'Modules/Plugin/ProductionCockpitDriver.dll').is_file(),'Same-SDK observation driver missing')
                    mesa_files(a.mesa.resolve(),directory)
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,{**case,'frames':60,'fixed_step':settings['fixed_step'],'epoch':settings['epoch']},configure)
                observed.append(inspect(directory,case,settings));dirs.append(directory)
            for name in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((dirs[0]/name).read_bytes()==(dirs[1]/name).read_bytes(),'Original deterministic repeat differs: '+name)
            ssim={str(frame):image_ssim((dirs[0]/f'instrument-{frame}.rgba').read_bytes(),(dirs[1]/f'instrument-{frame}.rgba').read_bytes(),1280,720) for frame in (20,50)}
            require(all(v>=settings['image_ssim_minimum'] for v in ssim.values()),'Original image repeat exceeds predeclared budget')
            report['cases'][case['id']]=dict(runs=observed,repeat_ssim=ssim,identical_state_and_display_text=True)
        except Exception as error:report['failures'][case['id']]=str(error)
    report['status']='passed' if not report['failures'] else 'failed';(a.output/'cockpit-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));require(not report['failures'],'Original cockpit gate failed; do not freeze or extract instrumentation')
if __name__=='__main__':main()
