#!/usr/bin/env python3
"""Fresh v2 normal admission through every unchanged original stock reader/policy."""
import csv,hashlib,json,math,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'Tests/Production/Closeout')]
from contracts import require,sha,load,atomic_json
from PhysicsV2.transforms import replace_once
from PhysicsV2.source import validate_current
import hosted_normal_admission as original
from frozen_admission_api import REFERENCE
RUNTIME=json.loads((HERE/'origins.json').read_text())['native']['source']
EXIT=ROOT/'out/frozen-stock-exit'


def version_lock():
    validate_current();body=dict(physics=load(HERE/'version.json'),origins=load(HERE/'origins.json'))
    return dict(id=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest(),**body)


def verify_units(profile):
    proof=load(ROOT/'out/physics-v2-unit-recheck'/profile/'verification.json')
    require(proof['status']=='passed-original-evidence-reader-with-original60second-deadline' and proof['profile']==profile and proof['actual_returncode']==0 and proof['original_timeout_seconds']==60 and
        proof['original32tests_complete_with_prior31passes'] is True and proof['original_failure_preserved'] is True and proof['original_native_sanitizers_unchanged'] is True and all(sha(p)==h for p,h in proof['prior_guarded_files_sha256'].items()),'Every original unit must be resolved with its preserved exact actual earlier failure before any scenario capture')
    return proof


def verify_scope(capture,audit,profile,lock):
    verify_units(profile)
    report=load(capture/'stock-scenarios.json');observed=load(audit);restored=load(ROOT/'out/physics-v2-input/native'/profile/'restoration.json')
    require(report['status']==observed['status']=='passed' and report['summary']==observed['summary'] and report['summary']['attempted']==report['summary']['passed']==report['summary']['inventory_ready']==157 and
        report['summary']['failed']==0 and report['diagnostic_only'] is observed['diagnostic_only'] is False and report['execution_protocol']=='normal-stock-capture-v4' and report['backend']=='wayland' and
        report['runtime_identity']['runtime_source_commit']==RUNTIME and report['runtime_identity']['profile']==profile and report['runtime_identity']['sanitizer_linked'] is True and
        report['runtime_identity']['build_record_sha256']==restored['build_manifest_sha256'] and report['sources_and_binaries_unchanged'] is True and observed['capture_sha256']==sha(capture/'stock-scenarios.json'),'All actual fresh v2 157-scenario launches and unchanged original independent audit required')
    expected={p['path'] for p in load(ROOT/'Tests/Production/production-source.lock.json')['scenarios']}
    require(set(report['cases_requested'])==set(report['cases'])==expected=={r['scenario'] for r in observed['runs']} and len(expected)==157 and
        sum(c.get('intentional_exit') is not None for c in report['cases'].values())==1 and sum(c.get('general_api_startup_exit') is not None for c in report['cases'].values())==1,'Complete original scenario roster and both unchanged exit policies required')
    pids=set();finite={};failed=load(ROOT/'Tests/Production/Closeout/failed-normal-admission-v4.lock.json')['failed_cases']
    for name,c in report['cases'].items():
        folder=capture/c['output'];receipt=load(folder/'process-receipt.json')
        require(c['status']=='passed' and not c['problems'] and receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and receipt['actual_collector_pid'] not in pids,'Every actual original normal launch must terminate cleanly once')
        pids.add(receipt['actual_collector_pid']);console=(folder/'console.log').read_text(errors='replace')
        require(not any(mark in console for mark in ('runtime error:','ERROR: AddressSanitizer:','ERROR: LeakSanitizer:','Native module rejected','Cannot load native module','Native module initialization failed','Missing native module entry')),'Unsuppressed clean actual runtime and all classes required')
        if name in failed:
            with (folder/'flight-state.csv').open() as stream:rows=list(csv.DictReader(stream))
            require(rows and {int(r['tick']) for r in rows}==set(range(61)),'All original ticks required for the four repaired scenes')
            for row in rows:
                for key,value in row.items():
                    if key not in ('object','class'):require(value is not None and math.isfinite(float(value)),'Nonfinite corrected-scene state: '+name+' '+key)
            finite[name]=dict(rows=len(rows),all_original61ticks=True,every_numeric_column_finite=True)
    return dict(version_id=lock['id'],physics_version='assembly-contact-v2',profile=profile,actual_normal_launches=len(pids),original_stock_cases=len(expected),four_original_failures_complete_finite=finite,
        capture_sha256=sha(capture/'stock-scenarios.json'),independent_audit_sha256=sha(audit),unchanged_original_policies_and_readers=True,published_raw_independent_audit_pending=True,qualification_granted=False)


