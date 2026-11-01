#!/usr/bin/env python3
"""Compare actual native production modules against frozen original Windows."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from frozen_reference import load
from capture import HERE,ROOT,compare,require

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path,required=True)
    parser.add_argument('--modules',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();metadata,golden=load()
    output=args.output.resolve();reference=HERE/'Reference'
    require(output!=reference and reference not in output.parents,'cannot overwrite accepted SPICE evidence')
    output.mkdir(parents=True,exist_ok=True)
    executable=args.executable.resolve(strict=True);modules=args.modules.resolve(strict=True)
    for repeat in (1,2):
        command=[str(executable),str(ROOT/'Src/Celbody/SPICE/Config'),str(args.data.resolve()),str(modules),
                 str(HERE/'bodies.txt'),str(HERE/'epochs.txt'),str(output/f'trace-{repeat}.csv')]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (output/f'run-{repeat}.log').write_bytes(result.stdout)
        require(result.returncode==0,'native production SPICE probe failed; see run log')
    first=(output/'trace-1.csv').read_bytes();second=(output/'trace-2.csv').read_bytes()
    require(first==second,'native production SPICE repeats differ')
    report=compare(golden,first)
    checksum=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report.update(source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        configuration=args.configuration,host=platform.platform(),executable_sha256=checksum(executable),
        modules_sha256={p.relative_to(modules).as_posix():checksum(p) for p in modules.rglob('*') if p.is_file() and p.suffix in ('.so','.dll')},
        working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','--','Src','Orbitersdk'])),
        reference_protocol_sha256_lf=metadata['protocol_sha256_lf'],
        scope='actual native SPICE/atmosphere modules and production CelestialBody configuration; direct callbacks only, not a production world/session or renderer')
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
