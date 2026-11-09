#!/usr/bin/env python3
"""Materialize source-bound evidence namespaces and run the unchanged original API qualifier."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path,PurePosixPath,PureWindowsPath
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/GeneralApiCorrection'),
             str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import require,sha,load
import qualification
import inspect_hosted_native_general_api as native
import restore_hosted_native_providers as providers
import restore_hosted_mesa_topology as mesa
import inspect_published_general_api as windows
import audit_hosted_general_api as cases
import replay_published_general_api as replay
import restore_sdk
from retain_hosted_sdk import unit_result
from hosted_native_general_api import source_identity

LOCK=Path(__file__).with_name('joint-api-inputs-v1.lock.json')
QUALIFIER_SHA256='4e13d325912ef33bfbe69d3448bfdf63443b3f95d82e22cdc2e9a325b32e634e'
NATIVE_ROOT=PurePosixPath('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')
WINDOWS_ROOT=PureWindowsPath('D:/a/orbiter-cross-platform/orbiter-cross-platform')
PROFILES=sorted(qualification.PROFILES)
NATIVE_FINAL='f5172e3ed0ae814b52b10cc2557e294e30d310bf'
INPUTS=ROOT/'out/joint-api-inputs'
OUTPUT=ROOT/'out/joint-api-qualification'
WORK=ROOT/'out/joint-api-work'


def validate_input(name,record):
    lock=load(LOCK);require(name in lock['inputs'] and record['repository']==lock['repository'],'Exact joint input namespace/repository required')
    pin=lock['inputs'][name];run=record['run'];artifact=record['artifact']
    require((run['id'],run['head_sha'],run['head_branch'],run['path'],run['run_attempt'],run['status'],run['conclusion'])==
        (pin['run_id'],pin['source'],pin['branch'],pin['workflow'],1,'completed','success'),'Exact actual completed joint input producer required')
    require((artifact['id'],artifact['name'],artifact['size_in_bytes'],artifact['digest'],artifact['expired'],
        artifact['workflow_run']['id'],artifact['workflow_run']['head_sha'])==
        (pin['artifact_id'],pin['artifact_name'],pin['archive_bytes'],'sha256:'+pin['archive_sha256'],False,pin['run_id'],pin['source']),
        'Exact actual published joint input artifact required')
    jobs=record['jobs'];require(len(jobs)==len(pin['jobs']) and len({j['id'] for j in jobs})==len(jobs),'Complete actual joint input job roster required')
    for job in jobs:
        expected=pin['jobs'].get(str(job['id']))
        require(expected is not None and job['run_id']==pin['run_id'] and job['head_sha']==pin['source'] and
            {k:job[k] for k in ('name','status','conclusion','labels')}==expected and
            set(job['labels'])<={'ubuntu-24.04','windows-2025'} and job['labels'],'Exact actually completed standard-runner input job required')
    if pin['family']=='native-capture':native.validate_api(record,name.removeprefix('native-'))
    elif pin['family']=='providers':providers.validate_api(record)
    elif pin['family']=='mesa':mesa.validate_api(record)
    elif pin['family']=='windows-sdk':restore_sdk.validate_api(record,name.removeprefix('sdk-'))
    elif pin['family']=='windows-audit':windows.validate_api(record,name.removeprefix('windows-audit-'))
    return pin


def zip_members(archive,target,max_bytes=4*1024**3):
    require(not target.exists(),'Fresh actual source artifact restoration required');target.mkdir(parents=True)
    files={};seen=set()
    with zipfile.ZipFile(archive) as incoming:
        require(len(incoming.infolist())<50000 and sum(i.file_size for i in incoming.infolist())<max_bytes,'Bounded complete source artifact required')
        for item in incoming.infolist():
            if item.is_dir():continue
            restore_sdk.safe(item.filename)
            require(item.filename.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16),'Duplicate/colliding/symlink source member')
            seen.add(item.filename.casefold());path=target/item.filename;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(incoming.read(item));files[item.filename]=sha(path)
    require(files,'Actual nonempty source artifact required');return files


def origin(name,kind,**details):
    pin=load(LOCK)['inputs'][name]
    return dict(kind=kind,input_namespace=name,source=pin['source'],run_id=pin['run_id'],artifact_id=pin['artifact_id'],
        archive_sha256=pin['archive_sha256'],**details)


def materialize_audit(original_body,scope,destination,resolver,source_origin):
    require(scope in {'native-'+p for p in PROFILES}|{'windows-Debug','windows-Release'},'Explicit cohort/configuration/profile evidence namespace required')
    require(not destination.exists(),'Fresh scoped materialized evidence required');destination.mkdir(parents=True)
    raw=destination/'original-audit.json';raw.write_bytes(original_body);report=json.loads(original_body)
    require(report['evidence_sha256'],'Complete original evidence map required')
    evidence={};mapping={}
    for index,(old_name,expected) in enumerate(sorted(report['evidence_sha256'].items())):
        actual,details=resolver(old_name)
        require(isinstance(actual,(bytes,Path)),'Resolver must supply actual bytes or a real file, never expected hashes')
        target=destination/('evidence-'+str(index).zfill(4)+'.bin')
        if isinstance(actual,bytes):target.write_bytes(actual)
        else:
            actual=actual.resolve();require(actual.is_file() and not actual.is_symlink(),'Actual real source member required')
            os.link(actual,target)
        actual_sha256=sha(target)
        if actual_sha256!=expected:
            (destination/'materialization-failure.json').write_text(json.dumps(dict(original_path=old_name,
                expected_sha256=expected,actual_sha256=actual_sha256,actual_preserved_file=str(target),origin=details),indent=2)+'\n')
        require(actual_sha256==expected,'Actual materialized evidence byte differs: '+old_name)
        evidence[str(target)]=expected
        mapping[old_name]=dict(materialized_path=str(target),sha256=expected,origin=details)
    derived=copy.deepcopy(report);derived['evidence_sha256']=evidence
    derived['materialized_evidence_protocol']='phase6-joint-GeneralApi-scoped-actual-bytes-v1'
    derived['original_audit_sha256']=hashlib.sha256(original_body).hexdigest()
    derived['original_evidence_sha256']=report['evidence_sha256']
    derived['derivation']=dict(scope=scope,origin=source_origin,original_report=str(raw),
        observation_source_roles_process_IDs_and_results_unchanged=True,new_simulator_processes_launched=0)
    path=destination/'materialized-audit.json';path.write_text(json.dumps(derived,indent=2)+'\n')
    require(raw.read_bytes()==original_body and all(sha(p)==v for p,v in evidence.items()),'Original audit or actual materialized evidence changed')
    return path,dict(scope=scope,original_audit_path=str(raw),original_audit_sha256=sha(raw),
        materialized_audit_path=str(path),materialized_audit_sha256=sha(path),original_to_materialized=mapping)


def verify_native_final(folder):
    base=folder/'native-api-final-proof';proof=load(base/'proof.json')
    require(proof['protocol']=='phase6-independent-published-native-GeneralApi-matrix-v1' and
        proof['status']=='verified-complete-native-GeneralApi-subset-only' and proof['auditor_source']==NATIVE_FINAL and
        proof['github_run_id']==42705320489 and set(proof['profiles'])==set(PROFILES) and proof['actual_original_and_corrected_processes']==8 and
        proof['every_original_assertion_startup_policy_sanitizer_and_failure_preserved'] is True and
        proof['qualification_granted'] is False and proof['complete_general_api_qualification'] is False and proof['phase6_complete'] is False,
        'Complete independently published four-profile native API proof required')
    require(all(sha(base/n)==v for n,v in proof['proof_member_sha256'].items()),'Every native proof metadata member must match')
    for name,value in proof['source_sha256'].items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',NATIVE_FINAL+':'+name])
        require(hashlib.sha256(body).hexdigest()==value,'Original native publication owning source differs')
    return base,proof


def native_audit(profile,base):
    name='native-'+profile;archive=INPUTS/name/'producer.zip'
    metadata=base/'profiles'/profile/'native-api-independent'/profile
    published=load(metadata/'proof.json')
    independent=(metadata/'independent-native-api-audit.json').read_bytes()
    require(published['status']=='verified-published-native-GeneralApi-profile-only' and published['profile']==profile and
        published['auditor_source']==NATIVE_FINAL and published['original_collector_source']==native.SOURCE and
        published['original_run_id']==native.RUN and published['reexecuted_original_audit_same_bytes'] is True and
        published['independent_audit_sha256']==published['original_audit_sha256']==hashlib.sha256(independent).hexdigest() and
        published['all_original_source_runtime_provider_and_evidence_bytes_unchanged'] is True and published['actual_processes']==2 and
        (published['original_job_id'],published['original_artifact_id'],published['original_archive_bytes'],published['original_archive_sha256'])==native.PINS[profile],
        'Original native independent byte-for-byte audit proof required')
    def resolve(old):
        path=PurePosixPath(old);require(path.is_absolute() and '..' not in path.parts and path.is_relative_to(NATIVE_ROOT),'Original native evidence origin outside its actual workspace')
        relative=path.relative_to(NATIVE_ROOT).as_posix()
        if relative.startswith('Tests/Production/GeneralApiCorrection/'):
            require(Path(relative).name in ('capture_native.py','prepare.py','startup_contract.py','startup-policy-v1.json'),'Unexpected original native source evidence')
            body=subprocess.check_output(['git','-C',str(ROOT),'show',native.SOURCE+':'+relative])
            return body,dict(kind='immutable-git-blob',source=native.SOURCE,path=relative)
        if relative.startswith(providers.PREFIX+'/') or relative.startswith(mesa.PREFIX+'/'):
            family='providers' if relative.startswith(providers.PREFIX+'/') else 'mesa'
            record=load(ROOT/('out/joint-api-work/'+family+'-restoration.json'))
            require(relative in record['members'],'Actual provider member absent from its full restored closure')
            return ROOT/relative,origin(family,'restored-original-provider-member',member=relative,
                original_link=record['members'][relative]['symlink'])
        require(relative.startswith('out/'),'Original native archive evidence must have an explicit out namespace')
        member=relative.removeprefix('out/');restore_sdk.safe(member)
        with zipfile.ZipFile(archive) as incoming:
            require(incoming.namelist().count(member)==1,'Exactly one original raw native evidence member required')
            return incoming.read(member),origin(name,'zip-member',member=member)
    with zipfile.ZipFile(archive) as incoming:
        body=incoming.read('hosted-native-api/'+profile+'/independent-native-api-audit.json')
    require(body==independent,'Actual original native capture audit must equal independently reproduced audit bytes')
    return body,resolve,origin(name,'original-audit',member='hosted-native-api/'+profile+'/independent-native-api-audit.json')


def windows_audit(configuration):
    name='windows-audit-'+configuration;parent=WORK/('windows-'+configuration);parent.mkdir()
    published=parent/'published';members=zip_members(INPUTS/name/'producer.zip',published,128*1024**2)
    independent=parent/'independent';zip_members(INPUTS/('windows-final-'+configuration)/'producer.zip',independent,32*1024**2)
    retained=independent/'Windows-api-independent'/configuration/'proof';proof=load(retained/'proof.json')
    pin=load(LOCK)['inputs']['windows-final-'+configuration]
    require(proof['protocol']=='phase6-independent-published-Windows-GeneralApi-v1' and
        proof['status']=='verified-published-Windows-GeneralApi-configuration-only' and proof['configuration']==configuration and
        proof['auditor_source']==pin['source'] and proof['auditor_run_id']==pin['run_id'] and proof['actual_original_processes']==8 and
        proof['actual_published_audit_members']==members and proof['original_actual_case_assertions_reexecuted_unchanged'] is True and
        proof['original_SDK_all_member_and_28_unit_receipts_reverified'] is True and proof['new_simulator_processes_launched']==0 and
        proof['original_capture_source']==replay.CAPTURE_SOURCE and proof['original_capture_run_id']==replay.CAPTURE_RUN and
        proof['original_capture_conclusion']=='failure' and proof['phase6_complete'] is False,'Complete source-bound independent Windows publication proof required')
    require(all(sha(retained/n)==v for n,v in proof['retained_receipt_sha256'].items()),'Every independent Windows receipt member required')
    require(proof['read_only_auditor_source']==windows.AUDITOR and proof['read_only_audit_run_id']==windows.AUDIT_RUN and
        proof['read_only_audit_job_id']==windows.PUBLISHED_PINS[configuration][0] and
        proof['read_only_audit_artifact']['id']==windows.PUBLISHED_PINS[configuration][1] and
        proof['read_only_audit_artifact']['digest']=='sha256:'+windows.PUBLISHED_PINS[configuration][3],
        'Exact original independently verified Windows audit lineage required')
    for relative,value in proof['source_sha256'].items():
        source_bytes=subprocess.check_output(['git','-C',str(ROOT),'show',pin['source']+':'+relative])
        require(hashlib.sha256(source_bytes).hexdigest()==value,'Original independent Windows publication source differs')
    replay.validate_capture_api(load(retained/'original-failed-capture-api.json'),configuration)
    body=(published/'Windows-api-published-reaudit'/(configuration+'-GeneralApi')/'audit.json').read_bytes()
    require(body==(retained/'original-Windows-audit.json').read_bytes(),'Actual Windows read-only and independently republished audit bytes differ')
    report=json.loads(body);require(report['evidence_sha256']==proof['all_published_protected_evidence_sha256'],'Complete Windows protected evidence map differs')
    sdk=parent/'sdk-payload';outer=INPUTS/('sdk-'+configuration)/'producer.zip';zip_members(outer,sdk)
    build=load(sdk/'current-application.json');item=build['configurations'][configuration]
    require(build['source_commit']==restore_sdk.PRODUCER and build['owning_sources_unchanged'] is True and
        sha(sdk/'runtime.zip')==build['runtime_archive_sha256'],'Original Windows SDK compiled owner/inner archive differs')
    runtime=parent/'sdk-runtime';restore_sdk.unpack(sdk/'runtime.zip',runtime,item['runtime_files_sha256'])
    cases.inspect_hosted_sdk_members(sdk/'runtime.zip',runtime,item,item['sdk_manifest_sha256'])
    require(windows.immutable_sdk_sources()==build['source_guard_sha256_lf'],'Every immutable Windows SDK owning source must match')
    require(unit_result(load(sdk/'registered-tests.json'),sdk/'runtime-ctest.xml')==item['tests'] and item['tests']['executed_processes']==28,
        'Every original Windows unit receipt required')
    cell=configuration+'-GeneralApi';cfg=load(published/'current-api-requests'/cell/'request.json')
    worker=load(published/'current-api-requests'/cell/'worker-result.json');observer=load(published/'current-api-observer'/configuration/'observer-build.json')['observer']
    actual=cases.inspect_cases(cfg,worker,published/'current-api-exports'/cell,observer,published/'Windows-api-canonical-inputs'/configuration)
    require(actual==report['results']==proof['actual_case_results'],'All unchanged original Windows case checks must independently reproduce')
    def resolve(old):
        path=windows.evidence_path(old,published,sdk,runtime,outer)
        relative=PureWindowsPath(old).relative_to(WINDOWS_ROOT/'out').as_posix()
        if relative=='current-sdk-source/producer.zip':details=origin('sdk-'+configuration,'whole-zip')
        elif relative=='current-windows-sdk/source-artifact/runtime.zip':details=origin('sdk-'+configuration,'zip-member',member='runtime.zip')
        elif relative=='current-windows-sdk/runtime/test-runtime.json':details=origin('sdk-'+configuration,'nested-zip-member',member='runtime.zip',nested_member='test-runtime.json')
        else:details=origin(name,'zip-member',member=relative)
        return path,details
    return body,resolve,origin(name,'original-audit',member='Windows-api-published-reaudit/'+cell+'/audit.json')


def run(command):
    child=subprocess.run(command,cwd=ROOT,check=False)
    require(child.returncode==0,'Actual source-bound evidence restoration failed: '+command[2])



def retain_candidate():
    base=ROOT/'out/joint-api-published';record=load(base/'api.json');run=record['run'];artifact=record['artifact']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and
        run['id']==int(os.environ['GITHUB_RUN_ID']) and run['head_sha']==os.environ['GITHUB_SHA'] and
        run['head_branch']=='qualification/joint-general-api-v1' and run['path']=='.github/workflows/phase6-joint-general-api.yml' and
        run['run_attempt']==1 and artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==run['head_sha'] and
        artifact['name']=='joint-GeneralApi-qualified-reference' and artifact['expired'] is False,
        'Actual same-source published joint qualification reference required')
    jobs=record['jobs'];selected=[j for j in jobs if j['name']=='Joint original API qualification']
    require(len(jobs)==2 and {j['name'] for j in jobs}=={'Joint original API qualification','Independently restore and reproduce joint API qualification'} and
        len(selected)==1 and selected[0]['status']=='completed' and selected[0]['conclusion']=='success' and
        all(j['run_id']==run['id'] and j['head_sha']==run['head_sha'] and j['labels']==['ubuntu-24.04'] for j in jobs),
        'Exact completed standard-runner qualification producer and independent replay roster required')
    archive=base/'producer.zip'
    require(0<archive.stat().st_size==artifact['size_in_bytes']<32*1024**2 and 'sha256:'+sha(archive)==artifact['digest'],
        'Actual published joint metadata ZIP length/digest differs')
    target=base/'source-artifact';files=zip_members(archive,target,128*1024**2)
    reference=target/'joint-api-qualification/proof';body=load(reference/'joint-proof.json')
    require(body['protocol']=='phase6-complete-joint-GeneralApi-scoped-evidence-v1' and body['status']=='qualified-complete-native-Windows-GeneralApi-only' and
        body['source']==run['head_sha'] and body['github_run_id']==run['id'] and body['github_run_attempt']==1 and
        body['independently_replayed_published_qualification'] is False and body['qualified_report_sha256']==sha(reference/'qualification.json') and
        body['inputs_lock_sha256']==sha(LOCK) and body['input_artifacts']==load(LOCK)['inputs'] and
        body['new_simulator_processes_launched']==0 and body['normal_admission_qualified'] is False and body['phase6_complete'] is False,
        'Complete actual six-scope qualification reference required')
    (base/'raw-members.json').write_text(json.dumps(files,indent=2)+'\n')
    return reference


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--replay-published',type=Path);p.add_argument('--unpack-published',action='store_true');a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
        Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted Linux joint closure required')
    source=os.environ['GITHUB_SHA'];require(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==source,
        'Actual joint qualification source differs')
    require(sha(Path(qualification.__file__))==QUALIFIER_SHA256,'Original joint API qualifier changed')
    if a.unpack_published:
        print(str(retain_candidate()));return
    source_proof=source_identity()
    require(not WORK.exists() and not (OUTPUT/'materialized').exists(),'Fresh actual source/evidence restoration required');WORK.mkdir(parents=True)
    proof=OUTPUT/'proof';proof.mkdir(parents=True,exist_ok=True);published=None
    if a.replay_published:
        published=a.replay_published.resolve()
        for name in ('helpers.json','controls.json'):shutil.copy2(published/name,proof/name)
    require((proof/'helpers.json').is_file() and (proof/'controls.json').is_file(),'Actual Lua/damaged/18 original API helper controls required')
    progress=dict(protocol='phase6-joint-GeneralApi-evidence-progress-v1',status='running',source=source,
        run_id=int(os.environ['GITHUB_RUN_ID']),mode='independent-replay' if published else 'joint-qualification',
        completed=[],new_simulator_processes_launched=0,normal_admission_qualified=False,phase6_complete=False)
    def completed(label):
        progress['completed'].append(label);(proof/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    try:
        for name in load(LOCK)['inputs']:
            pin=validate_input(name,load(INPUTS/name/'api.json'));archive=INPUTS/name/'producer.zip'
            require(archive.stat().st_size==pin['archive_bytes'] and sha(archive)==pin['archive_sha256'],'Actual whole input archive bytes differ: '+name)
        completed('all13-input-APIs-original-job-rosters-and-whole-ZIP-digests-verified')
        for family,script in (('providers','restore_hosted_native_providers.py'),('mesa','restore_hosted_mesa_topology.py')):
            run([sys.executable,'-B',str(ROOT/'Tests/Production/Closeout'/script),'--api',str(INPUTS/family/'api.json'),
                '--archive',str(INPUTS/family/'producer.zip'),'--output',str(WORK/(family+'-restoration.json'))])
        completed('complete-original-provider-and-Mesa-members-links-and-unsuppressed-positive-negative-controls-restored')
        native_final=WORK/'native-final';zip_members(INPUTS/'native-final/producer.zip',native_final,64*1024**2)
        native_base,native_proof=verify_native_final(native_final)
        original_reports={};scopes={};native_paths=[];windows_paths=[]
        for profile in PROFILES:
            scope='native-'+profile;body,resolver,source_origin=native_audit(profile,native_base)
            path,record=materialize_audit(body,scope,OUTPUT/'materialized'/scope,resolver,source_origin)
            native_paths.append(path);scopes[scope]=record;original_reports[scope]=hashlib.sha256(body).hexdigest();completed(scope+'-all-original-evidence-bytes-materialized')
        for configuration in ('Debug','Release'):
            scope='windows-'+configuration;body,resolver,source_origin=windows_audit(configuration)
            path,record=materialize_audit(body,scope,OUTPUT/'materialized'/scope,resolver,source_origin)
            windows_paths.append(path);scopes[scope]=record;original_reports[scope]=hashlib.sha256(body).hexdigest();completed(scope+'-full-SDK-units-original-cases-and-all-original-evidence-bytes-materialized')
        target=proof/'qualification.json'
        result=qualification.qualify(native_paths,windows_paths,proof/'helpers.json',proof/'controls.json',target)
        require(result['status']=='qualified-general-api-correction-v2' and set(result['profiles'])==set(PROFILES) and
            set(result['cohorts'])=={'native','current-windows'} and result['normal_stock_admission_qualified'] is False,
            'Original unchanged complete API qualifier did not close')
        require(source_identity()==source_proof,'Locked production core or original API sources changed during joint closure')
        for scope,row in scopes.items():
            require(sha(row['original_audit_path'])==row['original_audit_sha256'] and sha(row['materialized_audit_path'])==row['materialized_audit_sha256'] and
                all(sha(v['materialized_path'])==v['sha256'] for v in row['original_to_materialized'].values()),'Original or materialized evidence changed during qualification')
        completed('unchanged-original-qualifier-and-its-full-evidence-reinspection-passed')
        if published is not None:
            require(target.read_bytes()==(published/'qualification.json').read_bytes(),'Independently reexecuted original joint qualification must match published bytes exactly')
            old=load(published/'joint-proof.json')
            require(old['scopes']==scopes and old['original_audit_sha256']==original_reports and
                old['qualified_report_sha256']==sha(target),'Independent actual-byte scope restoration must reproduce the published closure')
            completed('published-qualified-report-reproduced-byte-for-byte-after-independent-restoration')
        report=dict(protocol='phase6-complete-joint-GeneralApi-scoped-evidence-v1',status='qualified-complete-native-Windows-GeneralApi-only',
            source=source,github_run_id=int(os.environ['GITHUB_RUN_ID']),github_run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),
            independently_replayed_published_qualification=published is not None,
            qualified_report_sha256=sha(target),original_qualifier_sha256=QUALIFIER_SHA256,source_identity=source_proof,
            inputs_lock_sha256=sha(LOCK),input_artifacts=load(LOCK)['inputs'],original_audit_sha256=original_reports,scopes=scopes,
            cohorts=['native','current-windows'],profiles=PROFILES,actual_original_native_processes=8,actual_original_Windows_processes=16,
            all_original_audit_bytes_source_roles_PIDs_and_failed_statuses_preserved=True,
            every_original_evidence_hash_reads_actual_scoped_bytes=True,original_conflicting_evidence_guard_preserved=True,
            new_simulator_processes_launched=0,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
        (proof/'joint-proof.json').write_text(json.dumps(report,indent=2)+'\n')
        progress['status']='passed-complete-joint-API-closure-only';completed('complete-versioned-joint-API-reference')
        print(json.dumps(dict(status=report['status'],scopes=len(scopes),original_native_processes=8,original_Windows_processes=16,
            independent_replay=published is not None,normal_admission_qualified=False)))
    except BaseException as error:
        progress.update(status='failed-or-incomplete-unqualified',error=str(error));(proof/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');raise


if __name__=='__main__':main()
