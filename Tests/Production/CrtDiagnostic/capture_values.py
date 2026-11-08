#!/usr/bin/env python3
"""Observe typed elementary-math exports on exact inputs in the local Windows process."""
import argparse
import csv
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import sys

ARITY={'asin':1,'acos':1,'sin':1,'cos':1,'sqrt':1,'exp':1,'atan2':2,'hypot':2,'pow':2}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def number(text):return struct.unpack('>d',bytes.fromhex(text))[0]
def bits(value):return struct.pack('>d',value).hex()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--provider',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if sys.platform!='win32' or a.output.exists():raise ValueError('Windows and fresh primitive output required')
    with a.inputs.open() as stream:rows=list(csv.DictReader(stream))
    if not rows or any(r['function'] not in ARITY for r in rows):raise ValueError('Known nonempty elementary-math input set required')
    a.output.mkdir();lib=C.CDLL(str(a.provider));get=lib._get_FMA3_enable;get.restype=C.c_int
    set_fma=lib._set_FMA3_enable;set_fma.argtypes=[C.c_int];set_fma.restype=C.c_int
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.GetModuleHandleExW.argtypes=[C.c_uint,C.c_void_p,C.POINTER(C.c_void_p)]
    kernel.GetModuleHandleExW.restype=C.c_int;kernel.GetModuleFileNameW.argtypes=[C.c_void_p,C.c_wchar_p,C.c_uint]
    functions={};providers={}
    for name in {r['function'] for r in rows}:
        fn=getattr(lib,name);fn.restype=C.c_double;fn.argtypes=[C.c_double]*ARITY[name];functions[name]=fn
        handle=C.c_void_p()
        if not kernel.GetModuleHandleExW(6,C.cast(fn,C.c_void_p),C.byref(handle)):raise C.WinError(C.get_last_error())
        path=C.create_unicode_buffer(32768)
        if not kernel.GetModuleFileNameW(handle,path,len(path)):raise C.WinError(C.get_last_error())
        providers[name]=dict(actual_owner_path=path.value,sha256=sha(path.value))
    initial=get();report=dict(status='running',inputs_sha256=sha(a.inputs),requested_provider=str(a.provider),
        requested_provider_sha256=sha(a.provider),providers=providers,initial_fma3=initial,profiles={},
        purpose='Typed direct CRT exports only; no simulator acceptance',phase6_complete=False)
    try:
        for profile in ('default','sse2'):
            if profile=='sse2':set_fma(0)
            active=get();count=0
            if profile=='default' and active!=initial:raise ValueError('Default FMA state changed')
            path=a.output/(profile+'.csv')
            with path.open('w',newline='') as stream:
                out=csv.DictWriter(stream,fieldnames=['tag','function','x','y','result']);out.writeheader()
                for row in rows:
                    args=[number(row['x'])]
                    if ARITY[row['function']]==2:args.append(number(row['y']))
                    value=functions[row['function']](*args)
                    out.writerow({k:row[k] for k in ('tag','function','x','y')}|dict(result=bits(value)));count+=1
            report['profiles'][profile]=dict(samples=count,active_fma3=active,output_sha256=sha(path))
        report['status']='observed-elementary-exports-only'
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:
        set_fma(initial)
        report['fma3_restored']=get()==initial
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
