#!/usr/bin/env python3
"""Check actual original-package delivery metadata and reject damaged copies."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

import audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('preserved','runtime','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();audit.require(not a.output.exists(),'Fresh original metadata control output required')
    original=audit.preserved(a.preserved)
    positive=audit.preserved_metadata(a.preserved,a.runtime)
    controls=[];names=('test-runtime.json','control-reference-runtime.json')
    with tempfile.TemporaryDirectory(prefix='orbiter-original-metadata-') as temporary:
        base=Path(temporary)
        for newline in ('lf','crlf'):
            folder=base/newline;folder.mkdir()
            for name in names:shutil.copy2(a.runtime/name,folder/name)
            path=folder/names[1];body=path.read_bytes().replace(b'\r\n',b'\n')
            path.write_bytes(body if newline=='lf' else body.replace(b'\n',b'\r\n'))
            audit.preserved_metadata(a.preserved,folder)
        for damage in ('changed_client_archive_hash','changed_runtime_archive_hash','extra_report_whitespace',
                       'reordered_report','mixed_report_newlines','changed_original_manifest',
                       'changed_original_manifest_newlines','missing_metadata'):
            folder=base/damage;folder.mkdir()
            for name in names:shutil.copy2(a.runtime/name,folder/name)
            path=folder/names[1];body=path.read_bytes().replace(b'\r\n',b'\n')
            if damage in ('changed_client_archive_hash','changed_runtime_archive_hash'):
                value=json.loads(body);key='client_archive_sha256' if damage.startswith('changed_client') else 'runtime_archive_sha256'
                value[key]='0'*64;path.write_text(json.dumps(value,indent=2)+'\n')
            elif damage=='extra_report_whitespace':path.write_bytes(body+b'\n')
            elif damage=='reordered_report':path.write_text(json.dumps(json.loads(body),indent=2,sort_keys=True)+'\n')
            elif damage=='mixed_report_newlines':path.write_bytes(body.replace(b'\n',b'\r\n',1))
            elif damage=='changed_original_manifest':
                path=folder/names[0];value=json.loads(path.read_text());value['source_commit']='0'*40
                path.write_text(json.dumps(value,indent=2)+'\n')
            elif damage=='changed_original_manifest_newlines':
                path=folder/names[0];body=path.read_bytes();lf=body.replace(b'\r\n',b'\n')
                path.write_bytes(lf if body!=lf else lf.replace(b'\n',b'\r\n'))
            else:path.unlink()
            try:audit.preserved_metadata(a.preserved,folder)
            except (ValueError,OSError) as error:controls.append(dict(control=damage,reason=str(error)))
            else:raise ValueError('Damaged original delivery metadata accepted: '+damage)
    audit.require(audit.preserved(a.preserved)==original and audit.preserved_metadata(a.preserved,a.runtime)==positive,
                  'Actual retained package or delivered metadata changed')
    a.output.write_text(json.dumps(dict(status='passed',actual_original_files_verified=len(original),positive=positive,
        controls=controls,owning_package_and_metadata_unchanged=True,source_sha256=audit.sha(Path(__file__)),
        reader_sha256=audit.sha(Path(audit.__file__))),indent=2)+'\n')
    print('Actual original payload verified; LF/CRLF report delivery accepted; eight damaged metadata copies rejected')


if __name__=='__main__':main()
