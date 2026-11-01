#!/usr/bin/env python3
"""Snapshot a matching native build without overwriting any live mapped binary."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    build=a.build.resolve();destination=a.destination.resolve();files={}
    for name,target in [('orbiter-production','bin/orbiter-production'),('liborbiter_production_vessels.so','lib/liborbiter_production_vessels.so'),('liborbiter_production_boundary.so','lib/liborbiter_production_boundary.so')]:files[build/name]=target
    for file in (build/'NativeModules').rglob('*'):
        if file.is_file():files[file]=str(Path('NativeModules')/file.relative_to(build/'NativeModules'))
    checksums={name:digest(file) for file,name in files.items()}
    key=hashlib.sha256(json.dumps(checksums,sort_keys=True).encode()).hexdigest()
    version=destination/'versions'/key
    if not version.exists():
        version.mkdir(parents=True)
        for source,name in files.items():target=version/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest=dict(files=checksums,source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only'])))
        (version/'binaries.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for name,checksum in checksums.items():
        if digest(version/name)!=checksum:raise RuntimeError('Prepared native snapshot differs: '+name)
    temporary=destination/'current.tmp'
    temporary.unlink(missing_ok=True);temporary.symlink_to(Path('versions')/key,target_is_directory=True);os.replace(temporary,destination/'current')
    print(version)
if __name__=='__main__':main()
