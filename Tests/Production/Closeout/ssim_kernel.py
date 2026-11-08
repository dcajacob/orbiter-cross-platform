"""Bind a verified scalar SSIM kernel; the retained Python reader stays intact."""
import inspect
import math
from pathlib import Path
import struct
import subprocess
from contracts import load,require,sha


def compare(executable,left,right,width,height):
    require(len(left)==len(right)==width*height*4 and 11<=width<=16384 and 11<=height<=16384,
            'Invalid complete RGBA dimensions')
    if left==right:return 1.0
    weights=[math.exp(-i*i/(2*1.5**2)) for i in range(-5,6)]
    total=sum(weights);weights=[v/total for v in weights]
    data=struct.pack('=II13d',width,height,*weights,(.01*255)**2,(.03*255)**2)+left+right
    result=subprocess.run([str(executable)],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=True,timeout=60)
    value=float.fromhex(result.stdout.decode().strip())
    require(math.isfinite(value),'Nonfinite SSIM result')
    return value


def bind(path,expected_sha256,reference):
    path=Path(path).resolve();require(sha(path)==expected_sha256,'SSIM verification record changed')
    record=load(path)
    require(record['status']=='verified-bit-identical-to-retained-python-ssim' and
            record['full_frame_pairs']==2 and record['small_control_pairs']==5 and
            all(v['actual_hex']==v['reference_hex'] for v in record['comparisons']) and
            all(sha(p)==v for p,v in record['guarded_files_sha256'].items()),
            'Complete unchanged SSIM kernel/reference/input equivalence required')
    executable=Path(record['executable'])
    require(sha(inspect.getsourcefile(reference))==record['reference_reader_sha256'],
            'Verified SSIM reference differs from the owning comparison reader')
    require(record['guarded_files_sha256'].get(str(executable))==sha(executable) and
            record['guarded_files_sha256'].get(str(Path(__file__).resolve()))==sha(__file__) and
            record['guarded_files_sha256'].get(str(Path(__file__).with_suffix('.cpp').resolve()))==
            sha(Path(__file__).with_suffix('.cpp')),'Verified SSIM implementation binding missing')
    def image_ssim(left,right,width,height):return compare(executable,left,right,width,height)
    return image_ssim,dict(verification=str(path),verification_sha256=expected_sha256,
                          executable=str(executable),executable_sha256=sha(executable),
                          arithmetic='retained Python scalar order, exact supplied binary64 weights/constants',
                          masks=False,rescaling=False,budgets_changed=False)
