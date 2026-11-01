#!/usr/bin/env python3
"""Exercise actual Planet/Base CPU geometry and lifetime using stock resources.

This is component coverage, not a native application or scene acceptance gate.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from mesa_runtime import digest,require

def prepare(args,output):
    source_inputs={}
    fixture=tempfile.TemporaryDirectory(prefix='planet-config-',dir=output)
    config=Path(fixture.name)
    for relative in ('Config','Src/Celbody/SPICE/Config'):
        directory=ROOT/relative
        for path in sorted(directory.rglob('*')):
            if not path.is_file():continue
            target=config/path.relative_to(directory);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
            source_inputs[path.relative_to(ROOT).as_posix()]=digest(path)
    # Verify the same frozen kernels, gravity models and archives as terrain CI.
    inputs={}
    for name,base in (('stock-data.lock.json',args.data),('standard-planets.lock.json',args.planets)):
        profile=json.loads((ROOT/'Tests/Production'/name).read_text())
        for relative,record in profile['data_files'].items():
            if name.startswith('stock') and not relative.startswith(('Kernels/','GravityModels/')):continue
            path=base/relative
            require(path.is_file() and path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],'Planet input differs: '+relative)
            inputs[relative]=record['sha256']
    return fixture,config,source_inputs,inputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','modules','data','planets','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    fixture,config,source_inputs,inputs=prepare(args,output)
    command=[str(args.executable.resolve(strict=True)),str(config),str(args.data.resolve()),str(args.modules.resolve()),str((args.planets/'Textures').resolve()),str(ROOT/'Meshes')]
    process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (output/'run.log').write_bytes(process.stdout)
    require(process.returncode==0,'Production planet lifecycle/geometry failed; see '+str(output/'run.log'))
    text=process.stdout.decode(errors='replace')
    require('Earth bases=37 ' in text and 'Moon bases=1 ' in text and 'Mars bases=1 ' in text and '20 actual production Planet/Base load/unload cycles passed' in text,'Incomplete stock planet/base coverage')
    report=dict(status='passed',scope='Production Planet/Base/terrain/CPU mesh component lifecycle; not a native world/application/renderer',
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        executable_sha256=digest(args.executable),source_inputs=source_inputs,data_inputs=inputs,log_sha256=digest(output/'run.log'))
    (output/'planet-components.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Production stock planets, 39 bases, CPU geometry and 20 load/unload cycles passed')

if __name__=='__main__':main()
