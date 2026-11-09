#!/usr/bin/env python3
"""Keep original pinned data preparation and failed transport bytes in an API-only lane."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
ORIGINAL=ROOT/'Tests/Production/CurrentWindows/Hosted/prepare_current_data_retry.py'
SHA256_LF='60f16ab0212bc808dcec40ed1c072a5d80d6f55eb979466e9a3a0f81334de833'


def prepared_body():
    body=ORIGINAL.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(body).hexdigest()!=SHA256_LF:raise ValueError('Original pinned data helper changed')
    before="a.cell in {c+'-'+m+'-'+phase for c in ('Debug','Release') for m in ('automatic','sse2') for phase in ('stock','reload')}"
    body=body.decode()
    if body.count(before)!=1:raise ValueError('Original current data scope anchor changed')
    return body.replace(before,"a.cell in {c+'-GeneralApi' for c in ('Debug','Release')}",1)


if __name__=='__main__':
    import sys
    sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
    exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
