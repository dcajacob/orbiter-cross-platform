#!/usr/bin/env python3
"""Download only the existing pinned renderer archives and verify every byte."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path,required=True);args=parser.parse_args();args.cache.mkdir(parents=True,exist_ok=True)
lock=json.loads((ROOT/'OVP/OGLClient/dependencies.lock.json').read_text())
lock['glfw']=dict(url='https://codeload.github.com/glfw/glfw/tar.gz/refs/tags/3.5.1',sha256='5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20')
for name,entry in lock.items():
    target=args.cache/(name+('.tar.gz' if name=='glfw' else '.zip'))
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:
        with urllib.request.urlopen(entry['url'],timeout=180) as incoming:payload=incoming.read()
        if hashlib.sha256(payload).hexdigest()!=entry['sha256'] or ('bytes' in entry and len(payload)!=entry['bytes']):raise ValueError('Pinned dependency differs: '+name)
        target.write_bytes(payload)
    print(name,entry['sha256'])
