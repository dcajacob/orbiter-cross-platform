#!/usr/bin/env python3
"""Verify the additional original Windows upright-landing reference; never refresh it."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.dont_write_bytecode=True;sys.path.insert(0,str(HERE.parent))
from mesa_runtime import require,digest
def verify(directory=None):
    directory=directory or HERE.parent/'ControlledReference';p=json.loads((directory/'provenance.json').read_text())
    require(p['automatic_refresh'] is False and p['run_id']==41374941546 and p['application_source']=='391919027ac3e4a4d42f145373c788fc859c32cd','Wrong original controlled-landing reference')
    for name,checksum in p['input_sha256_lf'].items():
        require(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==checksum,'Controlled-landing source input changed: '+name)
    for configuration,record in p['artifacts'].items():
        require(digest(directory/record['path'])==record['sha256'],'Controlled-landing archive changed')
        with zipfile.ZipFile(directory/record['path']) as archive:
            require(set(archive.namelist())==set(p['members'][configuration]),'Controlled-landing member set changed')
            for name,checksum in p['members'][configuration].items():require(hashlib.sha256(archive.read(name)).hexdigest()==checksum,'Original captured member changed: '+name)
            if configuration=='comparison':
                require(json.loads(archive.read('controlled-landing-report.json'))['status']=='passed original Windows cross-configuration qualification','Original Windows cross-configuration qualification failed')
            else:
                for name,checksum in p['repeat_sha256'][configuration].items():
                    require(hashlib.sha256(archive.read('production-behavior/controlled-landing/'+name)).hexdigest()==checksum,'Controlled-landing repeat proof changed')
    return p
if __name__=='__main__':print('Verified original Windows controlled upright landing:',verify()['run_id'])
