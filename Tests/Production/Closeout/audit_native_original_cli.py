"""Decode and expose immutable native observations, then run the complete original/native audit."""
import json
import os
from pathlib import Path
import shutil
import stat
import zipfile
from contracts import ROOT,require,sha,load,atomic_json,PROFILES,PHASES
import audit_native_original_phase as physical


def decode(api,archive,target,profile,phase):
    """Retain every exact native artifact member and the unchanged eight-GiB reserve."""
    collector=physical.writers if phase=='stock-writer' else physical.reloads
    require(profile in PROFILES and phase in PHASES,'Exact retained native source phase required')
    collector.validate_api(api,profile);artifact=api['artifact'];archive=Path(archive);target=Path(target)
    require(not target.exists() and archive.stat().st_size==artifact['size_in_bytes'] and
        'sha256:'+sha(archive)==artifact['digest'],'Fresh exact native API ZIP bytes required')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        require(shutil.disk_usage(target.parent).free>=sum(m.file_size for m in source.infolist())+8*1024**3,
            'Native physical decode must retain the unchanged capacity reserve')
        seen=set();entries=[]
        for entry in source.infolist():
            name=str(physical.original.legacy.safe(entry.filename))
            require(name.casefold() not in seen and not stat.S_ISLNK(entry.external_attr>>16),
                'Duplicate/case-colliding/symlink retained native artifact member')
            seen.add(name.casefold())
            if not entry.is_dir():entries.append((entry,name))
        target.mkdir()
        for entry,name in entries:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
            with source.open(entry) as incoming,destination.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,1024*1024)
    return physical.original.legacy.inspect_archive(archive,target,artifact['digest'][7:],artifact['size_in_bytes'])


def expose_native(payload,profile,phase):
    """Link only the protected observation tree to its exact captured path; no recapture or rewrite."""
    require(profile in PROFILES and phase in PHASES,'Exact complete native phase required')
    prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload'
    source=Path(payload)/prefix/profile;destination=ROOT/'out'/prefix/profile
    require(source.is_dir() and not source.is_symlink() and not destination.exists(),
        'Fresh original native path and retained decoded observations required')
    require(all(not path.is_symlink() for path in source.rglob('*')),'No redirected native observation input')
    destination.parent.mkdir(parents=True,exist_ok=True)
    require(source.stat().st_dev==destination.parent.stat().st_dev,'Retained native observations require the same guarded local volume')
    shutil.copytree(source,destination,copy_function=os.link)
    files=physical.bound_native_tree(payload,destination,profile,phase)
    require(all((source/name).stat().st_ino==(destination/name).stat().st_ino and sha(destination/name)==value
        for name,value in files.items()),'Actual immutable native exposure links or bytes differ')
    return destination,dict(policy='read-only-retained-native-observation-hardlinks-v1',source=str(source),destination=str(destination),
        files_sha256=files,original_capture_bytes_rewritten=False,simulator_executed=False,qualification_granted=False)


def restore_asset_metadata(payload,capture,output):
    """Retain fresh setup metadata, then restore the exact captured descriptors over identical actual assets."""
    assets=ROOT/'out/native-stock-assets';names={'remaining-vessels-resources.json','resources.json','cockpit-test-font.json'}
    expected=capture['asset_files_sha256'];require(expected,'Full recorded native asset closure required')
    for name,value in expected.items():
        require(str(physical.original.legacy.safe(name))==name,'Canonical recorded native asset required')
        if name not in names:require(sha(assets/name)==value,'Actual staged native asset differs from its captured original: '+name)
    records={};fresh=Path(output)/'fresh-asset-metadata';fresh.mkdir()
    for name in sorted(names):
        source=Path(payload)/'native-stock-assets'/name;target=assets/name
        require(source.is_file() and not source.is_symlink() and target.is_file() and not target.is_symlink(),
            'Both fresh and captured exact asset descriptors required')
        shutil.copy2(target,fresh/name);original_sha=sha(source);shutil.copy2(source,target)
        require(sha(source)==sha(target)==original_sha,'Captured native resource descriptor changed during restoration')
        records[name]=dict(captured_sha256=original_sha,fresh_setup_sha256=sha(fresh/name),restored_sha256=sha(target))
    require(all(sha(assets/name)==value for name,value in expected.items()),'Every actual restored/staged native asset must equal the unchanged capture')
    return dict(protocol='phase6-retained-native-asset-descriptor-restoration-v1',files=records,
        actual_asset_bytes_equal_captured_map=True,captured_descriptors_relabelled=False,qualification_granted=False)


def audit_after_bootstrap(profile,phase,bootstrap_output):
    require(profile in PROFILES and phase in PHASES and os.environ.get('GITHUB_ACTIONS')=='true' and
        os.environ.get('RUNNER_OS')=='Linux' and os.environ.get('ImageOS')=='ubuntu24',
        'Exact standard hosted native physical phase required; no local full audit')
    cell=profile+'-'+phase;base=ROOT/'out/native-original-source'/cell
    api_file=base/'api.json';archive=base/'producer.zip';api=load(api_file)
    payload=ROOT/'out/native-original-payload'/cell;receipt_path=Path(bootstrap_output)/'input-restoration.json'
    require(not receipt_path.exists(),'Fresh native physical input restoration receipt required')
    report=dict(protocol='phase6-retained-native-physical-input-restoration-v1',status='running',profile=profile,phase=phase,
        original_api_sha256=sha(api_file),original_archive_sha256=sha(archive),simulator_executed=False,
        phase6_complete=False,native_admission_qualified=False)
    def save():atomic_json(receipt_path,report)
    save()
    try:
        members=decode(api,archive,payload,profile,phase);report['decoded_members_sha256']=members;save()
        native,exposure=expose_native(payload,profile,phase);report['observation_exposure']=exposure;save()
        report['asset_metadata']=restore_asset_metadata(payload,load(native/'capture.json'),bootstrap_output);save()
        result=physical.inspect(payload,api,archive,native,profile,phase,
            ROOT/'out/native-original-auxiliary/ssim/api.json',ROOT/'out/native-original-auxiliary/ssim/producer.zip',
            ROOT/'out/native-original-windows-mesa',ROOT/'out/native-original-physical-audits'/(cell+'.json'),api_file)
        require(result['status']=='passed-one-complete-native-original-physical-phase-only',
            'Complete actual original/native physical phase required')
        require(physical.original.legacy.inspect_archive(archive,payload,api['artifact']['digest'][7:],api['artifact']['size_in_bytes'])==members and
            sha(api_file)==report['original_api_sha256'] and sha(archive)==report['original_archive_sha256'],
            'Actual native API/archive/every decoded input changed during physical audit')
        report.update(status='restored-and-audited-one-complete-native-original-physical-phase-only',actual_native_processes=76,
            actual_direct_original_native_pairs=76,complete_four_profile_two_phase_matrix_pending=True,current_native_comparisons_pending=True)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(json.dumps(dict(status=result['status'],profile=profile,phase=phase,actual_native_processes=result['actual_native_processes'],
        actual_direct_original_native_pairs=result['actual_direct_original_native_pairs'],phase6_complete=False,native_admission_qualified=False)))
    return result
