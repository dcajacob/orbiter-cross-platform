#!/usr/bin/env python3
"""Compare actual native vessel states with matching pre-extraction Windows inputs.

Numerical component coverage only. This does not accept application callback,
camera, renderer, cockpit, input-device or stock-corpus integration.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from mesa_runtime import digest,require
from frozen_behavior import load_reference
from behavior_suite import compare_states
from Planets.verify import prepare

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','modules','data','planets','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    temporary,config,source_inputs,data_inputs=prepare(args,output)
    resources=Path(temporary.name);meshes=resources/'Meshes'
    for source,target in [(ROOT/'Meshes',meshes),
        (ROOT/'Src/Vessel/ISS/Meshes',meshes/'ISS'),
        (ROOT/'Src/Vessel/ShuttlePB/Meshes',meshes),
        (ROOT/'Src/Vessel/ISS/Config',config/'Vessels'),
        (ROOT/'Src/Vessel/ShuttlePB/Config',config/'Vessels')]:
        shutil.copytree(source,target,dirs_exist_ok=True)
        for path in source.rglob('*'):
            if path.is_file():source_inputs[path.relative_to(ROOT).as_posix()]=digest(path)
    metadata=load_reference(ROOT/'Tests/Production/BehaviorReference')
    cases=json.loads((ROOT/'Tests/Production/behavior-cases.json').read_text())['cases']
    selected=[case for case in cases if case['id'] in ('rcs','autopilot','callbacks')]
    artifact=metadata['artifacts'][args.configuration]
    results={}
    with zipfile.ZipFile(ROOT/'Tests/Production/BehaviorReference'/artifact['path']) as reference:
        for case in selected:
            directory=output/case['id'];directory.mkdir(exist_ok=True)
            base=f'production-behavior/{case["id"]}/'
            for name in ('Orbiter.cfg','Scenarios/Behavior.scn','behavior-state.csv'):
                target=directory/'original'/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(reference.read(base+name))
            for repeat in (1,2):
                command=[str(args.executable.resolve(strict=True)),str(config),str(args.data.resolve()),str(args.modules.resolve()),
                    str((args.planets/'Textures').resolve()),str(meshes),str(directory/'original/Orbiter.cfg'),
                    str(directory/'original/Scenarios/Behavior.scn'),str(directory/f'state-{repeat}.csv'),case['id']]
                process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
                (directory/f'run-{repeat}.log').write_bytes(process.stdout)
                require(process.returncode==0,'Actual native vessel failed: '+str(directory/f'run-{repeat}.log'))
            first,second=directory/'state-1.csv',directory/'state-2.csv'
            require(first.read_bytes()==second.read_bytes(),'Native repeated vessel states differ: '+case['id'])
            rows=list(csv.DictReader(io.StringIO(first.read_text())))
            require(len(rows)==2*(case['frames']+1),'Native vessel sample count differs')
            initial=next(row for row in rows if row['tick']=='0' and row['object']=='PB')
            require(float(initial['density'])>0,'Required production atmosphere did not contribute')
            results[case['id']]=dict(states=compare_states(directory/'original/behavior-state.csv',first,case),
                repeated_sha256=digest(first),source_atmosphere='EarthAtmJ71G at its CMake install destination')
    for mode in ('orbit','controls'):
        directory=output/mode;directory.mkdir(exist_ok=True)
        for repeat in (1,2):
            command=[str(args.executable.resolve(strict=True)),str(config),str(args.data.resolve()),str(args.modules.resolve()),
                str((args.planets/'Textures').resolve()),str(meshes),str(ROOT/'Tests/Production/Fixtures/Orbiter.cfg'),
                str(ROOT/'Tests/Production/Fixtures/Sol-ISS-ShuttlePB.scn'),str(directory/f'state-{repeat}.csv'),mode]
            process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            (directory/f'run-{repeat}.log').write_bytes(process.stdout)
            require(process.returncode==0,'Native 6000-step world/vessel execution failed')
        first=directory/'state-1.csv'
        require(first.read_bytes()==(directory/'state-2.csv').read_bytes(),'Native 6000-step repeat differs')
        require(len(list(csv.DictReader(first.open())))==601*5,'Native finalized 6000-step sample count differs')
        results[mode]=dict(status='repeatable 6000-step execution; matching long-duration Windows comparison still required',sha256=digest(first))
    report=dict(status='passed numerical component cases',source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','--','Src','Orbitersdk'])),
        configuration=args.configuration,host=platform.platform(),executable_sha256=digest(args.executable),
        source_inputs=source_inputs,data_inputs=data_inputs,results=results,
        frozen_profile='BehaviorReference 41193020450: actual installed atmosphere modules',
        excluded_profile='Initial Reference 41187217665 logged missing atmosphere DLLs; it is preserved, never replaced or used to disable native forces',
        scope='Actual native production Sol/Vessel/SDK/ShuttlePB numerical states. Native application/callback/camera/rendering acceptance remains outstanding.')
    (output/'vessel-components.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],results=results),indent=2))

if __name__=='__main__':main()
