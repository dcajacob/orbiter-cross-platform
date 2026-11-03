#!/usr/bin/env python3
"""Stage the narrow native production scene from verified original resources.

Development provisioner; this is not the Phase 8 release asset installer.
Windows installation overlay order is explicit. No proxy models are generated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[3]
def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('data','planets','destination'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--delta-glider',action='store_true',help='Include the stock DG and DG-S installation resources and scenarios')
    args=parser.parse_args();destination=args.destination.resolve();destination.mkdir(parents=True,exist_ok=True)
    inputs={}
    for lock,base in [('stock-data.lock.json',args.data),('standard-planets.lock.json',args.planets)]:
        records=json.loads((ROOT/'Tests/Production'/lock).read_text())['data_files']
        for name,record in records.items():
            if name=='Fonts/architext.regular.ttf':continue
            path=base/name
            if not path.is_file() or path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:
                raise ValueError('Original resource differs: '+str(path))
            inputs[name]=record['sha256']
    chosen={}
    def overlay(source,target):
        if not source.is_dir():raise ValueError('Required source resource directory missing: '+str(source))
        local={}
        for path in sorted(source.rglob('*')):
            if not path.is_file() or path.name=='architext.regular.ttf':continue
            relative=(target/path.relative_to(source)).as_posix();key=relative.casefold()
            if key in local:raise ValueError('Conflicting case aliases within original resource source: '+relative)
            local[key]=str(path)
            # Match Windows' case-insensitive installation overlay behavior.
            spelling=chosen[key][0] if key in chosen else relative
            chosen[key]=(spelling,path)
    overlay(ROOT/'Config',Path('Config'));overlay(ROOT/'Src/Celbody/SPICE/Config',Path('Config'))
    overlay(ROOT/'Meshes',Path('Meshes'));overlay(ROOT/'Textures',Path('Textures'))
    for name in ('ISS','ShuttlePB'):
        source=ROOT/'Src/Vessel'/name
        overlay(source/'Config',Path('Config/Vessels'))
        overlay(source/'Meshes',Path('Meshes/ISS') if name=='ISS' else Path('Meshes'))
        overlay(source/'Textures',Path('Textures/ISS') if name=='ISS' else Path('Textures'))
    if args.delta_glider:
        overlay(ROOT/'Script',Path('Script'))
        overlay(ROOT/'Scenarios',Path('Scenarios'))
        overlay(ROOT/'Flights',Path('Flights'))
        source=ROOT/'Src/Vessel/DeltaGlider'
        for name,target in (('Config','Config/Vessels'),('Meshes','Meshes/DG'),
                            ('Textures','Textures/DG'),('Textures2','Textures2/DG'),
                            ('Script','Script/DG'),('Thumbnail','Images/Vessels/Default')):
            overlay(source/name,Path(target))
    for name in ('Textures','Textures2','Fonts'):
        overlay(args.data/name,Path(name))
    overlay(ROOT/'OVP/OGLClient/shaders',Path('Modules/OGLClient'))
    sources={}
    for relative,source in chosen.values():
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if digest(target)!=digest(source):raise ValueError('Existing staged resource differs: '+str(target))
        else:
            try:os.link(source,target)
            except OSError:shutil.copy2(source,target)
        sources[relative]=dict(source=str(source.resolve()),sha256=digest(target))
    scope='original stock Sol/ISS/ShuttlePB external view'
    if args.delta_glider:scope+=' with DG/DG-S vessel resources and stock scenarios'
    (destination/'resources.json').write_text(json.dumps(dict(scope=scope,
        source_resources=sources,locked_data=inputs,excluded='Fonts/architext.regular.ttf'),indent=2)+'\n')
    print('Verified and staged',len(sources),'original source/data resources; planetary archives remain at',args.planets.resolve())
if __name__=='__main__':main()
