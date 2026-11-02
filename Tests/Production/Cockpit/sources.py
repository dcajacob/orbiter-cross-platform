#!/usr/bin/env python3
"""Verify preserved pre-extraction cockpit/DG owning sources, never refresh pins."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--current',action='store_true',help='Also require current owning sources to be unchanged, before extraction');a=p.parse_args()
    lock=json.loads(Path(__file__).with_name('source.lock.json').read_text())
    for name,digest in lock['files'].items():
        original=subprocess.check_output(['git','-C',str(ROOT),'show',lock['source']+':'+name]).replace(b'\r\n',b'\n')
        if hashlib.sha256(original).hexdigest()!=digest:raise ValueError('Original cockpit source pin differs: '+name)
        if a.current:
            current=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            if name in lock.get('pre_reference_repairs',{}):
                repair=lock['pre_reference_repairs'][name]
                if hashlib.sha256(current).hexdigest()!=repair['sha256']:raise ValueError('Declared pre-reference repair changed: '+name)
                added=repair['added_line'].encode()
                if current.count(added)!=1 or current.replace(added,b'',1)!=original:raise ValueError('Pre-reference repair exceeds its declared initialization: '+name)
            elif hashlib.sha256(current).hexdigest()!=digest:raise ValueError('Current cockpit source changed before reference capture: '+name)
    print('Verified',len(lock['files']),'original cockpit/DG sources'+(' and exact declared pre-reference repairs' if a.current and lock.get('pre_reference_repairs') else ' and unchanged current owners' if a.current else ''))
if __name__=='__main__':main()
