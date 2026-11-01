#!/usr/bin/env python3
"""Compare the actual native celestial world with the unchanged Windows reference."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from Planets.verify import prepare
from frozen_reference import load_reference
from compare_references import quaternion
from trace_tools import distance,quaternion_angle,LIMITS
from mesa_runtime import digest,require

def compare(data):
    metadata=load_reference(ROOT/'Tests/Production/Reference')
    reference=metadata['artifacts']['Release']
    with zipfile.ZipFile(ROOT/'Tests/Production/Reference'/reference['path']) as archive:
        golden=list(csv.DictReader(io.StringIO(archive.read('production-reference/orbit/production-state.csv').decode('ascii'))))
    rows=list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    require(len(rows)==601*41,'Incomplete production Sol trace')
    initial=[r['body'] for r in rows[:41]]
    require(len(set(initial))==41 and {'Sun','Earth','Moon'}<=set(initial),'Production Sol body identities differ')
    selected={}
    for position,row in enumerate(rows):
        step=position//41*10
        require(int(row['step'])==step and float(row['seconds'])==step and int(row['index'])==position%41 and row['body']==initial[position%41],'World sample time/order differs')
        require(all(math.isfinite(float(value)) for key,value in row.items() if key!='body'),'Nonfinite world state')
        require(abs(float(row['mjd'])-51982.5-step/86400)<=LIMITS['mjd_days'],'World MJD differs')
        matrix=[[float(row[f'r{i}{j}']) for j in range(1,4)] for i in range(1,4)]
        require(all(abs(sum(matrix[i][k]*matrix[j][k] for k in range(3))-(1 if i==j else 0))<=1e-12 for i in range(3) for j in range(3)),'World rotation is not orthonormal')
        if row['body'] in ('Sun','Earth','Moon'):selected[(step,row['body'])]=row
    maximum=dict(position_m=0.,velocity_m_s=0.,orientation_rad=0.,mjd_days=0.)
    for ref in golden:
        if ref['object'] not in ('Sun','Earth','Moon'):continue
        row=selected[(int(ref['step']),ref['object'])]
        rotation={f'm{i}{j}':row[f'r{i}{j}'] for i in range(1,4) for j in range(1,4)}
        errors=dict(position_m=distance([float(ref[k]) for k in ('x','y','z')],[float(row[k]) for k in ('px','py','pz')]),
            velocity_m_s=distance([float(ref[k]) for k in ('vx','vy','vz')],[float(row[k]) for k in ('vx','vy','vz')]),
            orientation_rad=quaternion_angle(quaternion(ref),quaternion(rotation)),mjd_days=abs(float(ref['mjd'])-float(row['mjd'])))
        for key,error in errors.items():
            require(math.isfinite(error) and error<=LIMITS[key],f"{ref['object']} step {ref['step']}: {key} exceeds original budget: {error}")
            maximum[key]=max(maximum[key],error)
        require(float(row['mass'])==float(ref['mass']),'Configured celestial mass changed')
    return dict(rows=len(rows),compared_windows_states=len(selected),maximum=maximum)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','modules','data','planets','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    fixture,config,source_inputs,inputs=prepare(args,output)
    executable=args.executable.resolve(strict=True)
    for repeat in (1,2):
        command=[str(executable),str(config),str(args.data.resolve()),str(args.modules.resolve()),str((args.planets/'Textures').resolve()),str(ROOT/'Meshes'),str(output/f'trace-{repeat}.csv')]
        process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        (output/f'run-{repeat}.log').write_bytes(process.stdout)
        require(process.returncode==0,'Production world probe failed; see '+str(output/f'run-{repeat}.log'))
    first=(output/'trace-1.csv').read_bytes();second=(output/'trace-2.csv').read_bytes()
    require(first==second,'Production world repeated traces differ')
    result=compare(first)
    # Fail after some real bodies/modules have been constructed. This tests
    # actual partial-world cleanup, including under ASan/LSan, without proxies.
    earth=config/'Earth.cfg';original=earth.read_text()
    require(original.count('Module = spice')==1,'Unexpected stock Earth module selection')
    earth.write_text(original.replace('Module = spice','Module = RequiredMissingFixture'))
    command=[str(executable),str(config),str(args.data.resolve()),str(args.modules.resolve()),str((args.planets/'Textures').resolve()),str(ROOT/'Meshes'),str(output/'rejected-trace.csv')]
    failed=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (output/'missing-module.log').write_bytes(failed.stdout)
    failure=failed.stdout.decode(errors='replace')
    require(failed.returncode==1 and 'RequiredMissingFixture' in failure,'Missing required module was not rejected explicitly')
    require(not any(marker in failure for marker in ('AddressSanitizer','LeakSanitizer','runtime error:')),'Partial-world failure leaked or corrupted resources')

    report=dict(status='passed',source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','--','Src','Orbitersdk'])),
        configuration=args.configuration,host=platform.platform(),executable_sha256=digest(executable),
        source_inputs=source_inputs,data_inputs=inputs,result=result,
        missing_module_failure='explicit rejection with partial-world cleanup',
        scope='Actual PlanetarySystem celestial graph/update, not native vessels/camera/renderer; all 41 bodies observed, Sun/Earth/Moon compared with original Windows; full SPICE module parity is separate')
    (output/'world-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='passed',result=result),indent=2))
if __name__=='__main__':main()
