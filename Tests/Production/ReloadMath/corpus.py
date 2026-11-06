#!/usr/bin/env python3
"""Extract exact captured arcsine inputs and adjacent values without altering simulation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--first-tick',type=int,default=211)
    parser.add_argument('--last-tick',type=int,default=243)
    parser.add_argument('--neighbours',type=int,default=32)
    args=parser.parse_args()
    if args.output.exists() or args.first_tick > args.last_tick or not 0 <= args.neighbours <= 1024:
        raise ValueError('Fresh output, ordered ticks and bounded neighbour count required')
    trace_sha=sha(args.trace)
    with args.trace.open() as stream:
        rows=[row for row in csv.DictReader(stream) if args.first_tick <= int(row['tick']) <= args.last_tick]
    if [int(row['tick']) for row in rows] != list(range(args.first_tick,args.last_tick+1)):
        raise ValueError('Complete exact tick range required')
    values=[];captured=[]
    for row in rows:
        x=float(row['nz'])
        if not math.isfinite(x) or abs(x)>1:raise ValueError('Invalid observed arcsine input')
        captured.append(dict(tick=int(row['tick']),input_bits=struct.pack('>d',x).hex(),
                             captured_asin_bits=struct.pack('>d',float(row['asin_nz'])).hex(),
                             rounding=int(row['rounding']),mxcsr_control=int(row['mxcsr_control'])))
        values.append(x)
        for direction in (-math.inf,math.inf):
            neighbour=x
            for _ in range(args.neighbours):
                neighbour=math.nextafter(neighbour,direction)
                if abs(neighbour)<=1:values.append(neighbour)
    inputs=list(dict.fromkeys(struct.pack('>d',x).hex() for x in values))
    args.output.mkdir(parents=True)
    path=args.output/'inputs.txt';path.write_text('\n'.join(inputs)+'\n',encoding='ascii')
    result=dict(status='prepared-observed-input-diagnostic-corpus',trace=str(args.trace.resolve()),
        trace_sha256=trace_sha,input_sha256=sha(path),first_tick=args.first_tick,last_tick=args.last_tick,
        neighbours=args.neighbours,captured=captured,samples=len(inputs),
        scope='Math observer nz/asin only; these inputs do not establish the first differing physics operation.',
        simulator_acceptance=False,phase6_complete=False)
    if sha(args.trace)!=trace_sha:raise ValueError('Captured trace changed')
    (args.output/'corpus.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(inputs),'captured and neighbouring inputs prepared')


if __name__=='__main__':main()
