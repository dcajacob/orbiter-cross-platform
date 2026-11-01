#!/usr/bin/env python3
"""Compare shared production terrain against frozen original Windows queries."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from frozen_reference import load
from capture import HERE,ROOT,compare,require
from mesa_runtime import digest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','modules','data','planets','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();metadata,golden=load();output=args.output.resolve();reference=HERE/'Reference'
    require(output!=reference and reference not in output.parents,'cannot overwrite frozen terrain reference')
    output.mkdir(parents=True,exist_ok=True)
    executable=args.executable.resolve(strict=True);modules=args.modules.resolve(strict=True)
    data=args.data.resolve();planets=args.planets.resolve();input_hashes={}
    for name,base in [('stock-data.lock.json',data),('standard-planets.lock.json',planets)]:
        profile=json.loads((HERE.parent/name).read_text())
        for relative,record in profile['data_files'].items():
            if name.startswith('stock') and not relative.startswith(('Kernels/','GravityModels/')):continue
            path=base/relative
            require(path.is_file() and path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],
                'terrain verification input differs: '+relative)
            input_hashes[relative]=record['sha256']
    results={}
    for mode in ('1','2'):
        for repeat in (1,2):
            command=[str(executable),str(ROOT/'Src/Celbody/SPICE/Config'),str(data),str(modules),str(planets/'Textures'),
                str(HERE/'points.csv'),mode,str(output/f'mode-{mode}-trace-{repeat}.csv')]
            run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
            (output/f'mode-{mode}-run-{repeat}.log').write_bytes(run.stdout)
            require(run.returncode==0,'shared production terrain probe failed; see run log')
        first=(output/f'mode-{mode}-trace-1.csv').read_bytes();second=(output/f'mode-{mode}-trace-2.csv').read_bytes()
        require(first==second,'native terrain repeats differ')
        results[mode]=compare(golden[mode],first)
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    report=dict(status='passed',source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        configuration=args.configuration,host=platform.platform(),executable_sha256=sha(executable),
        modules_sha256={p.relative_to(modules).as_posix():sha(p) for p in modules.rglob('*') if p.is_file() and p.suffix in ('.so','.dll')},
        working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','--','Src','Orbitersdk'])),
        input_files_sha256=input_hashes,protocol_sha256_lf=metadata['protocol_sha256_lf'],results=results,
        scope='actual production elevation manager, celestial bodies/modules and indexed assets; direct queries, not a native world/session/renderer')
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],configuration=args.configuration,results=results),indent=2))

if __name__=='__main__':main()
