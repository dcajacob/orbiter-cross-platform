#!/usr/bin/env python3
"""Reject mixed SDK/application artifacts before recompiling a test-only driver."""
import argparse
import json
from pathlib import Path
import subprocess
from mesa_runtime import digest,require

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime',type=Path,required=True)
parser.add_argument('--source',required=True)
args=parser.parse_args()
manifest=json.loads((args.runtime/'test-runtime.json').read_text())
require(manifest['source_commit']==args.source,'wrong source-built application revision')
for name,checksum in manifest['files'].items():
    require(digest(args.runtime/name)==checksum,'test runtime file changed: '+name)
# Core observation blocks and SDK headers must be exactly the runtime's sources.
for name in subprocess.check_output(['git','ls-files','Src','Orbitersdk/include','Tests/Production/ApplicationObservation.cpp','Tests/Production/ApplicationObservation.h']).decode().splitlines():
    original=subprocess.check_output(['git','show',args.source+':'+name]).replace(b'\r\n',b'\n')
    require(Path(name).read_bytes().replace(b'\r\n',b'\n')==original,'runtime needs a full rebuild after changing '+name)
print('Verified complete application/SDK artifact from',args.source)
