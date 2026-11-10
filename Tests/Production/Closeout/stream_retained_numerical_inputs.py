"""Verify all original raw bytes; materialize only inputs the unchanged auditor opens."""
import hashlib
import posixpath
from pathlib import Path
import shutil
import tarfile
from contracts import require,sha
import rejection_input_bundle as bundle
import restore_rejection_input_bundle as restore

RESERVE=8*1024**3


class MeasuredStream:
    def __init__(self,source):self.source=source;self.digest=hashlib.sha256();self.bytes=0
    def read(self,count=-1):
        body=self.source.read(count);self.digest.update(body);self.bytes+=len(body);return body


def verify(root,compressed,index,selected,objects,reserve=RESERVE):
    root=Path(root).resolve();selected=set(selected);objects=Path(objects)
    require(index['protocol']=='phase6-lossless-original-rejection-input-bundle-v1' and index['status']=='preserved-original-files-only-not-qualified' and index['source_root']==str(root) and index['original_files_rewritten'] is False and index['source_and_runtime_rejection_audits_still_required'] is True and index['missing_guarded_paths']==[],'Complete original exact raw bundle required')
    expected=index['files'];require(0<len(expected)<300000 and selected and selected<=set(expected) and not objects.exists() and objects.is_relative_to(root/'out'),'Fresh separate bounded original file restoration required')
    require(reserve==RESERVE,'Original eight-GiB reserve may not be reduced')
    for n,v in expected.items():
        path=bundle.safe(n);restore.checked_path(root,n)
        require(v['kind'] in ('file','symlink') and type(v['bytes']) is int and v['bytes']>=0 and type(v['mode']) is int and 0<=v['mode']<=0o777 and len(v['sha256'])==64 and all(c in '0123456789abcdef' for c in v['sha256']),'Every actual original type/mode/length/hash required')
        require(all(str(p) not in expected for p in path.parents),'Original file path cannot also be an original directory')
        if path.parts[0]!='out':require(restore.check_existing(root,n,v),'Every original immutable source must already exist unchanged')
    require(all(expected[n]['kind']=='file' and bundle.safe(n).parts[0]=='out' for n in selected),'Only the exact auditor raw file inputs may be materialized')
    keys={(expected[n]['sha256'],expected[n]['bytes']) for n in selected};objects.mkdir(parents=True)
    stream=MeasuredStream(compressed);seen={};folded=set();groups={};objects_by_group={};alias_count=0
    with tarfile.open(fileobj=stream,mode='r|gz') as incoming:
        for entry in incoming:
            n=entry.name;bundle.safe(n);require(n in expected and n.casefold() not in folded and not entry.mode&0o7000 and entry.mode==expected[n]['mode'],'Every exact original raw member/type/mode required');folded.add(n.casefold());v=expected[n]
            if entry.isfile():
                require(v['kind']=='file' and entry.size==v['bytes'],'Every actual original regular body length required');actual=hashlib.sha256();length=0;dest=None
                if (v['sha256'],v['bytes']) in keys:
                    require(shutil.disk_usage(objects).free>=entry.size+RESERVE,'Exact original audit inputs must retain the unchanged eight-GiB reserve')
                    path=objects/('object-'+str(len(objects_by_group)));dest=path.open('xb');objects_by_group[n]=path
                try:
                    with incoming.extractfile(entry) as source:
                        for body in iter(lambda:source.read(1024*1024),b''):
                            actual.update(body);length+=len(body)
                            if dest:dest.write(body)
                finally:
                    if dest:dest.close();objects_by_group[n].chmod(v['mode'])
                require(length==v['bytes'] and actual.hexdigest()==v['sha256'],'Actual original regular raw bytes differ: '+n);groups[n]=n
            elif entry.islnk():
                bundle.safe(entry.linkname);require(v['kind']=='file' and entry.linkname in groups and seen[entry.linkname]==v['sha256'] and expected[entry.linkname]['bytes']==v['bytes'] and expected[entry.linkname]['mode']==v['mode'],'Original hardlink target and complete verified bytes required');groups[n]=groups[entry.linkname];alias_count+=1
            elif entry.issym():
                target=v['resolved_target'];bundle.safe(target);require(v['kind']=='symlink' and entry.linkname==v['target'] and target in expected and expected[target]['kind']=='file' and expected[target]['sha256']==v['sha256'] and expected[target]['bytes']==v['bytes'],'Every exact original symbolic alias/target body required');alias_count+=1
            else:raise ValueError('Unsupported original raw member type')
            seen[n]=v['sha256']
    while stream.read(1024*1024):pass
    require(set(seen)==set(expected) and stream.bytes==index['archive_bytes'] and stream.digest.hexdigest()==index['archive_sha256'],'Every actual original compressed/raw byte and logical member required')
    closure=dict(logical_files=len(seen),logical_bytes=sum(v['bytes'] for v in expected.values()),all_logical_names_types_lengths_and_digests_preserved=True);require(closure==index['closure'],'Exact original full logical closure required')
    for n,v in expected.items():
        if v['kind']!='symlink':continue
        target=n;visited=set()
        while expected[target]['kind']=='symlink':
            require(target not in visited,'Original symbolic alias cycle');visited.add(target);value=expected[target]['target']
            if value.startswith('/'):
                require(value.startswith(str(root)+'/'),'Original absolute alias cannot escape the source root');value=value[len(str(root))+1:]
            else:value=posixpath.join(posixpath.dirname(target),value)
            target=posixpath.normpath(value);bundle.safe(target);require(target in expected,'Every original symbolic target must be retained')
        require(target==v['resolved_target'],'Original symbolic resolution differs from its actual retained owner')
    for n in sorted(selected):
        target=restore.checked_path(root,n);require(not target.exists() and not target.is_symlink(),'Original auditor input cannot overwrite another file');target.parent.mkdir(parents=True,exist_ok=True);origin=objects_by_group[groups[n]]
        require(origin.stat().st_mode&0o777==expected[n]['mode'],'Actual original materialized hardlink mode differs');target.hardlink_to(origin)
        require(restore.check_existing(root,n,expected[n]),'Actual original auditor file bytes/mode changed')
    require(shutil.disk_usage(objects).free>=RESERVE,'Original eight-GiB reserve must remain available')
    return seen,dict(**closure,all_original_file_aliases_verified=alias_count,actual_auditor_inputs_materialized=len(selected),original_large_unused_input_bytes_stream_verified=True,full_original_archive_remains_published=True,original_raw_bundle_sha256=stream.digest.hexdigest(),original_raw_bundle_bytes=stream.bytes,restore_reserve_bytes=RESERVE,new_simulator_processes=0)
