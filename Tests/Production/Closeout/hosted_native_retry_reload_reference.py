"""Bind native reload inputs to the untouched, independently audited fresh Windows cohort."""
import os
from pathlib import Path
import subprocess
import sys
from contracts import ROOT,require,sha,load,case_ids

ORIGINAL='ba38a7efccb5f770e87add95f5e966aa40270756'
AUDITOR='a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7'


def bind(profile):
    require(profile in {c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')},'Exact complete native reload profile required')
    sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
    from source_complete_retry_provider import reference_receipts
    from retry_reference_proof import inventory,guarded as retry_guarded
    source=os.environ['GITHUB_SHA'];base=ROOT/'out/original-stock-audit'
    paths=dict(reference_transport=base/'transport/download.json',reference_audit=base/'independent/writer-audit.json',
        reference_persistence_audit=base/'independent/original-persistence-audit.json',
        reference_restoration=ROOT/'out/reference-audit-restoration/restoration.json')
    cfg=dict(roles=dict(runner=dict(commit=source)),reference_retry_inputs=inventory(ROOT/'out'),**{name:dict(path=str(path),sha256=sha(path)) for name,path in paths.items()})
    proof=reference_receipts(cfg)
    require(proof['original_capture_source']==ORIGINAL and proof['original_auditor_source']==AUDITOR and
            proof['original_windows_processes']==608,'Actual independently audited complete fresh original cohort required')
    restoration=load(paths['reference_restoration']);manifest=load(paths['reference_transport']);writer=load(paths['reference_audit'])
    require(len(manifest['artifacts'])==4 and {value['profile'] for value in manifest['artifacts']}=={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')},'Complete independently audited original API profile matrix required')
    item=[value for value in manifest['artifacts'] if value['profile']==profile];require(len(item)==1,'One exact original API profile required');item=item[0]
    require(item['name']=='matched-clock-remaining-stock-v2-'+profile and item['decoded']=='out/original-stock-audit/transport/'+profile and
            item['path']=='out/original-stock-audit/archives/'+item['name']+'.zip','Exact immutable original API archive/decoded paths required')
    decoded=ROOT/item['decoded'];capture=decoded/'remaining-stock-repaired';build=decoded/'remaining-stock-repaired-build'
    binding=restoration['original_api_archive_bindings'][profile];members=binding['decoded_members_sha256']
    archive=ROOT/item['path'];require(sha(archive)==item['sha256']==binding['archive_sha256'] and archive.stat().st_size==item['bytes']==binding['archive_bytes'],
            'Actual original raw API ZIP differs from the independently audited source')
    parent_file=capture/'capture.json';parent=load(parent_file);ids=list(case_ids());configuration,mode=profile.split('-',1)
    require(parent['producer_commit']==ORIGINAL and parent['configuration']==configuration and parent['math_profile']==mode and
            parent['protocol']=='remaining-stock-matched-clock-v2' and parent['status']=='captured-awaiting-independent-audit' and
            parent['diagnostic_only'] is False and not parent['failures'] and parent['cases_requested']==ids and set(parent['cases'])==set(ids) and
            sha(parent_file)==members['remaining-stock-repaired/capture.json']==writer['profiles'][profile]['capture_sha256'],
            'Exact immutable original complete parent observations required')
    guarded={str(path):sha(path) for path in paths.values()};guarded.update(retry_guarded(cfg));guarded[str(parent_file)]=sha(parent_file);guarded[str(archive)]=sha(archive)
    saves=[]
    for identity in ids:
        require(len(parent['cases'][identity]['runs'])==2,'Both real original parent repetitions required')
        for repeat in (1,2):
            relative=identity+'-'+str(repeat)+'/Scenarios/(Current state).scn';path=capture/relative;checksum=members['remaining-stock-repaired/'+relative]
            require(sha(path)==checksum,'Actual exact original saved input differs from its audited API archive member')
            guarded[str(path)]=checksum;saves.append(dict(case=identity,repeat=repeat,path=str(path),sha256=checksum))
    require(len(saves)==76 and build.is_dir(),'Complete immutable exact-save parent/build closure required')
    preserved=base/('preserved-'+configuration);require(preserved.is_dir(),'Separately retained original application and SDK required')
    sources=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',source,'--','Tests/Production/Closeout','Tests/Production/CurrentWindows/Hosted'],text=True).splitlines()
    sources=[name for name in sources if name.endswith(('.py','.sh'))]
    require(sources and 'Tests/Production/Closeout/hosted_native_retry_reload_reference.py' in sources, 'Complete exact retry helper source closure required')
    for name in sources:
        path=ROOT/name;require(path.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+name]),
            'Actual native reference helper differs from immutable collector source');guarded[str(path)]=sha(path)
    return dict(protocol='phase6-hosted-audited-native-reload-retry-reference-v2',status='bound-exact-audited-original-parent-saves-only',
        collector_source=source,profile=profile,capture=str(capture),build=str(build),preserved=str(preserved),original=proof,
        parent_capture_sha256=sha(parent_file),saved_inputs=saves,guarded_files_sha256=guarded,
        original_saves_relabelled=False,native_admission_qualified=False,phase6_complete=False)


def verify(record):
    require(record['protocol']=='phase6-hosted-audited-native-reload-retry-reference-v2' and record['collector_source']==os.environ['GITHUB_SHA'] and
            record['status']=='bound-exact-audited-original-parent-saves-only' and len(record['saved_inputs'])==76 and
            {(item['case'],item['repeat']) for item in record['saved_inputs']}=={(name,repeat) for name in case_ids() for repeat in (1,2)} and
            record['original_saves_relabelled'] is False and record['native_admission_qualified'] is False and record['phase6_complete'] is False,
            'Exact native reload reference scope and pending qualification required')
    require(all(sha(name)==value for name,value in record['guarded_files_sha256'].items()),
            'Actual original API archive/receipts/parent/saved input or owning helper changed during native reloads')
    return record
