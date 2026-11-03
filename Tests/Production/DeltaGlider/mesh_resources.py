#!/usr/bin/env python3
"""Verify every generated DG header ID against the original Windows mesh tables."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'


def values(pairs):
    table=dict(pairs)
    if not table or len(table)!=len(pairs):
        raise ValueError('Missing or duplicate mesh resource definition')
    return table


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    results={}
    for stem,suffix in (('meshres',''),('meshres_vc','_VC'),('meshres_p0','_P0'),('meshres_p1','_P1')):
        path=f'Orbitersdk/samples/Lua/DeltaGlider/Src/{stem}.lua'
        reference=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]).replace(b'\r\n',b'\n')
        expected=values([(k.replace('GRP.','GRP_'),v) for k,v in re.findall(r'^module\.([\w.]+)\s*=\s*(\d+)\s*$',reference.decode(),re.M)])
        header=(args.headers/(stem+'.h')).read_text()
        actual=values([(k.removesuffix(suffix),v) for k,v in re.findall(r'^#define (\w+) (\d+)$',header,re.M)])
        if expected!=actual:
            raise ValueError(f'{stem}: original mesh counts or named group IDs differ')
        results[stem]=dict(definitions=len(actual),groups=int(actual['NGRP']),materials=int(actual['NMAT']),textures=int(actual['NTEX']),reference_sha256_lf=hashlib.sha256(reference).hexdigest())
    report=dict(status='passed',source=BASE,meshes=results)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
