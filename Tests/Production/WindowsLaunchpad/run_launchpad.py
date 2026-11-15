"""Launch one complete stock scene through the actual Windows Qt Launchpad."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

production = Path.cwd() / 'Tests/Production'
sys.path[:0] = [str(production/'RemainingStock'), str(production/'Client'), str(production)]
from inputs import ROOT, digest, require, sha_lf
from inventory import ships
from behavior_suite import link_or_copy
from run_client import mesa_files
from execution import run_process

STOCK = 'Scenarios/Delta-glider/DG Mk4 in orbit.scn'

def run(args):
    runtime = json.loads((args.runtime/'test-runtime.json').read_text())
    require(runtime['source_commit']==args.source, 'Windows runtime source differs')
    lock = json.loads((production/'production-source.lock.json').read_text())
    source = ROOT/STOCK
    require(sha_lf(source)==next(case['sha256'] for case in lock['scenarios'] if case['path']==STOCK),
            'The stock test scenario changed')
    root = args.output
    root.mkdir()
    for src in args.runtime.iterdir():
        if src.is_file() and src.suffix.lower() in ('.dll','.exe'):
            shutil.copy2(src,root/src.name)
    for directory in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
        src = args.runtime/directory
        if src.is_dir():
            shutil.copytree(src,root/directory,copy_function=link_or_copy)
    for body,names in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),
                       'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
        for name in names:
            original = root/'Modules/Celbody/Atmosphere'/(name+'.dll')
            destination = root/'Modules/Celbody'/body/'Atmosphere'/original.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(original,destination)
    for directory in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
        shutil.copytree(args.data/directory,root/directory,dirs_exist_ok=True,copy_function=link_or_copy)
    for name in json.loads((production/'standard-planets.lock.json').read_text())['data_files']:
        dst = root/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        link_or_copy(args.planets/name,dst)
    target = root/'Test Flights'/Path(STOCK).relative_to('Scenarios')
    target.parent.mkdir(parents=True)
    shutil.copyfile(source,target)
    base = (production/'Fixtures/Orbiter.cfg').read_text()
    base = base.replace('ScenarioDir = .\\Scenarios\\','ScenarioDir = .\\Test Flights\\')
    base = base.replace('  ProductionReferenceDriver','  LaunchpadFlightProbe\n  OGLClient')
    (root/'Orbiter.cfg').write_text(base,encoding='ascii')
    (root/'ogl-evidence.enabled').touch()
    mesa_files(args.mesa,root)
    require(digest(root/'Orbiter.exe')==runtime['files']['Orbiter.exe'],'Staged simulator image differs')
    for name, expected in runtime['files'].items():
        if name.startswith(('Config/','Meshes/')):
            require(digest(root/name)==expected,'Staged simulator resource differs: '+name)

    (root/'profile.json').write_text(json.dumps({'mode':'windows','executable':'Orbiter.exe'}))
    os.environ['ORBITER_LAUNCHPAD_TEST_RECEIPT'] = str(root/'launchpad-events.txt')
    os.environ['ORBITER_LAUNCHPAD_TEST_SETTINGS'] = str(root/'settings')
    launcher = run_process([str(args.launcher),'--profile',str(root/'profile.json')],root,95)
    require(launcher.returncode==0, f'Qt Launchpad exited with code {launcher.returncode}')
    expected_events = ['selected-and-launched-stock-scenario','launcher-hidden-during-flight',
                       'launcher-returned-with-selection']
    require((root/'launchpad-events.txt').read_text().splitlines()==expected_events,'Qt Launchpad transition differs')
    receipt = [line.split('=',1) for line in (root/'launchpad-flight.txt').read_text().splitlines()]
    details = {key:value for key,value in receipt if key!='vessel'}
    require(details['focus']=='GL-01' and details['class']=='DeltaGlider' and details['close-requested']=='1',
            'Wrong stock vessel or abnormal close request')
    actual = dict(value.split(':',1) for key,value in receipt if key=='vessel')
    require(actual==ships(source.read_bytes().decode('cp1252')),'The original stock roster changed')
    require((root/'launchpad-flight-end.txt').read_text().strip()=='48','Stock session did not close normally')
    lifecycle = json.loads((root/'graphics-lifecycle.json').read_text())
    require(lifecycle==dict(rendered_frames=48,successful_presents=48,context_deleted=True),
            'Full short window presentation and teardown are required')
    require('Could not find a module' not in (root/'Orbiter.log').read_text(errors='replace'),
            'Original vessel module missing')
    require(digest(target)==digest(source),'Launchpad changed the source scenario')
    result = dict(source=args.source, scenario=STOCK, input_sha256=digest(target), details=details,
                  lifecycle=lifecycle, launchpad_events=expected_events, full_runs_invoked=False)
    (root/'launchpad-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','data','planets','mesa','output','launcher'):
        parser.add_argument('--'+name,type=lambda arg:Path(arg).resolve(),required=True)
    parser.add_argument('--source',required=True)
    run(parser.parse_args())
