#!/usr/bin/env python3
"""Read-only verification of preserved Windows planet/base client evidence."""
import hashlib
import json
from pathlib import Path
import zipfile
HERE=Path(__file__).resolve().parent
def verify():
    metadata=json.loads((HERE/'provenance.json').read_text())
    if metadata['automatic_refresh'] is not False:raise ValueError('Evidence must remain immutable')
    for artifact in metadata['artifacts']:
        path=HERE/artifact['filtered_file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=artifact['filtered_sha256']:raise ValueError('Evidence archive differs')
        with zipfile.ZipFile(path) as archive:
            for name,expected in artifact['members_sha256'].items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=expected:raise ValueError('Evidence member differs')
            if artifact['name']=='real-client-comparison':
                result=json.loads(archive.read('client-comparison.json'))
                for record in (result,result['frozen_debug'],result['frozen_release']):
                    if record['status']!='passed' or record['ssim']!=1 or record['maximum_projected_landmark_error_px']!=0:
                        raise ValueError('Accepted Windows client result differs')
    print('Preserved original Windows planet/base client evidence verified; not native graphics')
if __name__=='__main__':verify()
