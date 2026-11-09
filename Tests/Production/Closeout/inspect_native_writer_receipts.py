"""Verify retained native writer API/source/member receipts without running a simulator.

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
import zipfile
from contracts import ROOT,require,sha,case_ids

SOURCE='9edaec08fbc41a25dc6cd4d319a14c950fdd8177'
RUNTIME='ccc02c8a34bd1f227624d8778a141e8736ae8111'
PINS={
 'Debug-automatic':(42556975058,128964915249,13657036771,736116240,'c00df4086fe107a79ef87d08b2abac56ee9fa7ab1fd059130902cbd9f479bb90'),
 'Debug-sse2':(42556645824,128963912109,13655200082,735672583,'bd8c9078f5b85971f14acbb833cebcdbbafb406a09d190d8dd78252f2374c0d5'),
 'Release-automatic':(42558052729,128968217162,13656707649,736291319,'9a24896010ffd0d3947b4582ecb0945c1b6dd181566f19a8348c96f266e0be67'),
 'Release-sse2':(42556648122,128963912091,13656181152,735852648,'63987945a8c17d3d47635bb9ed6988c5ec9cb45ce36ca2b6287b7393bd3e6ebc')}
MINIMUM={'Tests/Production/RemainingStockPersistence/capture_native.py','Tests/Production/RemainingStockPersistence/saved_inputs.py',
 'Tests/Production/RemainingStockPersistence/saved_state.py','Tests/Production/RemainingStockPersistence/protocol.json',
 'Tests/Production/RemainingVessels/NativeProbe.cpp','Tests/Production/RemainingVessels/native.py',
 'Tests/Production/RemainingStock/configuration_input.py','Tests/Production/RemainingStock/matched_clock.py'}


def validate_api(record,profile):
    run_id,job_id,artifact_id,size,digest=PINS[profile];run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and
        run['id']==run_id and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['head_sha']==SOURCE and
        run['head_branch']=='qualification/native-runtime-writer-'+profile.lower()+'-v2' and
        run['path']=='.github/workflows/phase6-native-runtime-network-writers.yml' and run['run_attempt']==1 and
        run['status']=='completed' and run['conclusion']=='success' and len(jobs)==2 and
        all(j['run_id']==run_id and j['head_sha']==SOURCE and j['status']=='completed' and j['conclusion']=='success' and
            'ubuntu-24.04' in j['labels'] and 'self-hosted' not in j['labels'] for j in jobs),
        'Exact successful immutable standard-hosted native writer run/jobs required')
    selected=[j for j in jobs if j['id']==job_id and j['name']=='Normal native runtime stock writer '+profile.replace('-',' ')]
    require(len(selected)==1,'Exact completed native writer profile job required')
    steps=[s for s in selected[0]['steps'] if s['name']=='Run all unchanged normal-host writer cases and independently inspect every result in matching userspace']
    require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success',
            'Actual full native writer collection and native-only inspection must have passed')
    require(artifact['id']==artifact_id and artifact['name']=='normal-native-runtime-stock-writer-'+profile and
        artifact['size_in_bytes']==size and artifact['digest']=='sha256:'+digest and artifact['expired'] is False and
        artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==SOURCE,
        'Exact native writer raw API artifact identity required')


def inspect(record,archive,profile,owner=ROOT):
    sys.path.insert(0,str(ROOT/'Tests/Production/RemainingStockPersistence'))
    import source_complete_original_transport
    transport=source_complete_original_transport.legacy
    validate_api(record,profile);_,_,_,size,digest=PINS[profile];archive=Path(archive)
    require(archive.stat().st_size==size and sha(archive)==digest,'Actual immutable native writer ZIP digest/size differs')
    prefix='native-stock-writer/'+profile+'/';top='hosted-native-writer/'+profile+'/';ids=list(case_ids());checked={};sources={}
    with zipfile.ZipFile(archive) as source:
        seen=set();members={}
        for entry in source.infolist():
            name=str(transport.safe(entry.filename));require(name.casefold() not in seen and not stat.S_ISLNK(entry.external_attr>>16),
                'Duplicate/case-colliding/symlink native writer ZIP member');seen.add(name.casefold())
            if not entry.is_dir():members[name]=entry
        def read(name):
            require(name in members,'Missing retained native writer member: '+name)
            body=source.read(name);checked[name]=hashlib.sha256(body).hexdigest();return body
        capture_body=read(prefix+'capture.json');capture=json.loads(capture_body);collection=json.loads(read(top+'collection.json'))
        audit_body=read(top+'independent-native-writer-audit.json');audit=json.loads(audit_body)
        require(collection['protocol']=='phase6-hosted-native-stock-writer-runtime-v3' and
            collection['status']=='captured-and-independently-audited-native-writers-only' and collection['profile']==profile and
            collection['collector_source']==SOURCE and collection['compiled_runtime_source']==RUNTIME and collection['actual_processes']==76 and
            collection['capture_sha256']==hashlib.sha256(capture_body).hexdigest() and
            collection['independent_audit_sha256']==hashlib.sha256(audit_body).hexdigest() and
            collection['phase6_complete'] is False and collection['native_admission_qualified'] is False,
            'Actual source-bound native collection receipt differs')
        configuration,mode=profile.split('-',1)
        require(capture['status']=='captured-awaiting-independent-persistence-audit' and capture['phase']=='stock-writer' and
            capture['host']=='native-linux' and capture['producer_commit']==SOURCE and capture['runtime_source_commit']==RUNTIME and
            capture['runtime_role']=='normal' and capture['observer_delay_ms']==120 and capture['process_receipts']=='owned-pid-start-argv-exit-v1' and
            capture['runtime_identity']['configuration']==configuration and capture['runtime_identity']['math_profile']==mode and
            capture['cases_requested']==ids and set(capture['cases'])==set(ids) and capture['repeats']==2 and capture['frames']==960 and
            not capture['failures'] and capture['diagnostic_only'] is False and
            capture['owning_sources_runtime_probe_windows_inputs_assets_and_data_unchanged'] is True and
            capture['native_admission_qualified'] is False and capture['phase6_complete'] is False,
            'Complete normal-host native writer source/profile/scope receipt required')
        require(audit['status']=='audited-native-phase-only' and audit['profile']==profile and audit['phase']=='stock-writer' and
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
            rows=capture['cases'][identity]['runs'];require(len(rows)==2,'Both native writer repetitions required')
            for repeat,row in enumerate(rows,1):
                require(type(row['files_sha256']) is dict and row['files_sha256'],'Complete recorded native raw process member set required')
                for name,value in row['files_sha256'].items():
                    require(str(transport.safe(name))==name,'Canonical actual native run member required')
                    require(hashlib.sha256(read(prefix+identity+'-'+str(repeat)+'/'+name)).hexdigest()==value,
                            'Actual retained native raw process member differs from its recorded source: '+identity+'/'+name)
    require(sha(archive)==digest,'Native writer raw API archive changed during inspection')
    return dict(protocol='phase6-retained-native-writer-source-member-receipts-v1',status='verified-native-writer-API-source-and-raw-process-members-only',
        profile=profile,writer_source=SOURCE,runtime_source=RUNTIME,archive_sha256=digest,actual_native_processes=76,
        checked_retained_members_sha256=checked,source_sha256_lf=sources,full_physical_camera_frame_clock_saved_state_and_cross_comparisons_pending=True,
        phase6_complete=False,native_admission_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=sorted(PINS),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('ImageOS')=='ubuntu24' and sys.platform=='linux',
            'Standard hosted Ubuntu source verification only; no local bulk transfers')
    require(not a.output.exists(),'Fresh native writer source verification output required');api_sha=sha(a.api)
    result=inspect(json.loads(a.api.read_text()),a.archive,a.profile);require(sha(a.api)==api_sha,'Actual native writer API receipt changed')
    result.update(actual_API_sha256=api_sha,verifier_source=os.environ['GITHUB_SHA'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