def prepared_body():
    body=original.prepared_body()
    body=replace_once(body,"protocol='phase6-frozen-native-normal-admission-v1'","protocol='phase6-versioned-physics-v2-normal-admission'")
    body=body.replace("'ccc02c8a34bd1f227624d8778a141e8736ae8111'",repr(RUNTIME))
    body=replace_once(body,"from hosted_native_runtime_dependencies import install as install_native_runtime,verify as verify_native_runtime","from runtime_dependencies import install as install_native_runtime,verify as verify_native_runtime")
    body=replace_once(body,'from hosted_normal_admission import candidate,verify_scope,REFERENCE,EXIT,RUNTIME','from native_capture import version_lock,verify_scope,REFERENCE,EXIT,RUNTIME')
    body=replace_once(body,"lock=candidate();report['candidate_id']=lock['id'];save()","lock=version_lock();report['version_id']=lock['id'];save()")
    body=replace_once(body,"build=ROOT/'out/phase6-hosted-native'/a.profile","build=ROOT/'out/phase6-physics-v2-native'/a.profile")
    body=replace_once(body,"restore=load(ROOT/'out/native-api-source/native/candidate-restoration.json')","restore=load(ROOT/'out/physics-v2-input/native'/a.profile/'restoration.json')")
    body=replace_once(body,"restore['candidate_id']==lock['id'] and restore['profile']==a.profile and restore['build_record_sha256']==sha(build/'build.json')","restore['physics_version']=='assembly-contact-v2' and restore['profile']==a.profile and restore['compiled_source']==RUNTIME and restore['build_manifest_sha256']==sha(build/'build.json')")
    body=replace_once(body,"require(candidate()==lock,'Frozen application/reference/source lock changed')","require(version_lock()==lock,'Versioned application/reference/source lock changed')")
    body=replace_once(body,"status='captured-and-audited-full-normal-admission-profile-only'","status='captured-and-audited-fresh-v2-full-normal-profile-only'")
    return body


def prepare(profile):
    original.prepare_snapshot(profile)
    folder=ROOT/'out/admission-package-source'/profile
    bootstrap=(ROOT/'Tests/Production/Closeout/prepare_hosted_normal_admission.sh').read_text()
    bootstrap=replace_once(bootstrap,'Tests/Production/Closeout/hosted_normal_admission.py','Tests/Production/PhysicsV2/native_capture.py')
    (folder/'physics-v2-bootstrap.sh').write_text(bootstrap)
    network=(folder/'network.sh').read_text();network=network.replace('Tests/Production/Closeout/prepare_hosted_normal_admission.sh','out/admission-package-source/$PROFILE/physics-v2-bootstrap.sh')
    (folder/'physics-v2-network.sh').write_text(network)
    (folder/'physics-v2-generated-capture.py').write_text(prepared_body())
    paths=[HERE/'native_capture.py',HERE/'runtime_dependencies.py',folder/'physics-v2-bootstrap.sh',folder/'physics-v2-network.sh',folder/'physics-v2-generated-capture.py']
    (folder/'physics-v2-before.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in paths))


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux','Hosted v2 capture only')
    require(len(sys.argv)==3 and sys.argv[1] in ('--prepare','--profile'),'Explicit v2 preparation/profile required');profile=sys.argv[2]
    verify_units(profile)
    if sys.argv[1]=='--prepare':prepare(profile);return
    try:exec(compile(prepared_body(),str(HERE/'native_capture.py'),'exec'),{'__name__':'__main__','__file__':str(HERE/'native_capture.py')})
    finally:original.preserve(profile)


if __name__=='__main__':main()
