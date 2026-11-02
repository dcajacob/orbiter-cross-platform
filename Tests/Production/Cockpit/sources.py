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
        if a.current and hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=digest:raise ValueError('Current cockpit source changed before reference capture: '+name)
    print('Verified',len(lock['files']),'original cockpit/DG sources'+(' and unchanged current owners' if a.current else ''))
if __name__=='__main__':main()
