#!/usr/bin/env python3
"""Stage exact preserved pre-extraction application/SDK/client binaries."""
import argparse,hashlib,io,json,shutil,sys,zipfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent)]
from frozen import metadata,obtain
from mesa_runtime import require,digest

def extract(archive,output):
    for item in archive.infolist():
        if item.is_dir():continue
        name=PurePosixPath(item.filename)
        require(not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename and ':' not in item.filename,'Invalid preserved runtime path')
        target=output.joinpath(*name.parts);require(output.resolve() in target.resolve().parents,'Preserved runtime path escaped output')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(item))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--offline',action='store_true')
    a=p.parse_args();pins=metadata(HERE.parent/'Cockpit/Reference/provenance.json')
    require(not a.output.exists(),'Pre-extraction runtime output exists; replacement is forbidden')
    runtime=obtain(pins['runtime_artifacts'][a.configuration],a.cache,a.offline)
    client=obtain(pins['artifacts'][a.configuration],a.cache,a.offline)
    with zipfile.ZipFile(runtime) as archive:
        names=[name for name in archive.namelist() if PurePosixPath(name).name=='windows-test-runtime.zip']
        require(len(names)==1,'Preserved runtime artifact layout differs')
        payload=archive.read(names[0])
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:extract(archive,a.output)
    record=json.loads((a.output/'test-runtime.json').read_text())
    require(record['source_commit']==pins['application_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37','Wrong pre-extraction application/SDK')
    for name,checksum in record['files'].items():require(digest(a.output/name)==checksum,'Preserved application/SDK file differs: '+name)
    actual={p.relative_to(a.output).as_posix() for p in a.output.rglob('*') if p.is_file()}
    require(actual==set(record['files'])|{'test-runtime.json'},'Unmanifested preserved runtime files')
    copied={}
    with zipfile.ZipFile(client) as archive:
        for name in archive.namelist():
            prefix='out/production-app/'
            if not name.startswith(prefix) or name.endswith('/'):continue
            relative=name[len(prefix):]
            if relative=='Modules/Plugin/OGLClient.dll' or relative.startswith('Modules/OGLClient/'):
                target=a.output/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name));copied[relative]=digest(target)
    require('Modules/Plugin/OGLClient.dll' in copied and len(copied)>10,'Exact preserved original client/shaders missing')
    report=dict(schema=1,application_source=pins['application_source'],client_source=pins['source_commit'],reference_run=pins['run_id'],
        runtime_archive_sha256=digest(runtime),runtime_payload_sha256=hashlib.sha256(payload).hexdigest(),client_archive_sha256=digest(client),client_files_sha256=copied)
    (a.output/'control-reference-runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified exact preserved pre-extraction Windows application, SDK, real graphics client and shaders')
if __name__=='__main__':main()
