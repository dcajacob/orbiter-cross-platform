"""Losslessly retain all logical rejection files and guards while sharing existing hardlinks."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import stat
import tarfile
from contracts import require,atomic_json


def safe(name):
    p=PurePosixPath(name)
    require(name and str(p)==name and not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name,
            'Canonical relative original input path required')
    return p


def digest_file(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def inventory(root,paths):
    root=Path(root).resolve();pending=list(paths);files={};seen=set();cache={};missing=[]
    while pending:
        path=Path(pending.pop());require(path.is_absolute() and path.is_relative_to(root),'Every guarded file must remain inside its actual repository root')
        name=path.relative_to(root).as_posix();safe(name)
        if name in files:continue
        require(name.casefold() not in seen,'Case-colliding original logical input');seen.add(name.casefold())
        if not path.exists() and not path.is_symlink():missing.append(name);continue
        require(path.resolve().is_relative_to(root),'Original symbolic input cannot escape its actual root')
        state=path.lstat();require(not state.st_mode&0o7000 and (stat.S_ISREG(state.st_mode) or stat.S_ISLNK(state.st_mode)),
            'Only original regular files and within-root file aliases may be preserved')
        actual=path.stat();require(stat.S_ISREG(actual.st_mode),'Original input alias must resolve to a regular file')
        token=(actual.st_dev,actual.st_ino,actual.st_size,actual.st_mtime_ns,actual.st_ctime_ns)
        if token not in cache:cache[token]=digest_file(path)
        value=dict(sha256=cache[token],bytes=actual.st_size,mode=state.st_mode&0o777,kind='symlink' if path.is_symlink() else 'file')
        if path.is_symlink():
            value['target']=os.readlink(path);value['resolved_target']=path.resolve().relative_to(root).as_posix();pending.append(path.resolve())
        files[name]=value
    return files,sorted(missing)


def inspect_archive(archive,expected):
    seen=set();seen_folded=set();logical={}
    with tarfile.open(archive,'r:gz') as incoming:
        for entry in incoming:
            name=entry.name;safe(name)
            require(name in expected and name not in seen and name.casefold() not in seen_folded and
                    not entry.mode&0o7000 and entry.mode==expected[name]['mode'],'Every exact original member/type/mode required')
            seen.add(name);seen_folded.add(name.casefold());value=expected[name]
            if entry.isfile():
                require(value['kind']=='file' and entry.size==value['bytes'],'Complete original regular file length required')
                h=hashlib.sha256();stream=incoming.extractfile(entry)
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
                require(h.hexdigest()==value['sha256'],'Original regular input byte digest differs');logical[name]=value['sha256']
            elif entry.islnk():
                safe(entry.linkname);require(value['kind']=='file' and entry.linkname in logical and logical[entry.linkname]==value['sha256'] and
                    expected[entry.linkname]['bytes']==value['bytes'],'Lossless original hardlink target and bytes required');logical[name]=value['sha256']
            elif entry.issym():
                safe(value['resolved_target']);require(value['kind']=='symlink' and entry.linkname==value['target'] and value['resolved_target'] in expected and
                    expected[value['resolved_target']]['kind']=='file' and expected[value['resolved_target']]['sha256']==value['sha256'] and
                    expected[value['resolved_target']]['bytes']==value['bytes'],'Exact original symbolic alias and actual target byte identity required')
                logical[name]=value['sha256']
            else:raise ValueError('Unaccepted original input archive member type')
    require(seen==set(expected),'No original logical member may be omitted or invented')
    return dict(logical_files=len(seen),logical_bytes=sum(v['bytes'] for v in expected.values()),all_logical_names_types_lengths_and_digests_preserved=True)


def pack(root,paths,archive,index):
    root=Path(root).resolve();archive=Path(archive);index=Path(index)
    require(not archive.exists() and not index.exists() and not archive.is_relative_to(root/'Tests'),'Fresh separate original evidence bundle required')
    files,missing=inventory(root,paths);require(files,'No empty original rejection bundle');archive.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,'w:gz',compresslevel=3,dereference=False) as outgoing:
        for name in sorted(files):outgoing.add(root/name,arcname=name,recursive=False)
    closure=inspect_archive(archive,files)
    require(inventory(root,[root/name for name in files])[0]==files,'Any original byte/alias changed during packing')
    record=dict(protocol='phase6-lossless-original-rejection-input-bundle-v1',status='preserved-original-files-only-not-qualified',
        source_root=str(root),files=files,missing_guarded_paths=missing,archive_bytes=archive.stat().st_size,
        archive_sha256=digest_file(archive),closure=closure,original_files_rewritten=False,
        source_and_runtime_rejection_audits_still_required=True,phase6_complete=False,hands_on_ready=False)
    atomic_json(index,record);return record
