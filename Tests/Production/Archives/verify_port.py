#!/usr/bin/env python3
"""Check the actual shared archive reader against accepted original Windows."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess

from observations import HERE, ROOT, expected, fixtures, file_sha, observe, protocol, require, sha
from frozen_reference import compare, load


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    parser.add_argument('--data',type=Path,help='Optional verified full stock archive directory; default is generated fixtures only')
    args=parser.parse_args()
    _,golden=load()
    output=args.output.resolve()
    require(output!=HERE/'Reference' and HERE/'Reference' not in output.parents,'cannot overwrite accepted evidence')
    output.mkdir(parents=True,exist_ok=True)
    executable=args.executable.resolve(strict=True)
    try:
        if args.data:
            rows=observe(executable,args.data.resolve(),output)
        else:
            rows={}
            for ordinal,(name,path,layer,inputs) in enumerate(fixtures(output/'fixtures')):
                raw,observation=expected(path)
                for repeat in (1,2):
                    target=output/f'fixture-{ordinal}-{repeat}.bin'
                    run=subprocess.run([str(executable),str(path.parent.parent),str(layer),str(target)],
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
                    (output/f'fixture-{ordinal}-{repeat}.log').write_bytes(run.stdout)
                    require(run.returncode==0 and target.read_bytes()==raw,'shared archive fixture decode differs')
                    target.unlink()
                rows[name]=dict(inputs=inputs,**observation)
        for name,row in rows.items():
            require(row==golden['observations'][name],'shared archive differs from frozen Windows: '+name)
    finally:
        shutil.rmtree(output/'fixtures',ignore_errors=True)
    report=dict(status='passed',configuration=args.configuration,host=platform.platform(),
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        executable_sha256=file_sha(executable),protocol_sha256=sha((HERE/'protocol.json').read_bytes()),
        automatic_refresh=False,protocol=protocol(),observations=rows,
        scope='actual shared archive reader; full stock archive queries' if args.data else 'actual shared archive reader; generated fixtures only')
    report['working_tree_dirty']=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only','--',
        'Src','Orbitersdk','Tests/Production/Archives','Tests/Production/Boundary']))
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Shared production archives match frozen Windows exactly:',len(rows),'archives; repeats and independent decoder pass')


if __name__=='__main__':main()
