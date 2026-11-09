"""Read exact immutable current Windows failed process output; never rerun a simulator."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,stat,zipfile
base=Path('out/current-startup-source');dest=Path('out/current-startup-diagnostic');assert not dest.exists();dest.mkdir(parents=True)
result={'status':'retained-failed-current-process-text-only','verifier_source':os.environ['GITHUB_SHA'],'simulator_executed':False,'qualification_granted':False,'artifacts':{}}
for archive in sorted(base.glob('*.zip')):
    cell=archive.stem;api=json.loads((base/(cell+'.api.json')).read_text());artifact=api['artifact']
    assert archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+hashlib.sha256(archive.read_bytes()).hexdigest()==artifact['digest']
    checked={};selected={};print('CELL '+cell,flush=True)
    with zipfile.ZipFile(archive) as source:
        seen=set()
        for entry in source.infolist():
            name=entry.filename;path=PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\\\' not in name and not stat.S_ISLNK(entry.external_attr>>16)
            assert name.casefold() not in seen;seen.add(name.casefold())
            if entry.is_dir():continue
            checked[name]={'bytes':entry.file_size}
            lower=path.name.lower()
            if lower.endswith(('.log','.txt')) or lower in {'process-result.json','process-timing.json','invocation.json','graphics-lifecycle.json','scene-summary.json','resource-history.json'}:
                assert entry.file_size<16*1024**2
                body=source.read(entry);target=dest/cell/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
                selected[name]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
                print('FILE '+cell+'/'+name+'\n'+body.decode('utf-8',errors='replace')[-24000:],flush=True)
    assert selected
    result['artifacts'][cell]={'api':api,'archive_sha256':artifact['digest'],'all_member_inventory':checked,'selected_raw_text':selected}
(dest/'index.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)
