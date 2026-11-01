#!/usr/bin/env python3
"""Capture original production SPICE callbacks without refreshing references."""
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
    require(lock['automatic_refresh'] is False,'SPICE reference refresh is forbidden')
    for name,expected in lock['inputs_sha256_lf'].items():
        require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected,'SPICE input differs: '+name)
    if original:
        for name,expected in lock['production_source_sha256_lf'].items():
            require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected,'SPICE changed before Windows capture')
    return lock

def rows(data):
    lock=protocol()
    reader=csv.DictReader(io.StringIO(data.decode('ascii'),newline=''))
    fields=['body','mode','request','index','time','response']+['p'+str(i) for i in range(12)]
    require(reader.fieldnames==fields,'SPICE trace schema differs')
    result=list(reader);require(len(result)==lock['rows'],'SPICE trace coverage differs')
    bodies=(HERE/'bodies.txt').read_text().splitlines()
    epochs=[float(value) for value in (HERE/'epochs.txt').read_text().splitlines()]
    index=0
    for body in bodies:
        for request in lock['requests']:
            schedule=[('slow',i,time) for i,time in enumerate(epochs)]
            schedule += [('reset',0,-1000000.)]
            schedule += [('forward',i,float(i)) for i in range(0,6001,100)]
            schedule += [('jump',i,time) for i,time in enumerate([6000.,6000.5,6030.,0.,-1.,120.,60.,61.,3600.,10.,0.,0.125,7200.])]
            for mode,tick,time in schedule:
                row=result[index];index+=1
                require([row['body'],row['mode'],int(row['request']),int(row['index']),float(row['time'])]==
                    [body,mode,request,tick,time],'SPICE discrete query schedule differs')
                require((int(row['response'])>0 or (body=='Sun' and request==12)) and
                    all(math.isfinite(float(row['p'+str(i)])) for i in range(12)),
                    'missing/nonfinite production SPICE response')
    return result

def compare(left,right):
    lock=protocol();a,b=rows(left),rows(right)
    maximum=dict(position_m=0.,velocity_m_s=0.)
    for x,y in zip(a,b):
        require(all(x[k]==y[k] for k in ['body','mode','request','index','response']) and float(x['time'])==float(y['time']),
            'SPICE query identity/flags differ')
        for offset,quantity in [(0,'position_m'),(3,'velocity_m_s'),(6,'position_m'),(9,'velocity_m_s')]:
            error=math.dist([float(x['p'+str(i)]) for i in range(offset,offset+3)],
                            [float(y['p'+str(i)]) for i in range(offset,offset+3)])
            require(error<=lock['budgets'][quantity],'SPICE '+quantity+' budget exceeded for '+x['body'])
            maximum[quantity]=max(maximum[quantity],error)
    return dict(status='passed',rows=len(a),maximum_error=maximum,budgets=lock['budgets'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();lock=protocol(original=True)
    require(platform.system()=='Windows','original SPICE capture requires native Windows')
    output=args.output.resolve();reference=HERE/'Reference'
    require(not output.exists() and output!=reference and reference not in output.parents,'capture needs a new non-reference output')
    runtime=args.runtime.resolve();data=args.data.resolve()
    require((runtime/'Modules/Plugin/ProductionSpiceObserver.dll').is_file(),
            'observer DLL was not staged in the source-built runtime plugin directory')
    manifest=json.loads((runtime/'test-runtime.json').read_text())
    require(manifest['source_commit']==lock['runtime_source'],'SPICE observer needs the pinned source-built application')
    # The observer is added after unpacking; all original runtime files remain exact.
    for name,expected in manifest['files'].items():require(digest(runtime/name)==expected,'mixed/stale runtime file: '+name)
    output.mkdir(parents=True)
    for repeat in (1,2):
        directory=output/('run-'+str(repeat));directory.mkdir()
        for path in runtime.iterdir():
            if path.is_file() and path.suffix.lower() in ('.exe','.dll'):shutil.copy2(path,directory/path.name)
        for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
            if (runtime/name).is_dir():shutil.copytree(runtime/name,directory/name,copy_function=link_or_copy)
        for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
            shutil.copytree(data/name,directory/name,dirs_exist_ok=True,copy_function=link_or_copy)
        (directory/'Scenarios').mkdir()
        shutil.copy2(HERE.parent/'Fixtures/Sol-ISS-ShuttlePB.scn',directory/'Scenarios/Reference.scn')
        config=(HERE.parent/'Fixtures/Orbiter.cfg').read_text().replace('ProductionReferenceDriver','ProductionSpiceObserver')
        (directory/'Orbiter.cfg').write_text(config)
        shutil.copy2(HERE/'epochs.txt',directory/'spice-epochs.txt');shutil.copy2(HERE/'bodies.txt',directory/'spice-bodies.txt')
        command=[str(directory/'Orbiter.exe'),'--scenariox=Reference','--fixedstep=1','--maxframes=1']
        with (directory/'console.txt').open('wb') as console:
            run=subprocess.run(command,cwd=directory,stdout=console,stderr=subprocess.STDOUT,timeout=180)
        require(run.returncode==0 and (directory/'spice-modules.csv').is_file(),'actual Windows SPICE observer failed; see console/Orbiter logs')
        trace=(directory/'spice-modules.csv').read_bytes();rows(trace)
        (output/('trace-'+str(repeat)+'.csv')).write_bytes(trace)
    first=(output/'trace-1.csv').read_bytes();second=(output/'trace-2.csv').read_bytes()
    require(first==second,'Windows SPICE module repeats differ')
    report=compare(first,second)
    report.update(source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        runtime_source=lock['runtime_source'],configuration=args.configuration,host=platform.platform(),
        protocol_sha256=digest(HERE/'protocol.json'),trace_sha256=hashlib.sha256(first).hexdigest(),
        driver_sha256=digest(runtime/'Modules/Plugin/ProductionSpiceObserver.dll'),runtime_manifest_sha256=digest(runtime/'test-runtime.json'))
    (output/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
