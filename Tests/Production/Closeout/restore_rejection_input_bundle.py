"""Restore exact published rejection bytes, original aliases and recorded file-table membership on hosted workers."""
import hashlib
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import tarfile
from contracts import require
import rejection_input_bundle as original


def checked_path(root,name):
    relative=original.safe(name);require(relative.parts and relative.parts[0] not in ('.git','.codex','.aws') and '\x00' not in name,
        'Only original repository input paths may be restored')
    target=root/name
    for parent in target.parents:
        if parent==root:break
        require(not parent.is_symlink(),'Original input parents cannot redirect through a symbolic directory')
    require(target.is_relative_to(root),'Original destination escaped its actual root');return target


def check_existing(root,name,value):
    target=checked_path(root,name)
    if not target.exists() and not target.is_symlink():
        require(PurePosixPath(name).parts[0]=='out','An immutable owning source outside out may not be created or replaced')
        return False
    require(target.lstat().st_mode&0o777==value['mode'],'Existing original input mode differs')
    if value['kind']=='symlink':require(target.is_symlink() and os.readlink(target)==value['target'],'Existing original file alias differs')
    else:require(target.is_file() and not target.is_symlink() and target.stat().st_size==value['bytes'] and original.digest_file(target)==value['sha256'],
        'Existing owning source/input byte or file type differs; no overwrite')
    return True


def restore(root,archive,index,objects,flat_file_orders=None,reserve=8*1024**3):
    root=Path(root).resolve();archive=Path(archive);objects=Path(objects);orders=flat_file_orders or {}
    require(index['protocol']=='phase6-lossless-original-rejection-input-bundle-v1' and index['status']=='preserved-original-files-only-not-qualified' and
            index['source_root']==str(root) and index['original_files_rewritten'] is False and index['source_and_runtime_rejection_audits_still_required'] is True and
            index['missing_guarded_paths']==[] and archive.stat().st_size==index['archive_bytes'] and original.digest_file(archive)==index['archive_sha256'],
            'Complete exact source-bound original rejection bundle without missing guards required')
    expected=index['files'];require(expected and len(expected)<300000 and not objects.exists() and objects.is_relative_to(root/'out/rejection-independent'),
        'Fresh separate bounded original input object store required')
    for name,value in expected.items():
        checked_path(root,name);require(value['kind'] in ('file','symlink') and isinstance(value['bytes'],int) and value['bytes']>=0 and
            isinstance(value['mode'],int) and 0<=value['mode']<=0o777 and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256']),
            'Every actual original file type/mode/length/hash required')
        for parent in PurePosixPath(name).parents:
            require(str(parent) not in expected,'An original file cannot become another original file directory')
        check_existing(root,name,value)
    require(original.inspect_archive(archive,expected)==index['closure'],'Every original archive member must retain its exact full published identity')
    with tarfile.open(archive) as source:members=source.getmembers()
    unique=sum(v.size for v in members if v.isfile());base=objects.parent
    while not base.exists():base=base.parent
    require(shutil.disk_usage(base).free>=unique+reserve,'Original input restoration must retain the unchanged eight-GiB reserve')
    objects.mkdir(parents=True);data={};groups={};group_members={};hardlinks=[]
    with tarfile.open(archive) as source:
        for ordinal,entry in enumerate(source):
            value=expected[entry.name]
            if entry.isfile():
                path=objects/('object-'+str(ordinal));stream=source.extractfile(entry);h=hashlib.sha256();length=0
                with path.open('xb') as output:
                    for block in iter(lambda:stream.read(1024*1024),b''):output.write(block);h.update(block);length+=len(block)
                require(length==value['bytes'] and h.hexdigest()==value['sha256'],'Actual original object bytes differ')
                path.chmod(value['mode']);data[entry.name]=path;groups[entry.name]=entry.name;group_members[entry.name]=[entry.name]
            elif entry.islnk():
                require(entry.linkname in groups,'Actual original hardlink target must precede its alias')
                group=groups[entry.linkname];groups[entry.name]=group;group_members[group].append(entry.name);hardlinks.append((entry.name,entry.linkname))
    # Prefer already verified owning inputs as the original hardlink root; never overwrite them.
    for group,names in group_members.items():
        existing=[root/name for name in names if check_existing(root,name,expected[name])]
        if existing:
            require(all(path.samefile(existing[0]) for path in existing),'Existing original aliases do not share their declared hardlink identity')
            data[group]=existing[0]
    ordered=[];seen=set()
    for parent,names in orders.items():
        original.safe(parent);require(names and len(names)==len(set(names)) and all(PurePosixPath(name).name==name for name in names),
            'Exact recorded original flat-file order required')
        for leaf in names:
            name=parent+'/'+leaf;require(name in expected and name not in seen,'Recorded original file order contains a missing or duplicate input');ordered.append(name);seen.add(name)
    ordered.extend(name for name in sorted(expected) if name not in seen)
    for name in ordered:
        value=expected[name];target=checked_path(root,name)
        if check_existing(root,name,value):continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if value['kind']=='symlink':os.symlink(value['target'],target)
        else:os.link(data[groups[name]],target)
    restored,missing=original.inventory(root,{root/name for name in expected})
    require(not missing and restored==expected and original.digest_file(archive)==index['archive_sha256'],
        'Every original restored logical name/type/mode/alias/length/hash must remain exact')
    require(all((root/a).samefile(root/b) for a,b in hardlinks),'Every original hardlink relationship must remain exact')
    actual_orders={}
    for parent,names in orders.items():
        actual=[path.name for path in (root/parent).iterdir() if path.is_file()]
        require(len(actual)==len(names) and set(actual)==set(names),'Every original flat file must remain present without extra entries')
        actual_orders[parent]=actual
    shutil.rmtree(objects)
    return dict(protocol='phase6-restored-exact-original-rejection-inputs-v1',logical_files=len(expected),logical_bytes=sum(v['bytes'] for v in expected.values()),
        original_hardlink_aliases_verified=len(hardlinks),original_flat_file_directories_verified=len(orders),original_flat_file_record_orders=orders,actual_restored_file_enumeration_orders=actual_orders,
        original_flat_file_enumeration_order_matched=(actual_orders==orders),
        all_original_files_and_source_guards_unchanged=True,original_audit_or_capture_relabelled=False,new_simulator_processes=0,
        independent_original_rejection_audit_still_required=True,complete_class_eligibility_qualified=False,normal_admission_qualified=False,
        phase6_complete=False,hands_on_ready=False)



