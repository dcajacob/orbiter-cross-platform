#!/usr/bin/env python3
"""Observe original Windows terrain before moving its numerical implementation."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from capture_reference import link_or_copy
from mesa_runtime import digest,require

def protocol(original=False):
    lock=json.loads((HERE/'protocol.json').read_text())
    require(lock['automatic_refresh'] is False,'automatic terrain reference refresh is forbidden')
    inputs=dict(lock['inputs_sha256_lf'])
    if original: inputs.update(lock['production_source_sha256_lf'])
    for name,expected in inputs.items():
        require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected,
            'terrain observation input/source changed: '+name)
    return lock

def rows(data):
    fields=['mode','body','requested_level','cache','index','longitude_deg','latitude_deg',
            'elevation_m','nx','ny','nz','loaded_level']
    reader=csv.DictReader(io.StringIO(data.decode('ascii'),newline=''))
    require(reader.fieldnames==fields,'terrain CSV schema differs')
    values=list(reader);require(len(values)==2040,'terrain sample count differs')
    points=list(csv.DictReader((HERE/'points.csv').open(newline='')))
    expected=[(body,str(level),str(cache),str(i)) for body in ('Earth','Moon','Mars')
              for cache in (0,1) for level in (8,12,16,0) for i in range(85)]
    modes=set()
    for row,key in zip(values,expected):
        require(tuple(row[name] for name in ('body','requested_level','cache','index'))==key,'terrain query order differs')
        modes.add(row['mode']);point=points[int(row['index'])]
        for name in ('longitude_deg','latitude_deg'):
            require(float(row[name])==float(point[name]),'terrain query coordinate differs')
        for name in ('elevation_m','nx','ny','nz'): require(math.isfinite(float(row[name])),'nonfinite terrain state')
        require(0<int(row['loaded_level'])<=21,'required stock terrain did not load')
        norm=math.sqrt(sum(float(row[name])**2 for name in ('nx','ny','nz')))
        require(abs(norm-1)<=1e-12,'terrain normal is not a unit vector')
    require(modes in ({'1'},{'2'}),'terrain interpolation mode differs')
    for body in ('Earth','Moon','Mars'):
        heights=[float(r['elevation_m']) for r in values if r['body']==body]
        require(max(heights)-min(heights)>100,'required real terrain has no relief: '+body)
    return values

def compare(first,second):
    lock=protocol();a=rows(first);b=rows(second);maximum=dict(elevation_m=0.,normal_components=0.)
    for x,y in zip(a,b):
        for field in ('mode','body','requested_level','cache','index','longitude_deg','latitude_deg','loaded_level'):
            require(float(x[field])==float(y[field]) if field.endswith('_deg') else x[field]==y[field],
                'terrain discrete input/result differs: '+field)
        height=abs(float(x['elevation_m'])-float(y['elevation_m']))
        normal=max(abs(float(x[name])-float(y[name])) for name in ('nx','ny','nz'))
        require(height<=lock['budgets']['elevation_m'] and normal<=lock['budgets']['normal_components'],
            'production terrain exceeds predeclared budget')
        maximum['elevation_m']=max(maximum['elevation_m'],height)
        maximum['normal_components']=max(maximum['normal_components'],normal)
    return dict(status='passed',samples=len(a),maximum=maximum)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','data','planets','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();lock=protocol(original=True)
    require(platform.system()=='Windows','original terrain capture requires native Windows')
    runtime=args.runtime.resolve();data=args.data.resolve();planets=args.planets.resolve();output=args.output.resolve()
    require(not output.exists() and (HERE/'Reference').resolve() not in (output,*output.parents),
        'capture needs a new non-reference directory')
    manifest=json.loads((runtime/'test-runtime.json').read_text())
    require(manifest['source_commit']==lock['runtime_source'],'original terrain application identity differs')
    for name,expected in manifest['files'].items():require(digest(runtime/name)==expected,'mixed/stale Windows runtime: '+name)
    for profile,base in [('stock-data.lock.json',data),('standard-planets.lock.json',planets)]:
        for name,record in json.loads((HERE.parent/profile).read_text())['data_files'].items():
            require(digest(base/name)==record['sha256'],'terrain input asset differs: '+name)
    driver=runtime/'Modules/Plugin/ProductionElevationObserver.dll'
    require(driver.is_file(),'production elevation observer was not staged')
    output.mkdir(parents=True);results={}
    for mode in (1,2):
        for repeat in (1,2):
            directory=output/f'mode-{mode}-run-{repeat}';directory.mkdir()
            for path in runtime.iterdir():
                if path.is_file() and path.suffix.lower() in ('.exe','.dll'):shutil.copy2(path,directory/path.name)
            for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
                if (runtime/name).is_dir():shutil.copytree(runtime/name,directory/name,copy_function=link_or_copy)
            for body,models in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),
                'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
                for model in models:
                    source=directory/'Modules/Celbody/Atmosphere'/(model+'.dll')
                    target=directory/'Modules/Celbody'/body/'Atmosphere'/(model+'.dll')
                    require(source.is_file(),'required source-built atmosphere is missing')
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
                shutil.copytree(data/name,directory/name,dirs_exist_ok=True,copy_function=link_or_copy)
            for name in json.loads((HERE.parent/'standard-planets.lock.json').read_text())['data_files']:
                target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);link_or_copy(planets/name,target)
            (directory/'Scenarios').mkdir()
            shutil.copy2(HERE.parent/'Fixtures/Sol-ISS-ShuttlePB.scn',directory/'Scenarios/Reference.scn')
            config=(HERE.parent/'Fixtures/Orbiter.cfg').read_text().replace('ProductionReferenceDriver','ProductionElevationObserver')
            # Original Config accepts explicit linear mode=1. Cubic mode=2 is
            # its original default; the original parser rejects an explicit 2.
            if mode==1:config+='\nElevationMode = 1\n'
            (directory/'Orbiter.cfg').write_text(config)
            (directory/'elevation-mode.txt').write_text(str(mode))
            shutil.copy2(HERE/'points.csv',directory/'elevation-points.csv')
            command=[str(directory/'Orbiter.exe'),'--scenariox=Reference','--fixedstep=1','--maxframes=2']
            with (directory/'console.txt').open('wb') as console:
                completed=subprocess.run(command,cwd=directory,stdout=console,stderr=subprocess.STDOUT,timeout=240)
            require(completed.returncode==0 and (directory/'elevation.csv').is_file(),'original terrain observer failed; see application logs')
            trace=(directory/'elevation.csv').read_bytes();rows(trace)
            (output/f'mode-{mode}-trace-{repeat}.csv').write_bytes(trace)
        first=(output/f'mode-{mode}-trace-1.csv').read_bytes();second=(output/f'mode-{mode}-trace-2.csv').read_bytes()
        require(first==second,'original Windows terrain repeats differ');results[str(mode)]=compare(first,second)
    report=dict(status='passed',source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        runtime_source=lock['runtime_source'],configuration=args.configuration,host=platform.platform(),
        protocol_sha256_lf=hashlib.sha256((HERE/'protocol.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        driver_sha256=digest(driver),runtime_manifest_sha256=digest(runtime/'test-runtime.json'),results=results)
    (output/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Original Windows terrain repeats pass: 2,040 actual height/normal/cache queries in each interpolation mode')

if __name__=='__main__':main()
