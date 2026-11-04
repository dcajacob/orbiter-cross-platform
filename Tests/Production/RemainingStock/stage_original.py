"""Stage complete original scenes, all preserved inputs and every named recording."""
import json
import shutil
from execution import run_process

from behavior_suite import link_or_copy
from mesa_runtime import require,digest
from inputs import ROOT,recordings,stage_recordings,stage_delivery_repairs,argument
from configuration_input import stage as stage_configuration


def run(executable,data,planets,directory,config,case,configure,*,process_timeout=240):
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
    for name in json.loads((ROOT/'Tests/Production/standard-planets.lock.json').read_text())['data_files']:
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);link_or_copy(planets/name,target)
    (directory/'Scenarios').mkdir()
    cfg=(ROOT/'Tests/Production/Fixtures/Orbiter.cfg').read_text().replace('ProductionReferenceDriver','ProductionBehaviorDriver')
    (directory/'Orbiter.cfg').write_text(cfg+'\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n',encoding='ascii')
    stage_recordings(directory,case,config)
    configure(directory)
    preserved=json.loads((executable.parent/'test-runtime.json').read_text())['files']
    repairs=stage_delivery_repairs(directory,config,preserved)
    argv=[str(directory/executable.name),argument(case),f"--fixedstep={config['fixed_step']:.17g}",f"--maxframes={config['frames']}"]
    inputs={p.relative_to(directory).as_posix():digest(p) for name in ('Config','Meshes','Scenarios','Flights')
            for p in (directory/name).rglob('*') if p.is_file()}
    for name in recordings(case,config):require(name in inputs,'Staged recording missing before original execution')
    expected_inputs={name:value for name,value in preserved.items() if name.startswith(('Config/','Meshes/'))}
    require(all(inputs[name]==value for name,value in expected_inputs.items()),'Preserved input files differ before execution')
    configuration=stage_configuration(directory)
    (directory/'invocation.json').write_text(json.dumps(dict(argv=argv,case=case,scenario_entry_point=case['scenario_entry_point'],
        input_sha256=inputs,preserved_inputs_sha256=expected_inputs,delivery_repairs=repairs,
        configuration_input=configuration,
        data_profiles={name:digest(ROOT/'Tests/Production'/name) for name in ('stock-data.lock.json','standard-planets.lock.json')},
        driver_sha256=digest(directory/'Modules/Plugin/ProductionCockpitDriver.dll')),indent=2)+'\n')
    process=run_process(argv,directory,process_timeout)
    require(process.returncode==0,'Preserved original process returned '+str(process.returncode))
    require('Could not find a module' not in (directory/'Orbiter.log').read_text(errors='replace'),
            'Required original vessel module failed; generic fallback prohibited')
