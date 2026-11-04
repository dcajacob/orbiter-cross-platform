"""Stage exact already-published original runtime, SDK and captured client bytes."""
import argparse,hashlib,io,json,shutil,sys,urllib.request,zipfile
from pathlib import Path,PurePosixPath
from common import HERE,ROOT,require,sha,settings
sys.path.insert(0,str(HERE.parent/'Cockpit'))
from frozen import metadata,RELEASE

def member(name):
    path=PurePosixPath(name)
    require(name and '\\' not in name and not path.is_absolute() and '..' not in path.parts and ':' not in name,'Unsafe original archive member')
    return path

def obtain(entry,cache):
    path=cache/(entry['name']+'.zip')
    if not path.exists():
        cache.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.partial')
        require(not temporary.exists(),'A prior partial original input must be inspected')
        with urllib.request.urlopen(RELEASE+path.name,timeout=120) as source,temporary.open('xb') as target:shutil.copyfileobj(source,target)
        require(temporary.stat().st_size==entry['size_bytes'] and sha(temporary)==entry['sha256'],'Downloaded frozen original archive differs')
        temporary.replace(path)
    require(path.stat().st_size==entry['size_bytes'] and sha(path)==entry['sha256'],'Cached frozen original archive differs')
    return path

def prepare(cache,destination,configuration):
    pins=metadata(HERE.parent/'Cockpit/Reference/provenance.json');require(pins['application_source']==settings()['application_source'],'Wrong preserved original application')
    runtime=obtain(pins['runtime_artifacts'][configuration],cache);client=obtain(pins['artifacts'][configuration],cache)
    require(not destination.exists(),'Fresh original runtime directory required');destination.mkdir(parents=True)
    with zipfile.ZipFile(runtime) as outer:
        require(outer.namelist()==['windows-test-runtime.zip'],'Unexpected accepted original runtime payload')
        with zipfile.ZipFile(io.BytesIO(outer.read('windows-test-runtime.zip'))) as archive:
            for info in archive.infolist():
                relative=member(info.filename)
                if info.is_dir():continue
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(info))
    manifest=json.loads((destination/'test-runtime.json').read_text());require(manifest['source_commit']==pins['application_source'],'Original runtime revision differs')
    require({p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}==set(manifest['files'])|{'test-runtime.json'},'Original runtime file closure differs')
    require(all(sha(destination/name)==value for name,value in manifest['files'].items()),'Original runtime/SDK file hash differs')
    client_files={}
    with zipfile.ZipFile(client) as archive:
        prefix='out/production-app/'
        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith(prefix):continue
            name=info.filename[len(prefix):]
            if name!='Modules/Plugin/OGLClient.dll' and not name.startswith('Modules/OGLClient/'):continue
            relative=member(name);raw=archive.read(info);value=hashlib.sha256(raw).hexdigest();target=destination/relative
            require(not target.exists() or sha(target)==value,'Original program/client payload collision')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);client_files[name]=value
    require('Modules/Plugin/OGLClient.dll' in client_files and len(client_files)>30,'Exact captured original client/resources incomplete')
    record=dict(status='verified-exact-frozen-original-runtime-sdk-client',application_source=pins['application_source'],configuration=configuration,runtime_archive_sha256=sha(runtime),client_archive_sha256=sha(client),runtime_manifest_sha256=sha(destination/'test-runtime.json'),original_client_files_sha256=client_files,frozen_reference_run=pins['run_id'])
    (destination/'named-original-inputs.json').write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args();print(json.dumps(prepare(a.cache,a.output,a.configuration),indent=2))
