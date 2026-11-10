#!/usr/bin/env python3
"""Close only renewed positive class lifetime facets from four independently replayed profiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import zipfile
from hosted_native_package import ROOT,require,sha,load
from inspect_hosted_native_general_api import safe
from inspect_hosted_class_lifetimes import validate_api
import hosted_class_lifetimes as original
from hosted_native_general_api import source_identity
from class_eligibility import family_coverage
from checklist import requirements
from contracts import atomic_json,PROFILES

LOCK=ROOT/'Tests/Production/Closeout/class-lifetime-profile-proofs-v1.lock.json'


def decode(archive,destination):
    require(not destination.exists(),'Fresh positive profile metadata restoration required');destination.mkdir(parents=True)
    members={};seen=set()
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist()
        require(len(entries)<500 and sum(i.file_size for i in entries)<32*1024**2,'Bounded profile metadata only required')
        for item in entries:
            name=item.filename.rstrip('/') if item.is_dir() else item.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,
                    'Duplicate redirected or privileged profile metadata')
            seen.add(name.casefold())
            if item.is_dir():continue
            path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(incoming.read(item));members[name]=sha(path)
    return members


def inspect_profile(profile,base,pin):
    record=load(base/'api.json');run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==pin['run_id'] and
            run['head_sha']==pin['source'] and run['head_branch']==pin['branch'] and
            run['path']=='.github/workflows/phase6-native-class-independent.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Exact completed independent profile run required')
    require(len(jobs)==2 and len({j['id'] for j in jobs})==2 and
            all(str(j['id']) in pin['jobs'] and j['name']==pin['jobs'][str(j['id'])] and j['head_sha']==pin['source'] and
                j['run_id']==pin['run_id'] and j['status']=='completed' and j['conclusion']=='success' and
                j['labels']==['ubuntu-24.04'] for j in jobs),'Exact two closed standard-runner profile jobs required')
    archive=base/'producer.zip'
    require(artifact['id']==pin['artifact_id'] and artifact['name']=='independent-original-class-'+profile and not artifact['expired'] and
            artifact['size_in_bytes']==pin['archive_bytes']==archive.stat().st_size and
            artifact['digest']=='sha256:'+pin['archive_sha256'] and sha(archive)==pin['archive_sha256'] and
            artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==run['head_sha'],
            'Actual independently published profile artifact/API/source differs')
    payload=base/'decoded';members=decode(archive,payload);folder=payload/'class-lifetime-independent'/profile
    proof=load(folder/'proof.json');family=load(folder/'independent-family-lifetimes.json');paused=load(folder/'independent-paused-lifetimes.json')
    raw=load(folder/'raw-members.json');raw_api=load(payload/'class-lifetime-published'/profile/'api.json');capture_lock,capture_pin=validate_api(raw_api,profile)
    require(proof['protocol']=='phase6-independent-published-original-class-profile-v1' and
            proof['status']=='verified-published-original-family-and-paused-profile-only' and proof['profile']==profile and
            proof['auditor_source']==pin['source'] and proof['actual_auditor_pid']>0 and
            proof['original_run_id']==capture_lock['run_id'] and proof['original_source']==capture_lock['source'] and
            proof['original_job_id']==capture_pin['job_id'] and proof['original_artifact_id']==capture_pin['artifact_id'] and
            proof['original_archive_sha256']==capture_pin['archive_sha256'] and proof['original_archive_bytes']==capture_pin['archive_bytes'],
            'Actual complete independently replayed original profile lineage required')
    require(proof['new_simulator_processes']==0 and proof['actual_original_simulator_processes']==8 and
            proof['active_worlds']==140 and proof['paused_worlds']==20 and proof['real_F5_reloads']==19 and
            proof['all_original_input_and_raw_bytes_unchanged'] is True and
            proof['original_active_and_paused_audits_reproduced_byte_identically'] is True and
            all(proof[k] is False for k in ('qualification_granted','complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')),
            'Positive profile coverage must preserve every remaining acceptance gate')
    require(sha(folder/'raw-members.json')==proof['raw_members_sha256'] and len(raw)==proof['actual_raw_members'] and
            sum(v['bytes'] for v in raw.values())==proof['actual_raw_decoded_bytes'] and
            sha(payload/'class-lifetime-published'/profile/'api.json')==proof['source_api_sha256'],
            'Complete actual raw-member and input API witnesses required')
    require(family['capture_sha256']==raw['native-class-lifetimes/'+profile+'/lifetimes.json']['sha256'] and
            paused['capture_sha256']==raw['native-class-paused/'+profile+'/verification.json']['sha256'],
            'Both original capture hashes must match their complete independent audit witnesses')
    old='hosted-native-class-lifetimes/'+profile+'/'
    require(raw[old+'collection.json']['sha256']==proof['original_collection_sha256'] and
            raw[old+'independent-family-lifetimes.json']['sha256']==proof['original_family_audit_sha256']==sha(folder/'independent-family-lifetimes.json') and
            raw[old+'independent-paused-lifetimes.json']['sha256']==proof['original_paused_audit_sha256']==sha(folder/'independent-paused-lifetimes.json'),
            'Both unchanged original audit reports must reproduce byte for byte')
    require(family['status']=='audited-twenty-world-lifetimes-diagnostic-only' and family['worlds']==140 and
            family['successful_presents']==8400 and family['owning_bytes_unchanged'] is True and
            family['runtime_identity']==paused['runtime_identity'] and family['runtime_identity']['profile']==profile and
            family['runtime_identity']['runtime_source_commit']==original.COMPILED and family['runtime_identity']['sanitizer_linked'] is True and
            set(family['cases'])==set(original.CASES),'Original seven-scene complete finite class family coverage required')
    for case,actual in family['cases'].items():
        require(len(actual['worlds'])==20 and all(v==dict(init=20,fini=20,destroyed_link_maps=20) for v in actual['module_lifetimes'].values()),
                'Every original native module must complete twenty actual load/unload lifetimes')
        for index,world in enumerate(actual['worlds'],1):
            require(world['lifecycle']==dict(rendered_frames=60,successful_presents=60,context_deleted=True),
                    'Every original active world must retain all frames and clean contexts')
            require(all(raw['native-class-lifetimes/'+profile+'/'+case+'/session-'+str(index)+'/'+n]['sha256']==v
                        for n,v in world['files_sha256'].items()),'Actual original active-world file witness differs')
    require(paused['status']=='audited-paused-attachment-lifetime-facet-only' and len(paused['worlds'])==20 and paused['real_F5_reloads']==19 and
            paused['actual_simulator_pid']>0 and paused['actual_exitcode']==0 and paused['owning_bytes_unchanged'] is True and
            paused['no_preload_observer'] is True and paused['sanitizer_suppressions'] is False,'Every original paused graph and actual F5 dispatch required')
    for index,world in enumerate(paused['worlds'],1):
        life=world['lifecycle'];require(life['context_deleted'] is True and life['rendered_frames']==life['successful_presents']>=60,
                                     'Every paused original world must retain complete presents and clean context')
        prefix='native-class-paused/'+profile+'/'+('' if index==1 else 'session-'+str(index)+'/')
        require(all(raw[prefix+n]['sha256']==v for n,v in world['files_sha256'].items()),'Actual original paused-world file witness differs')
    scope=proof['original_facets'];prefix='/home/runner/work/orbiter-cross-platform/orbiter-cross-platform/out/'
    require(all(n.startswith(prefix) and raw[n.removeprefix(prefix)]['sha256']==v for n,v in scope['metadata_sha256'].items()),
            'Original scope metadata witness differs')
    require(all(c['actual_pid']>0 and c['actual_returncode']==0 and not c.get('timed_out') and
                sha(folder/(c['label']+'.log'))==c['log_sha256'] for c in proof['commands']),
            'Every actual independent provisioning/auditing command and log required')
    core=proof['auditor_core_source_identity']
    require(core['collector_source']==pin['source'] and core['complete_locked_source_count']==623 and core['actual_core_sources_identical'] is True,
            'Complete original core source equivalence required')
    capture=prefix+'native-class-lifetimes/'+profile+'/lifetimes.json'
    return dict(capture=capture,audit=family),dict(source=pin['source'],run_id=pin['run_id'],artifact_id=pin['artifact_id'],
        archive_sha256=pin['archive_sha256'],independent_proof_sha256=sha(folder/'proof.json'),raw_members=proof['actual_raw_members'],
        raw_decoded_bytes=proof['actual_raw_decoded_bytes'],paused_audit=paused,decoded_metadata_sha256=members,
        capture_source=capture_lock['source'],compiled_runtime_source=original.COMPILED,core_sources=core)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
                            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual independent standard hosted worker required')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out'),'Fresh independent positive coverage output required')
    a.output.mkdir(parents=True);lock=load(LOCK);require(set(lock['profiles'])==set(PROFILES),'All four exact independent profile inputs required')
    conserved=original.conserved_sources();core=source_identity();captures=[];proofs={}
    final_api=load(a.inputs/'capture-final-api.json');capture_lock=load(ROOT/'Tests/Production/Closeout/class-lifetime-inputs-v1.lock.json')
    run=final_api['run'];jobs=final_api['jobs']
    require(run['id']==capture_lock['run_id'] and run['head_sha']==capture_lock['source'] and run['head_branch']==capture_lock['branch'] and
            run['path']==capture_lock['workflow'] and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and
            len(jobs)==5 and len({j['id'] for j in jobs})==5 and
            all(str(j['id']) in capture_lock['jobs'] and j['name']==capture_lock['jobs'][str(j['id'])] and j['run_id']==run['id'] and
                j['head_sha']==run['head_sha'] and j['status']=='completed' and j['conclusion']=='success' and j['labels']==['ubuntu-24.04'] for j in jobs),
            'The full original four-profile producer must be actually complete before matrix closure')
    for profile in PROFILES:
        capture,proof=inspect_profile(profile,a.inputs/profile,lock['profiles'][profile]);captures.append(capture);proofs[profile]=proof
        require({k:v for k,v in proof['core_sources'].items() if k!='collector_source'}=={k:v for k,v in core.items() if k!='collector_source'},
                'Every actual native/current-Windows compiled core must remain identical')
    cases={c['id']:c for c in load(ROOT/'Tests/Production/RemainingStock/cases.json')['cases']}
    specification=requirements()['class-eligibility'];families=family_coverage(captures,specification,original.FAMILY_CASES,cases)
    passed=['source-abi','resource-ownership','twenty-cycle-teardown']
    report=dict(protocol='phase6-renewed-independent-positive-class-lifetime-matrix-v1',
        status='verified-four-profile-original-positive-and-paused-class-lifetime-facets-only',auditor_source=os.environ['GITHUB_SHA'],
        original_capture_source=capture_lock['source'],compiled_runtime_source=original.COMPILED,original_capture_run_id=run['id'],
        families=families,profiles=proofs,passed_positive_facets=passed,
        remaining_class_facets=[n for n in specification['required'] if n not in passed],actual_original_simulator_processes=32,
        active_worlds=560,paused_worlds=80,real_F5_reloads=76,active_successful_presents=33600,
        actual_raw_members=sum(p['raw_members'] for p in proofs.values()),actual_raw_decoded_bytes=sum(p['raw_decoded_bytes'] for p in proofs.values()),
        original_auditors_conserved=conserved,original_full_capture_api_sha256=sha(a.inputs/'capture-final-api.json'),
        exact_independent_profile_input_lock_sha256=sha(LOCK),new_simulator_processes=0,
        unavailable_historical_HST_canary_not_relabelled=True,historical_23_evidence_records_not_restored=True,
        scope='Four fresh complete seven-scene scopes replace no old capture identity. Unchanged original family_coverage verifies every family/profile/twenty-world cell; exact original active and paused audits independently reexecuted from published raw inputs. Capabilities, interactions, persistence, rejection, normal admission and final acceptance remain pending.',
        complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    require(len(families)==11 and all(len(v)==4 for v in families.values()),'Every original family and profile required')
    require(original.conserved_sources()==conserved and source_identity()==core,'Actual owning source changed during coverage audit')
    atomic_json(a.output/'positive-class-lifetimes.json',report);print(report['status'])


if __name__=='__main__':main()
