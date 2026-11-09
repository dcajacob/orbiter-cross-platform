#!/usr/bin/env python3
"""Reuse every immutable C08 shader guard with an explicit new API diagnostic cell."""
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
ORIGINAL=ROOT/'Tests/Production/CurrentWindows/Hosted/current_client_shaders.py'
SHA256_LF='f8b3f24b7c87cc18aeb83c32ecaecfa18a74bc521e1bdb77373d2c3331b2ae67'


def prepared_body():
    body=ORIGINAL.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(body).hexdigest()!=SHA256_LF:raise ValueError('Original complete current shader reader changed')
    body=body.decode()
    changes=[
      ("PROTOCOL='phase6-current-same-source-renderer-shader-inputs-v1'","PROTOCOL='phase6-current-GeneralApi-same-source-shader-inputs-v1'"),
      ("cell in {configuration+'-'+m+'-'+p for m in ('automatic','sse2') for p in ('stock','reload')}","cell==configuration+'-GeneralApi'")]
    for before,after in changes:
        if body.count(before)!=1:raise ValueError('Original shader scope anchor changed')
        body=body.replace(before,after,1)
    return body

exec(compile(prepared_body(),str(Path(__file__)),'exec'),globals())
