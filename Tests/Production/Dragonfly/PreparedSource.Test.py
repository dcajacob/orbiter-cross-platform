#!/usr/bin/env python3
"""Exercise actual generated-source preparation, read-only verification and damage rejection."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def tree(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();a.output=a.output.resolve()
    if a.output.exists():raise ValueError('Fresh preparation control output required')
    a.output.mkdir(parents=True)
    def run(target,label,verify=False):
        command=[sys.executable,'-B',str(HERE/'prepare_native.py'),'--output',str(target)]
        if verify:command.append('--verify-output')
        log=a.output/(label+'.log')
        with log.open('w') as stream:process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
        return process.returncode,log.read_text()
    valid=a.output/'valid';code,log=run(valid,'prepare')
    if code:raise ValueError('Actual source preparation failed: '+log[-2000:])
    before=tree(valid);code,log=run(valid,'verify',True)
    if code or tree(valid)!=before:raise ValueError('Actual JSON/source round-trip verification failed or wrote files: '+log[-2000:])
    results=[]
    for label,expected in [('physical-calculation','Generated native source bytes changed'),
                           ('resource-id-provenance','Native module source provenance changed')]:
        target=a.output/label;shutil.copytree(valid,target)
        if label=='physical-calculation':
            path=target/'Thermal.cpp';body=path.read_bytes()
            if body.count(b'energy=0;')!=1:raise ValueError('Actual thermal calculation control anchor differs')
            path.write_bytes(body.replace(b'energy=0;',b'energy=1;',1))
        else:
            path=target/'native-source.json';report=json.loads(path.read_text());report['bitmap_resources'][0][0]+=1
            path.write_text(json.dumps(report,indent=2)+'\n')
        damaged=tree(target);code,log=run(target,label,True)
        if code==0 or expected not in log or tree(target)!=damaged:
            raise ValueError('Actual prepared-source damage accepted or read-only verification wrote files: '+label)
        results.append(dict(control=label,status='rejected-without-writing',reason=expected))
    if tree(valid)!=before:raise ValueError('Valid generated source changed during damaged-copy controls')
    report=dict(status='passed',producer_commit=json.loads((valid/'native-source.json').read_text())['producer_commit'],
        prepared_files_sha256=before,source_json_round_trip_verified=True,verification_read_only=True,controls=results,
        preparer_sha256=hashlib.sha256((HERE/'prepare_native.py').read_bytes()).hexdigest(),
        test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_admission_qualified=False,phase6_complete=False)
    (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Actual prepared-source JSON/byte round trip passed; physical and resource-ID damage rejected without writing inputs')


if __name__=='__main__':main()
