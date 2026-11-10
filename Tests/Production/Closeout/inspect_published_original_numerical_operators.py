#!/usr/bin/env python3
"""Independently read every published actual original-operand result, without compiling or simulating."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import subprocess
from contracts import ROOT,require,load,sha,atomic_json
from inspect_published_numerical_observers import restore_outer
import replay_original_numerical_operators as original

SOURCE='6185094a02e0358dc93383b273a54b9508dbb448'
RUN=42917970279
JOB=130185201050
ARTIFACT=13810297717
ARCHIVE_BYTES=4372705
DIGEST='7f6ca9f51bffe203857adb129e4d6f4a713d1cdb09c44a9f294ffe3fff5a6c32'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('api','archive','output'):p.add_argument('--'+n,type=lambda s:Path(s).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists(),'Fresh standard hosted independent raw audit only');a.output.mkdir(parents=True)
    api=load(a.api);run=api['run'];jobs=api['jobs'];artifact=api['artifact'];require(api['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/numerical-original-operator-replay-v1' and run['path']=='.github/workflows/phase6-numerical-original-operator-replay.yml' and run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1 and len(jobs)==1 and jobs[0]['id']==JOB and jobs[0]['head_sha']==SOURCE and jobs[0]['run_id']==RUN and jobs[0]['conclusion']=='success' and jobs[0]['status']=='completed' and jobs[0]['labels']==['ubuntu-24.04'],'Exact completed standard source-bound original primitive job required')
    require(artifact['id']==ARTIFACT and artifact['expired'] is False and artifact['name']=='original-observed-operators-complete-raw-witness' and artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE and artifact['size_in_bytes']==a.archive.stat().st_size==ARCHIVE_BYTES and artifact['digest']=='sha256:'+DIGEST and sha(a.archive)==DIGEST,'Exact complete published original raw ZIP required')
    payload=a.output/'payload';members=restore_outer(a.archive,payload,'');base=payload/'original-observed-operators';r=load(base/'verification.json');require(r['source']==SOURCE and r['status']=='replayed-exact-complete-original-observed-primitive-sequences-only' and r['old_source']==original.OLD and r['fixed_source']==original.FIXED and r['new_simulator_processes']==0 and r['complete_numerical_reload_gate_qualified'] is False,'Exact original full scoped result required')
    for path in (Path(original.__file__),*original.CORPUS.iterdir()):
        require(path.is_file() and path.read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+path.relative_to(ROOT).as_posix()]),'Every actual original producer reader and operand byte required')
    manifest=load(original.CORPUS/'provenance.json');require(sha(original.CORPUS/'provenance.json')==r['original_operand_manifest_sha256'] and sha(base/'observed-operands.csv')==r['observed_input_sha256'],'Exact original sealed operand/source tables required');items=list(original.operands(manifest))
    with (base/'observed-operands.csv').open(newline='') as stream:
        reader=csv.reader(stream);require(next(reader)==['tag','function','x','y'] and [tuple(v) for v in reader]==[v for _,v in items],'Every actual original ordered operand must be re-read')
    actual={};fixed={}
    for role in ('old','fixed'):
        value,actual[role]=original.compare_results(base/('observe-'+role+'-all-original-inputs.log'),items,manifest,role)
        lib=base/('old-reference-math.a' if role=='old' else 'fixed-build/liborbiter_reference_math.a');value.update(actual_observer_executable_sha256=sha(base/(role+'-native-values')),actual_native_math_archive_sha256=sha(lib));require(value==r['actual_measured_results'][role],'Every actual original compiled observer/result digest must reproduce');fixed[role]=value
    changes=[dict(group=g,tag=v[0],function=v[1],y=v[2],x=v[3],old=l,fixed=b) for (g,v),l,b in zip(items,actual['old'],actual['fixed'],strict=True) if l!=b]
    require(len(items)==85008 and changes==[r['unique_first_sampled_operation_difference']] and changes[0]==dict(group='surface',tag='211|Atlantis-SRB1|longitude',function='atan2',y='c1550c2a4f069879',x='412bcfdda20e1e30',old='bff6837bee57350a',fixed='bff6837bee573509'),'Exactly the original first differing sampled operation required')
    receipts=set()
    for item in r['commands']:
        name=item['name'];path=base/(name+'-process.json');process=load(path);seen=[v for v in process['owned_process_identities'] if v['pid']==process['actual_collector_pid']];require(len(seen)==1 and seen[0]['pid']==item['actual_pid'] and seen[0]['start_ticks']==item['start_ticks']>0 and seen[0]['argv']==item['argv'] and process['terminal'] is True and process['cancelled'] is False and process['actual_returncode']==0 and sha(path)==item['receipt_sha256'] and sha(base/(name+'.log'))==item['log_sha256'] and sha(base/(name+'.stderr'))==item['stderr_sha256'],'Every actual original process/output source receipt required');receipts.add((item['actual_pid'],item['start_ticks']))
    require(len(receipts)==len(r['commands'])==8,'Distinct original actual build and observer process identities required')
    for name,digest in r['actual_corrected_source_sha256'].items():require(sha(base/'fixed-source'/name)==digest==hashlib.sha256(subprocess.check_output(['git','show',original.FIXED+':'+name])).hexdigest(),'Every actual corrected source body required')
    require((base/'NativeValues.cpp').read_bytes()==subprocess.check_output(['git','show',original.OLD+':Tests/Production/ReloadMath/NativeValues.cpp']) and sha(base/'NativeValues.cpp')==r['original_readonly_observer_source_sha256'],'Unchanged original observer source required')
    controls=load(payload/'original-observed-operators-controls.json');require(controls['tests_run']==469 and controls['producer_commit']==SOURCE and controls['sources_match_producer'] is True and controls['status']=='passed' and all(controls[n]==0 for n in ('skipped','failures','errors')),'Original complete469 source checks required')
    require(all(sha(payload/n)==v['sha256'] for n,v in members.items()) and sha(a.archive)==DIGEST,'Every actual original raw member and archive must remain unchanged')
    atomic_json(a.output/'original-members.json',members);atomic_json(a.output/'verification.json',dict(protocol='phase6-independent-complete-original-operator-replay-v1',status='independently-verified-all-original-observed-primitive-results-only',auditor_source=os.environ['GITHUB_SHA'],original_source=SOURCE,original_run_id=RUN,original_job_id=JOB,original_artifact=artifact,actual_original_complete_raw_members=len(members),original_qualification_report_sha256=sha(base/'verification.json'),original_result_rows_verified=170016,original_samples_per_binding=r['actual_samples_per_binding'],actual_original_process_receipts_verified=8,actual_original_primitive_processes=2,actual_fixed_and_old_bit_sequences_verified=fixed,unique_first_sampled_operation_difference=changes[0],original_historical_full_state_trajectory_relabelled=False,all_original_tolerances_and_sources_unchanged=True,new_simulator_or_build_processes=0,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False));print('independently-verified-all-original-observed-primitive-results-only')


if __name__=='__main__':main()
