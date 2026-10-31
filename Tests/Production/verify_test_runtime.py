#!/usr/bin/env python3
"""Reject mixed SDK/application artifacts before recompiling a test-only driver."""
import argparse
import json
from pathlib import Path
import subprocess
from mesa_runtime import digest,require


def verify_sources(source):
    names=subprocess.check_output(['git','ls-files','-z','Src','Orbitersdk/include',
        'Tests/Production/ApplicationObservation.cpp','Tests/Production/ApplicationObservation.h']).decode().split('\0')
    count=0
    # Keep one Git object reader alive. Thousands of separate git-show processes
    # dominate the Windows setup time and provide the same underlying bytes.
    with subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as reader:
        for name in filter(None,names):
            require('\n' not in name,'unsupported newline in source path')
            reader.stdin.write((source+':'+name+'\n').encode());reader.stdin.flush()
            header=reader.stdout.readline().split()
            require(len(header)==3 and header[1]==b'blob','missing frozen source blob: '+name)
            size=int(header[2]);original=reader.stdout.read(size)
            require(len(original)==size and reader.stdout.read(1)==b'\n','incomplete Git source blob: '+name)
            require(Path(name).read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),
                    'runtime needs a full rebuild after changing '+name)
            count+=1
        reader.stdin.close()
        require(reader.wait()==0,'Git source verification failed')
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--source',required=True)
    args=parser.parse_args()
    manifest=json.loads((args.runtime/'test-runtime.json').read_text())
    require(manifest['source_commit']==args.source,'wrong source-built application revision')
    for name,checksum in manifest['files'].items():
        require(digest(args.runtime/name)==checksum,'test runtime file changed: '+name)
    count=verify_sources(args.source)
    print('Verified complete application/SDK artifact and',count,'source files from',args.source)


if __name__=='__main__':main()
