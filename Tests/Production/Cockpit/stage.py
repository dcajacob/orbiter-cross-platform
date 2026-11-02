#!/usr/bin/env python3
"""Stage verified SDK/data like behavior_suite, with the cockpit validator."""
import json,shutil,subprocess
from pathlib import Path
from behavior_suite import link_or_copy
from mesa_runtime import require,digest
HERE=Path(__file__).resolve().parent
def run(executable,data,planets,directory,case,configure):
    directory.mkdir()
    for p in executable.parent.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,directory/p.name)
    for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
        source=executable.parent/name
        if source.is_dir():shutil.copytree(source,directory/name,copy_function=link_or_copy)
    for body,modules in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
        for module in modules:
            source=directory/'Modules/Celbody/Atmosphere'/(module+'.dll');target=directory/'Modules/Celbody'/body/'Atmosphere'/(module+'.dll')
            require(source.is_file(),'Required original atmosphere module missing: '+module)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
        require((data/name).is_dir(),'Required locked data missing: '+name)
        shutil.copytree(data/name,directory/name,dirs_exist_ok=True,copy_function=link_or_copy)
    for name in json.loads((HERE.parent/'standard-planets.lock.json').read_text())['data_files']:
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);link_or_copy(planets/name,target)
    (directory/'Scenarios').mkdir()
    config=(HERE.parent/'Fixtures/Orbiter.cfg').read_text().replace('ProductionReferenceDriver','ProductionBehaviorDriver')
    (directory/'Orbiter.cfg').write_text(config+'\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n',encoding='ascii')
    configure(directory)
    argv=[str(directory/executable.name),'--scenariox=Behavior',f"--fixedstep={case['fixed_step']:.17g}",f"--maxframes={case['frames']}"]
    (directory/'invocation.json').write_text(json.dumps(dict(argv=argv,case=case,
        input_sha256={p.relative_to(directory).as_posix():digest(p) for name in ('Config','Meshes','Scenarios') for p in (directory/name).rglob('*') if p.is_file()},
        data_profiles={name:digest(HERE.parent/name) for name in ('stock-data.lock.json','standard-planets.lock.json')},
        driver_sha256=digest(directory/'Modules/Plugin/ProductionCockpitDriver.dll')),indent=2)+'\n')
    with (directory/'console.txt').open('w') as console:subprocess.run(argv,cwd=directory,stdout=console,stderr=subprocess.STDOUT,check=True,timeout=240)
    require('Could not find a module' not in (directory/'Orbiter.log').read_text(errors='replace'),'Required real vessel module failed; generic fallback is prohibited')
