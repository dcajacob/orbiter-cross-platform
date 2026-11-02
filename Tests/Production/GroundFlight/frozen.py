#!/usr/bin/env python3
"""Verify immutable original Windows ground-flight traces; never regenerate them."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE.parent))
from mesa_runtime import require,digest
def verify(directory=None):
    directory=directory or HERE.parent/'GroundReference'
    p=json.loads((directory/'provenance.json').read_text())
    require(p['automatic_refresh'] is False and p['status']=='accepted Windows ground-flight reference',
            'Ground-flight reference was not accepted')
    require(p['run_id']==41368023101 and p['application_source']=='391919027ac3e4a4d42f145373c788fc859c32cd',
            'Wrong original Windows reference application/capture')
    for name,checksum in p['input_sha256_lf'].items():
        actual=hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        require(actual==checksum,'Frozen ground-flight source input changed: '+name)
    for key,record in p['artifacts'].items():
        path=directory/record['path'];require(digest(path)==record['sha256'],'Frozen ground-flight artifact changed: '+key)
        with zipfile.ZipFile(path) as archive:
            if key=='comparison':
                report=json.loads(archive.read('ground-flight-comparison.json'))
                require(report['status']=='passed' and len(report['cases'])==7,'Hosted Windows comparison did not pass')
                continue
            require(set(archive.namelist())==set(p['canonical_members'][key]),'Frozen canonical member set changed')
            for name,checksum in p['canonical_members'][key].items():
                require(hashlib.sha256(archive.read(name)).hexdigest()==checksum,'Original captured member changed: '+name)
            for case,files in p['repeat_sha256'][key].items():
                for name,checksum in files.items():
                    require(hashlib.sha256(archive.read(f'production-behavior/{case}/{name}')).hexdigest()==checksum,
                            'Frozen repeat proof differs: '+case+'/'+name)
    return p
if __name__=='__main__':
    result=verify();print('Verified original Windows ground-flight reference:',result['run_id'],'seven cases, both configurations')
