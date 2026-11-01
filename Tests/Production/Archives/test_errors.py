#!/usr/bin/env python3
"""Exercise corrupt disk records and payloads in the actual shared reader."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from observations import fixtures,require

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path,required=True)
    args=parser.parse_args()
    count=0
    with tempfile.TemporaryDirectory(prefix='orbiter-archive-errors-') as temporary:
        root=Path(temporary)
        _,original,_,_=fixtures(root/'inputs')[0]
        data=original.read_bytes()
        def run(name,content,mode):
            nonlocal count
            directory=root/name;path=directory/'Archive'/'Surf.tree'
            path.parent.mkdir(parents=True)
            if content is not None:path.write_bytes(content)
            result=subprocess.run([str(args.executable.resolve()),str(directory),mode],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
            require(result.returncode==0,name+': '+result.stdout.decode(errors='replace'))
            count+=1
        run('valid',data,'valid');run('missing',None,'closed')
        for size in range(48):run('header-'+str(size),data[:size],'closed')
        def changed(offset,value,fmt='<I'):
            modified=bytearray(data);struct.pack_into(fmt,modified,offset,value);return modified
        for name,offset,value,fmt in [
            ('magic',0,0,'<I'),('version',2,2,'<B'),('header-size',4,47,'<I'),('flags',8,2,'<I'),
            ('data-offset',12,47,'<I'),('data-length',16,-1,'<q'),('huge-length',16,0x7fffffffffffffff,'<q'),
            ('huge-count',24,0xffffffff,'<I'),('root-index',28,9,'<I'),('child-index',48+12,9,'<I'),
            ('self-cycle',48+12,0,'<I'),('negative-position',48,-1,'<q'),
            ('out-of-data',48,len(data),'<q'),('zero-compressed',48+32,0,'<q')]:run(name,changed(offset,value,fmt),'closed')
        cycle=changed(48+12,1);struct.pack_into('<I',cycle,48+32+12,0)
        run('graph-cycle',cycle,'closed')
        start=struct.unpack_from('<I',data,12)[0];corrupt=bytearray(data);corrupt[start]=0
        run('corrupt-zlib',corrupt,'corrupt');run('wrong-inflated',changed(48+8,8197),'corrupt')
        next_position=struct.unpack_from('<q',data,48+32)[0]
        run('trailing-compressed',changed(48+32,next_position+1,'<q'),'corrupt')
        run('short-file',data[:-1],'closed');run('truncate-after-open',data,'truncated')
    print('Passed',count,'archive validity/failure/resource cases')

if __name__=='__main__':main()
