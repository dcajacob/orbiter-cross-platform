"""Byte witnesses for the actual original simulation data and planet archives."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
LOCKS=(('stock-data.lock.json',('Kernels/','GravityModels/')),
       ('standard-planets.lock.json',('Textures/',)))


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def expected():
    result={};locks={}
    for filename,prefixes in LOCKS:
        body=(ROOT/'Tests/Production'/filename).read_bytes()
        locks[filename]=hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()
        selected={name:value for name,value in json.loads(body)['data_files'].items() if name.startswith(prefixes)}
        require(not set(result)&set(selected),'Ambiguous original data delivery path');result.update(selected)
    require(len(result)==57,'Original kernel/gravity/planet input closure differs')
    return dict(schema=1,lock_sha256_lf=locks,files=result)


def inspect(data,planets):
    result=expected();actual={}
    planet_files=json.loads((ROOT/'Tests/Production/standard-planets.lock.json').read_text())['data_files']
    for name,value in result['files'].items():
        path=(planets if name in planet_files else data)/name
        actual[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
        require(actual[name]==value,'Actual original simulation data changed: '+str(path))
    result['files']=actual
    return result


def validate(record):
    require(record==expected(),'Actual kernel/gravity/planet byte witnesses differ from original locks')
    return len(record['files'])
