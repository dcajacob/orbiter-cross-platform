#!/usr/bin/env python3
"""Locate first differing read-only math fields at exact common ticks and clocks."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open() as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    ticks=[int(row['tick']) for row in rows]
    if len(ticks)!=len(set(ticks)) or ticks!=sorted(ticks):raise ValueError('Unique ordered observed ticks required')
    for row in rows:
        if not all(math.isfinite(float(value)) for value in row.values()):raise ValueError('Nonfinite observed math field')
    return fields,{int(row['tick']):row for row in rows}


def bits(text):return struct.pack('>d',float(text)).hex()


def compare(windows,native,first=211,last=243):
    guarded={str(path):sha(path) for path in (windows,native)}
    fields,left=read(windows);right_fields,right=read(native)
    if fields!=right_fields:raise ValueError('Math observation field closure differs')
    common=sorted(set(left)&set(right))
    if not set(range(first,last+1))<=set(common):raise ValueError('Complete investigated common tick range required')
    differing={};window={}
    for tick in common:
        a,b=left[tick],right[tick]
        if float(a['seconds'])!=float(b['seconds']):raise ValueError('Observed finalized clocks differ at tick '+str(tick))
        changes={}
        for field in fields:
            if field in ('tick','seconds') or bits(a[field])==bits(b[field]):continue
            entry=dict(tick=tick,seconds=a['seconds'],windows=a[field],native=b[field],windows_bits=bits(a[field]),
                       native_bits=bits(b[field]),delta=float(b[field])-float(a[field]))
            differing.setdefault(field,entry);changes[field]=entry
        if first<=tick<=last:window[str(tick)]=changes
    if any(sha(Path(path))!=value for path,value in guarded.items()):raise ValueError('Math inputs changed during comparison')
    return dict(status='compared-read-only-math-diagnostic-only',common_ticks=[common[0],common[-1]],
        first_differing_fields=differing,investigation_window=window,evidence_sha256=guarded,
        simulator_acceptance=False,phase6_complete=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows',type=Path,required=True);parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh diagnostic comparison output required')
    result=compare(args.windows,args.native);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['first_differing_fields'],indent=2))
