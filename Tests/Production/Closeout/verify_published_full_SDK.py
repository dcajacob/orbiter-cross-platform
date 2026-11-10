#!/usr/bin/env python3
"""Verify full published SDK/source-witness receipts on GitHub and emit a small separate proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import stat
import subprocess
import zipfile
from contracts import ROOT,load,sha,require,atomic_json
import hosted_full_sdk_audit as sdk

LOCK=ROOT/'Tests/Production/Closeout/full-SDK-published-inputs-v1.lock.json'
CI=PurePosixPath('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')


def validate_api(record,mode):
    lock=load(LOCK);require(mode in lock['cohorts'],'Only explicitly completed published SDK cohorts may be verified')
    pin=lock['cohorts'][mode];run=record['run'];jobs=record['jobs'];a=record['artifact']
    require(record['repository']==lock['repository'] and run['id']==lock['run_id'] and run['head_sha']==lock['source'] and
            run['head_branch']==lock['branch'] and run['path']==lock['workflow'] and run['run_attempt']==1 and
            run['status'] in ('queued','in_progress','completed') and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and
            len(jobs)==2 and {str(j['id']):j['name'] for j in jobs}==lock['jobs'] and
            all(j['run_id']==run['id'] and j['head_sha']==run['head_sha'] and j['labels']==['ubuntu-24.04'] for j in jobs),
            'Exact complete published SDK run/source/job identities required; other job status is preserved')
    selected=next(j for j in jobs if j['id']==pin['job_id'])
    require(selected['status']=='completed' and selected['conclusion']=='success' and a['id']==pin['artifact_id'] and
            a['name']=='full-original-native-SDK-variants-'+mode and a['expired'] is False and
            a['size_in_bytes']==pin['archive_bytes'] and a['digest']=='sha256:'+pin['archive_sha256'] and
            a['workflow_run']['id']==run['id'] and a['workflow_run']['head_sha']==run['head_sha'],
            'Only exact completed source-bound SDK artifact bytes may be independently verified')
    return lock,pin


def inspect_members(archive):
    members={};bodies={};seen=set()
    with zipfile.ZipFile(archive) as source:
        require(len(source.infolist())<10000 and sum(i.file_size for i in source.infolist())<512*1024**2,'Bounded full published SDK/source metadata required')
        for info in source.infolist():
            name=info.filename;p=PurePosixPath(name)
            require(not info.is_dir() and name and str(p)==name and not p.is_absolute() and '..' not in p.parts and
                    ':' not in name and '\\' not in name and name.casefold() not in seen and
                    not stat.S_ISLNK(info.external_attr>>16) and not (info.external_attr>>16)&0o7000,
                    'Unsafe duplicate redirected or privileged published SDK member')
            seen.add(name.casefold());body=source.read(info);members[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body));bodies[name]=body
    return members,bodies


def summarize(record,mode,bodies):
    source=record['run']['head_sha'];report_name='class-full-SDK-variant-audits/'+mode+'.json'
    report=json.loads(bodies[report_name]);inventory=json.loads(bodies['class-capability-inventory/reference/inventory.json'])
    controls=json.loads(bodies['full-SDK-controls.json'])
    require(report['protocol']=='phase6-independent-full-original-native-initial-SDK-and-ports-v1' and
            report['status']=='passed-two-profile-full-original-native-initial-SDK-and-ports-only' and
            report['auditor_source']==source and report['math_profile']==mode and report['actual_initial_pairs']==152 and
            report['new_simulator_processes']==0 and report['all_22_full_17_field_variants_pending'] is False and
            report['all_22_full_17_field_variants_replayed'] is True and
            report['all_historical_source_guards_verified_at_original_commit'] is True and
            report['all_current_sources_separately_verified_at_auditor_commit'] is True and
            report['original_nine_scene_144_process_controls_pending'] is True and
            all(report[k] is False for k in ('complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')),
            'Complete published narrow SDK replay required; observer controls and broader acceptance remain pending')
    require(controls['status']=='passed' and controls['tests_run']==343 and controls['producer_commit']==source and
            controls['sources_match_producer'] is True and controls['failures']==controls['errors']==controls['skipped']==0,
            'Every original and source-owner negative control required at immutable replay source')
    cache={}
    def body(commit,name):
        key=(commit,name)
        if key not in cache:cache[key]=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+name])
        return cache[key]
    for name,value in controls['sources_sha256'].items():
        relative=PurePosixPath(name).relative_to(CI).as_posix()
        require(hashlib.sha256(body(source,relative)).hexdigest()==value,'Published control source differs from its immutable owner')
    require((ROOT/'Tests/Production/Closeout/hosted_full_sdk_audit.py').read_bytes()==body(source,'Tests/Production/Closeout/hosted_full_sdk_audit.py') and
            report['original_sources_sha256']==sdk.original_sources(), 'All original SDK/port/physical comparators must remain exact')
    profiles={};witnesses={};families={row[0] for row in inventory['unique_signatures']}
    require(set(report['profiles'])=={c+'-'+mode for c in ('Debug','Release')},'Both complete configurations required')
    for profile,value in report['profiles'].items():
        require(value['status']=='passed-full-original-native-initial-SDK-and-ports-only' and
                value['captured_normal_role']=='normal' and value['captured_diagnostic_only'] is False,
                'Original full normal capture scope must remain unrelabelled')
        signatures=set()
        for runs in value['cases'].values():
            for run in runs:
                require(len(run['files_sha256'])==6,'Both complete original/native SDK and docking/attachment inputs required')
                for row in run['actual_capabilities'].values():
                    require(set(row)=={'class',*sdk.reference.FIELDS},'All original seventeen exact SDK fields required')
                    if row['class'] in families:signatures.add((row['class'],*(float(row[k]) for k in sdk.reference.FIELDS)))
        summary=sdk.coverage(profile,value['cases'],signatures,signatures,inventory)
        require(json.loads(json.dumps(summary))==value['coverage'],'Every complete SDK comparison and full variant must be represented')
        bindings=report['historical_source_bindings'][profile]
        require(bindings,'Every recorded historical source guard must remain represented')
        for original_name,entry in bindings.items():
            relative=sdk.source_relative(original_name);name='class-full-SDK-source-witnesses/'+profile+'/'+relative
            require(entry['relative']==relative and entry['historical_source']==sdk.matrix_cli.matrix.SOURCE and entry['current_source']==source and
                    entry['historical_report_rewritten'] is False and entry['current_file_replaced'] is False and
                    hashlib.sha256(bodies[name]).hexdigest()==entry['historical_sha256']==hashlib.sha256(body(entry['historical_source'],relative)).hexdigest() and
                    hashlib.sha256(body(source,relative)).hexdigest()==entry['current_sha256'],
                    'Every historical/current source owner and published witness byte must remain exact')
            require(report['guarded_inputs_sha256'][entry['immutable_historical_witness']]==entry['historical_sha256'] and
                    report['guarded_inputs_sha256'][str(CI/relative)]==entry['current_sha256'],
                    'Every historical and current source guard must be retained through replay completion')
            witnesses[name]=entry['historical_sha256']
        profiles[profile]=summary|dict(native_capture_sha256=value['capture_sha256'],
            raw_native_archive_sha256=value['raw_native_binding']['raw_proof']['archive_sha256'],
            prior_physical_phase_artifact_id=value['prior_physical_phase_artifact_id'],prior_physical_report_sha256=value['prior_physical_report_sha256'])
    return dict(profiles=profiles,actual_initial_pairs=152,full_variants_per_profile=22,fields=list(sdk.reference.FIELDS),
                source_controls_passed=343,historical_source_guards_verified=sum(len(v) for v in report['historical_source_bindings'].values()),
                published_source_witnesses_sha256=witnesses,full_report_sha256=hashlib.sha256(bodies[report_name]).hexdigest(),
                full_inventory_sha256=hashlib.sha256(bodies['class-capability-inventory/reference/inventory.json']).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True);a=p.parse_args()
    head=sdk.matrix_cli.context();base=ROOT/'out/full-SDK-published'/a.math_profile;record=load(base/'api.json');lock,pin=validate_api(record,a.math_profile)
    archive=base/'producer.zip';require(archive.stat().st_size==pin['archive_bytes'] and sha(archive)==pin['archive_sha256'],'Actual complete published SDK ZIP digest differs')
    output=ROOT/'out/full-SDK-published-verification'/a.math_profile;require(not output.exists(),'Fresh separate small publication proof required');output.mkdir(parents=True)
    proof=dict(protocol='phase6-verified-published-full-original-native-SDK-cohort-v1',status='running',auditor_source=head,math_profile=a.math_profile,
        producer_source=lock['source'],producer_run_id=lock['run_id'],producer_job_id=pin['job_id'],producer_artifact_id=pin['artifact_id'],
        producer_archive_bytes=pin['archive_bytes'],producer_archive_sha256=pin['archive_sha256'],source_api_sha256=sha(base/'api.json'),
        new_simulator_processes=0,original_nine_scene_144_process_controls_pending=True,complete_class_eligibility_qualified=False,
        normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(output/'proof.json',proof)
    save()
    try:
        members,bodies=inspect_members(archive);proof.update(summarize(record,a.math_profile,bodies));atomic_json(output/'members.json',members)
        require(sha(archive)==pin['archive_sha256'],'Published SDK archive changed during independent verification')
        proof.update(status='verified-published-complete-two-profile-SDK-and-port-variants-only',members_sha256=sha(output/'members.json'),
                     producer_run_status=record['run']['status'],producer_run_conclusion=record['run']['conclusion'])
    except BaseException as error:proof.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(proof['status']+' '+a.math_profile)


if __name__=='__main__':main()
