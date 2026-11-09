"""Verify retained native reload API/source/member receipts without running a simulator.

This verifies immutable collection inputs for the next phase. Independent physical,
camera, full-frame, clock, saved-state and cross-platform comparisons remain required.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from contracts import ROOT,require,sha,case_ids

SOURCE='d2c579064f880e6c930da2263d1aa738d53e5423'
RUNTIME='ccc02c8a34bd1f227624d8778a141e8736ae8111'
PINS={
 'Release-sse2':(42586898292,129058981287,13670583705,735725777,'5c9dbd9ee46711f7753ef48ea214e3039d5a5579010a2f954ea1e1fe594c8d30'),
 'Debug-sse2':(42586898426, 129059018674, 13673108137, 735571099, '0eb3aa5828ee2de3892417ae0e8f310f78e07e56954d60aefe712a65e477b418'),
 'Release-automatic':(42586898836, 129058984274, 13673666999, 736202018, '5897e56bedecaf591390c7f3571d88690dd60abb6bf85cdfa2f7d6165d85162b')}
ORIGINAL='ba38a7efccb5f770e87add95f5e966aa40270756'
MINIMUM={'Tests/Production/RemainingStockPersistence/capture_native.py','Tests/Production/RemainingStockPersistence/saved_inputs.py',
 'Tests/Production/RemainingStockPersistence/saved_state.py','Tests/Production/RemainingStockPersistence/protocol.json',
 'Tests/Production/RemainingVessels/NativeProbe.cpp','Tests/Production/RemainingVessels/native.py',
 'Tests/Production/RemainingStock/configuration_input.py','Tests/Production/RemainingStock/matched_clock.py'}


def validate_api(record,profile):
    run_id,job_id,artifact_id,size,digest=PINS[profile];run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and
        run['id']==run_id and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['head_sha']==SOURCE and
        run['head_branch']=='qualification/native-stock-reload-'+profile.lower()+'-v3' and
        run['path']=='.github/workflows/phase6-native-retry-stock-reloads.yml' and run['run_attempt']==1 and
        run['status']=='completed' and run['conclusion']=='success' and len(jobs)==2 and
        all(j['run_id']==run_id and j['head_sha']==SOURCE and j['status']=='completed' and j['conclusion']=='success' and
            'ubuntu-24.04' in j['labels'] and 'self-hosted' not in j['labels'] for j in jobs),
        'Exact successful immutable standard-hosted native reload run/jobs required')
    selected=[j for j in jobs if j['id']==job_id and j['name']=='Native exact original save reload '+profile.replace('-',' ')]
    require(len(selected)==1,'Exact completed native reload profile job required')
    steps=[s for s in selected[0]['steps'] if s['name']=='Run all unchanged normal-host exact-save reloads and independently inspect every result in matching userspace']
    require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success',
            'Actual full native reload collection and native-only inspection must have passed')
    require(artifact['id']==artifact_id and artifact['name']=='retry-native-stock-reload-'+profile and
        artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and artifact['expired'] is False and
        artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==SOURCE,
        'Exact native reload raw API artifact identity required')


def inspect_reference(read,collection,capture,profile):
    """Re-read the actual retained retry proof and all 76 exact original saved-input hashes."""
    sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
    import retry_reference_proof as proof
    from source_complete_retry_provider import reference_receipts
    restored=json.loads(read('reference-audit-restoration/restoration.json'))
    names={
        'reference_transport':'original-stock-audit/transport/download.json',
        'reference_audit':'original-stock-audit/independent/writer-audit.json',
        'reference_persistence_audit':'original-stock-audit/independent/original-persistence-audit.json',
        'reference_restoration':'reference-audit-restoration/restoration.json'}
    retained=set(names.values())|proof.FIXED|{
        'reference-audit-restoration/source-artifact/'+name for name in restored['successful_audit_decoded_members_sha256']}|{
        'reference-audit-restoration/first-attempt-source-artifact/'+name for name in proof.retry.FIRST_MEMBERS}
    with tempfile.TemporaryDirectory(prefix='orbiter-native-reload-reference-') as temporary:
        out=Path(temporary)/'out'
        for name in sorted(retained):
            require(str(proof.prior.transport.legacy.safe(name))==name,'Canonical retained native retry member required')
            destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(read(name))
        cfg=dict(roles=dict(runner=dict(commit=SOURCE)),reference_retry_inputs=proof.inventory(out),
            **{name:dict(path=str(out/value),sha256=sha(out/value)) for name,value in names.items()})
        original=reference_receipts(cfg)
        reference=collection['original_reference'];ids=list(case_ids())
        require(reference['protocol']=='phase6-hosted-audited-native-reload-retry-reference-v2' and
            reference['status']=='bound-exact-audited-original-parent-saves-only' and reference['collector_source']==SOURCE and
            reference['profile']==profile and reference['original']==original and reference['original_saves_relabelled'] is False and
            reference['phase6_complete'] is False and reference['native_admission_qualified'] is False,
            'Actual native collection must bind the same independently reverified original audit retry')
        parent=Path('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform/out/original-stock-audit/transport')/profile/'remaining-stock-repaired'
        require(Path(reference['capture'])==parent,'Exact original parent capture path required')
        members=restored['original_api_archive_bindings'][profile]['decoded_members_sha256']
        writer=json.loads(read(names['reference_audit']))
        parent_sha=members['remaining-stock-repaired/capture.json']
        require(reference['parent_capture_sha256']==writer['profiles'][profile]['capture_sha256']==parent_sha,
            'Original parent capture identity differs from its full original writer audit')
        saves=reference['saved_inputs'];require(len(saves)==76 and
            {(v['case'],v['repeat']) for v in saves}=={(name,repeat) for name in ids for repeat in (1,2)},
            'Every original native reload input and both repeats required')
        cases={case['id']:case for case in json.loads((ROOT/'Tests/Production/RemainingStock/cases.json').read_text())['cases']}
        for identity in ids:
            for repeat,row in enumerate(capture['cases'][identity]['runs'],1):
                saved=next(v for v in saves if (v['case'],v['repeat'])==(identity,repeat))
                relative=identity+'-'+str(repeat)+'/Scenarios/(Current state).scn'
                checksum=members['remaining-stock-repaired/'+relative]
                require(saved['path']==str(parent/relative) and saved['sha256']==checksum and
                        reference['guarded_files_sha256'][saved['path']]==checksum,
                        'Exact original API-bound saved input or its captured guard differs')
                base='native-stock-reload/'+profile+'/'+identity+'-'+str(repeat)+'/'
                provenance=json.loads(read(base+'persistence-input.json'))
                entry='Scenarios/_Phase6Persistence/'+identity+'/'+Path(cases[identity]['scenario']).name
                require(provenance==row['persistence_input'] and provenance['parent_producer_commit']==ORIGINAL and
                    provenance['parent_capture_sha256']==parent_sha and provenance['parent_run']==identity+'-'+str(repeat) and
                    provenance['saved_input_sha256']==checksum and provenance['derived_scenario_entry_point']==entry and
                    row['executed_case']['scenario_entry_point']==entry and hashlib.sha256(read(base+entry)).hexdigest()==checksum,
                    'Actual executed native scenario is not its exact original audited Windows end save')
        require(reference_receipts(cfg)==original,'Actual immutable original retry proof changed during verification')
    return dict(original=original,exact_original_saved_inputs=76,original_parent_capture_sha256=parent_sha,
        original_saves_relabelled=False,full_native_physical_and_cross_comparisons_pending=True)


def inspect(record,archive,profile,owner=ROOT):
    sys.path.insert(0,str(ROOT/'Tests/Production/RemainingStockPersistence'))
    import source_complete_original_transport
    transport=source_complete_original_transport.legacy
    validate_api(record,profile);_,_,_,size,digest=PINS[profile];archive=Path(archive)
    require(archive.stat().st_size==size and sha(archive)==digest,'Actual immutable native reload ZIP digest/size differs')
    prefix='native-stock-reload/'+profile+'/';top='hosted-native-reload/'+profile+'/';ids=list(case_ids());checked={};sources={}
    with zipfile.ZipFile(archive) as source:
        seen=set();members={}
        for entry in source.infolist():
            name=str(transport.safe(entry.filename));require(name.casefold() not in seen and not stat.S_ISLNK(entry.external_attr>>16),
                'Duplicate/case-colliding/symlink native reload ZIP member');seen.add(name.casefold())
            if not entry.is_dir():members[name]=entry
        def read(name):
            require(name in members,'Missing retained native reload member: '+name)
            body=source.read(name);checked[name]=hashlib.sha256(body).hexdigest();return body
        capture_body=read(prefix+'capture.json');capture=json.loads(capture_body);collection=json.loads(read(top+'collection.json'))
        audit_body=read(top+'independent-native-reload-audit.json');audit=json.loads(audit_body)
        require(collection['protocol']=='phase6-hosted-native-exact-save-reload-retry-v2' and
            collection['status']=='captured-and-independently-audited-native-exact-save-reloads-only' and collection['profile']==profile and
            collection['collector_source']==SOURCE and collection['compiled_runtime_source']==RUNTIME and collection['actual_processes']==76 and
            collection['capture_sha256']==hashlib.sha256(capture_body).hexdigest() and
            collection['independent_audit_sha256']==hashlib.sha256(audit_body).hexdigest() and
            collection['phase6_complete'] is False and collection['native_admission_qualified'] is False,
            'Actual source-bound native collection receipt differs')
        configuration,mode=profile.split('-',1)
        require(capture['status']=='captured-awaiting-independent-persistence-audit' and capture['phase']=='windows-save-reload' and
            capture['windows_parent_producer']==ORIGINAL and capture['host']=='native-linux' and capture['producer_commit']==SOURCE and capture['runtime_source_commit']==RUNTIME and
            capture['runtime_role']=='normal' and capture['observer_delay_ms']==120 and capture['process_receipts']=='owned-pid-start-argv-exit-v1' and
            capture['runtime_identity']['configuration']==configuration and capture['runtime_identity']['math_profile']==mode and
            capture['cases_requested']==ids and set(capture['cases'])==set(ids) and capture['repeats']==2 and capture['frames']==960 and
            not capture['failures'] and capture['diagnostic_only'] is False and
            capture['owning_sources_runtime_probe_windows_inputs_assets_and_data_unchanged'] is True and
            capture['native_admission_qualified'] is False and capture['phase6_complete'] is False,
            'Complete normal-host native reload source/profile/scope receipt required')
        require(audit['status']=='audited-native-phase-only' and audit['profile']==profile and audit['phase']=='windows-save-reload' and
            audit['source_producer']==SOURCE and audit['runtime_source']==RUNTIME and audit['runtime_role']=='normal' and
            audit['actual_processes']==76 and audit['actual_presentations']==76*960 and audit['observer_delay_ms']==120 and
            audit['capture_sha256']==hashlib.sha256(capture_body).hexdigest() and audit['owning_bytes_unchanged'] is True and
            audit['diagnostic_only'] is False and audit['phase6_complete'] is False and audit['native_admission_qualified'] is False,
            'Actual full native-only independent audit receipt differs')
        require(MINIMUM<=set(capture['source_sha256_lf']),'Complete native source/input/clock closure required')
        for name,value in capture['source_sha256_lf'].items():
            require(str(transport.safe(name))==name and re.fullmatch('[0-9a-f]{64}',value),'Canonical native source byte identity required')
            body=subprocess.check_output(['git','-C',str(owner),'show',SOURCE+':'+name]).replace(b'\r\n',b'\n')
            require(hashlib.sha256(body).hexdigest()==value,'Retained native source differs from its exact immutable producer: '+name);sources[name]=value
        for identity in ids:
            rows=capture['cases'][identity]['runs'];require(len(rows)==2,'Both native reload repetitions required')
            for repeat,row in enumerate(rows,1):
                require(type(row['files_sha256']) is dict and row['files_sha256'],'Complete recorded native raw process member set required')
                for name,value in row['files_sha256'].items():
                    require(str(transport.safe(name))==name,'Canonical actual native run member required')
                    require(hashlib.sha256(read(prefix+identity+'-'+str(repeat)+'/'+name)).hexdigest()==value,
                            'Actual retained native raw process member differs from its recorded source: '+identity+'/'+name)
        reference=inspect_reference(read,collection,capture,profile)
    require(sha(archive)==digest,'Native reload raw API archive changed during inspection')
    return dict(protocol='phase6-retained-native-reload-source-member-receipts-v1',status='verified-native-reload-API-source-reference-and-raw-process-members-only',
        profile=profile,reload_source=SOURCE,runtime_source=RUNTIME,archive_sha256=digest,actual_native_processes=76,
        checked_retained_members_sha256=checked,source_sha256_lf=sources,original_reference=reference,full_physical_camera_frame_clock_saved_state_and_cross_comparisons_pending=True,
        phase6_complete=False,native_admission_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=sorted(PINS),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('ImageOS')=='ubuntu24' and sys.platform=='linux',
            'Standard hosted Ubuntu source verification only; no local bulk transfers')
    require(not a.output.exists(),'Fresh native reload source verification output required');api_sha=sha(a.api)
    result=inspect(json.loads(a.api.read_text()),a.archive,a.profile);require(sha(a.api)==api_sha,'Actual native reload API receipt changed')
    result.update(actual_API_sha256=api_sha,verifier_source=os.environ['GITHUB_SHA'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({key:result[key] for key in ('status','profile','archive_sha256','actual_native_processes','verifier_source','phase6_complete')}|dict(exact_original_saved_inputs=result['original_reference']['exact_original_saved_inputs'])))


if __name__=='__main__':main()