def compare_original_audit(original_audit,fresh_audit,control_ids):
    """Keep original raw JSON intact; allow only filesystem file-table enumeration differences."""
    require(control_ids and len(control_ids)==len(set(control_ids)) and set(original_audit['controls'])==set(fresh_audit['controls'])==set(control_ids),
            'Every exact original rejection control must be represented')
    allowed={('controls',name,'files_sha256') for name in control_ids};differences=[]
    def compare(left,right,path):
        require(type(left) is type(right),'Original audit field type changed: '+repr(path))
        if isinstance(left,dict):
            require(set(left)==set(right),'Original audit dictionary membership changed: '+repr(path))
            if list(left)!=list(right):
                require(path in allowed,'Original non-file-table dictionary order changed: '+repr(path))
                differences.append(dict(path=list(path),original_key_order=list(left),fresh_key_order=list(right)))
            for key in left:compare(left[key],right[key],path+(key,))
        elif isinstance(left,list):
            require(len(left)==len(right),'Original audit list scope changed: '+repr(path))
            for index,(a,b) in enumerate(zip(left,right)):compare(a,b,path+(index,))
        else:require(left==right,'Original audit field value changed: '+repr(path))
    compare(original_audit,fresh_audit,())
    return dict(every_original_audit_field_type_and_value_reproduced_exactly=True,all_original_list_order_and_dictionary_membership_preserved=True,
        original_Ccc_auditor_mapping_equality_contract_preserved=True,only_file_hash_table_key_order_differences=differences,
        original_raw_audit_or_capture_normalized=False,original_auditor_source_modified=False,acceptance_values_or_tolerances_changed=False)
