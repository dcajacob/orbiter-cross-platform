#!/usr/bin/env python3
"""Independently replay the unchanged original numerical audit from published complete raw bytes."""
import argparse
import hashlib
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import sys
from types import FunctionType
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
import rejection_input_bundle as bundle
import stream_retained_numerical_inputs as stream_inputs
import numerical_observer_equivalence as numerical
import build_native_numerical_observers as compiler


def validate_api(api,pin):
    r=api['run'];a=api['artifact'];jobs=api['jobs']
    require(api['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and r['repository']['private'] is False and r['repository']['full_name']=='dcajacob/orbiter-cross-platform' and r['id']==pin['run_id'] and r['head_sha']==pin['source'] and r['head_branch']==pin['branch'] and r['path']=='.github/workflows/phase6-native-numerical-observer-equivalence.yml' and r['run_attempt']==1 and r['status']=='completed' and r['conclusion']=='success','Only exact completed successful original numerical source/run required')
    require(len(jobs)==1 and jobs[0]['id']==pin['job_id'] and jobs[0]['run_id']==r['id'] and jobs[0]['head_sha']==r['head_sha'] and jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and jobs[0]['labels']==['ubuntu-24.04'],'One actual exact standard hosted capture job required')
    require(a['id']==pin['artifact_id'] and a['name']=='original-save-numerical-observer-three-world-full-raw' and a['size_in_bytes']==pin['archive_bytes'] and a['digest']=='sha256:'+pin['archive_sha256'] and a['expired'] is False and a['workflow_run']['id']==r['id'] and a['workflow_run']['head_sha']==r['head_sha'],'Exact published full raw archive API digest/source required')


def restore_outer(archive,folder,raw_member):
    require(not folder.exists(),'Fresh published complete outer namespace required');folder.mkdir(parents=True);members={};seen=set();total=0
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            n=item.filename;p=PurePosixPath(n);require(n and (str(p)==n or item.is_dir() and str(p)+'/'==n) and not p.is_absolute() and '..' not in p.parts and ':' not in n and '\\' not in n and n.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,'Safe unique unredirected complete published member required');seen.add(n.casefold());total+=item.file_size
            require(len(seen)<100000 and total<8*1024**3,'Original complete bounded published metadata/raw archive required')
            if n==raw_member:continue # consume every compressed/body byte directly from the outer ZIP once
            target=folder/n
            if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
            require(target.stat().st_size==item.file_size,'Every complete outer byte required');members[n]=dict(bytes=item.file_size,sha256=sha(target))
    return members


def compiler_witness(folder,source):
    p=load(folder/'proof.json');require(p['source']==source and p['profile']=='Debug-automatic' and p['compiled_engine_source']==compiler.COMPILED and p['status']=='built-two-unchanged-readonly-numerical-observers-only' and p['actual_original_compiler_processes']==2 and p['new_simulator_processes']==0 and p['actual_engine_CPP_ABI']==p['actual_host_preprocessor']['actual_cpp_abi']=='gcc-13.3.0:libstdc++-20240904-abi-1-normal-gxx-1018:201703L','Actual original matching compiler component required')
    require(p['compiler_version_or_ABI_macros_overridden'] is False and p['original_observer_sources_changed'] is False and p['original_runtime_files_replaced'] is False,'No compiler/source/runtime substitutions allowed')
    identities=[]
    for kind,item in zip(('sdk','internal'),p['commands'],strict=True):
        receipt=load(folder/(kind+'-process.json'));argv=compiler.command(kind,'Debug-automatic',folder)
        actual=numerical.actual_process(receipt,argv);require(item['kind']==kind and item['actual_argv']==argv and item['actual_pid']==actual['pid'] and item['start_ticks']==actual['start_ticks'] and item['actual_returncode']==0 and item['process_receipt_sha256']==sha(folder/(kind+'-process.json')) and item['output_sha256']==sha(Path(item['output'])) and item['log_sha256']==sha(folder/(kind+'-compile.log')) and item['dynamic_sha256']==sha(folder/(kind+'-dynamic.txt')) and item['symbols_sha256']==sha(folder/(kind+'-symbols.txt')),'Every actual original compiler process, source argv and ELF output required')
        dynamic=(folder/(kind+'-dynamic.txt')).read_text();require(Path(item['output']).read_bytes()[:6]==b'\x7fELF\x02\x01' and 'Shared library: [libasan.so.' in dynamic and 'Shared library: [libubsan.so.' in dynamic,'Both original sanitizer linkages and actual x64 ELF required');identities.append(actual)
    require(len({(v['pid'],v['start_ticks']) for v in identities})==2,'Two actual original compiler process identities required')
    for name,digest in p['original_sources_sha256'].items():require(sha(ROOT/name)==digest==hashlib.sha256(subprocess.check_output(['git','show',compiler.COMPILED+':'+name])).hexdigest(),'Every compiled observer/header source must remain original')
    require(p['actual_host_preprocessor']['preprocessor_sha256']==sha(folder/'host-preprocessor-macros.log'),'Actual compiler preprocessor raw bytes required')
    return dict(actual_original_compiler_processes=2,processes=identities,proof_sha256=sha(folder/'proof.json'),all_original_sources_and_sanitizers_unchanged=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','lock','output'):parser.add_argument('--'+n,type=lambda s:Path(s).resolve(),required=True)
    a=parser.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists(),'Fresh standard hosted independent audit only; no local bulk replay')
    a.output.mkdir(parents=True);api=load(a.inputs/'api.json');pin=load(a.lock);validate_api(api,pin);archive=a.inputs/'producer.zip';require(archive.stat().st_size==pin['archive_bytes'] and sha(archive)==pin['archive_sha256'],'Exact full published ZIP bytes required')
    payload=a.output/'outer';prefix='hosted-numerical-observer/Debug-automatic/';raw_member=prefix+'raw-original-inputs.tar.gz';members=restore_outer(archive,payload,raw_member);base=payload/prefix;index=load(base/'raw-index.json')
    folder=ROOT/'out/numerical-observer-renewal/Debug-automatic';relative=folder.relative_to(ROOT).as_posix()+'/';outer_collection=payload/relative.removeprefix('out/')/'collection.json';planned=load(outer_collection)
    scenario=planned['derived_case']['scenario_entry_point'];bundle.safe(scenario)
    common={*numerical.PRIMARY,'graphics-lifecycle.json','stock-vessel-complete.txt','observer-loaded-maps.txt','console.log','ground-math.csv',scenario}
    selected={n for n in index['files'] if n.startswith(relative) and '/' not in n[len(relative):]}
    selected.update(relative+'baseline/'+n for n in common|{'invocation.json','process-receipt.json'})
    selected.add(relative+'equivalence/capture.json')
    for mode in ('off','on'):
        selected.update(relative+'equivalence/observer-'+mode+'/'+n for n in common|{'process-result.json','diagnostic-invocation.json'}|({'internal-state.csv'} if mode=='on' else set()))
    with zipfile.ZipFile(archive) as zip_body,zip_body.open(raw_member) as raw:
        verified,restored=stream_inputs.verify(ROOT,raw,index,selected,a.output/'materialized-original-inputs')
    members[raw_member]=dict(bytes=restored['original_raw_bundle_bytes'],sha256=restored['original_raw_bundle_sha256'])
    require(sha(outer_collection)==sha(folder/'collection.json'),'Original producer collection report must be identical in both published locations')
    report=load(folder/'collection.json');require(report['status']=='captured-and-original-audited-three-world-observer-equivalence-only' and report['source_identity']['source']==pin['source'] and report['compiled_runtime_source']==compiler.COMPILED and report['runtime_role']=='diagnostic' and report['original_saved_input_sha256']==numerical.INPUT_SHA and report['complete_numerical_reload_gate_qualified'] is False and report['phase6_complete'] is False,'Original source/input/diagnostic scope must not be relabelled')
    controls=load(payload/'numerical-observer-renewal-controls.json');require(controls['status']=='passed' and controls['tests_run']==pin['source_controls_passed'] and all(controls[n]==0 for n in ('skipped','failures','errors')) and controls['producer_commit']==pin['source'] and controls['sources_match_producer'] is True,'All original source controls must have actually passed')
    for name,digest in controls['sources_sha256'].items():
        path=Path(name);require(path.is_relative_to(ROOT) and sha(path)==digest==hashlib.sha256(subprocess.check_output(['git','show',pin['source']+':'+path.relative_to(ROOT).as_posix()])).hexdigest(),'Every original control/helper source must match its original producer')
    for name in numerical.ORIGINAL:require((ROOT/name).read_bytes()==subprocess.check_output(['git','show',compiler.COMPILED+':'+name]),'Original collector/auditor source changed')
    def observed_sha(path):
        path=Path(path)
        if path.is_file():return sha(path)
        # All physical outputs are materialized; large unused input bodies have
        # already been read and hashed in full directly from the published ZIP.
        require(str(path) in report['guarded_files_sha256'] and path.is_relative_to(ROOT),'Only actual byte-verified original dependency inputs can use the streaming witness')
        return verified[path.relative_to(ROOT).as_posix()]
    for name,digest in report['guarded_files_sha256'].items():
        path=Path(name);require(path.is_relative_to(ROOT) and verified[path.relative_to(ROOT).as_posix()]==observed_sha(path)==digest,'Every original guarded dependency body must be verified')
    compiled=compiler_witness(folder,pin['source']);validator=numerical.validate_three_worlds
    validate=FunctionType(validator.__code__,dict(validator.__globals__,sha=observed_sha),validator.__name__)
    actual=validate(folder,report);require(actual==report['three_world_inspection'],'Every original actual three-world inspection field must reproduce exactly')
    fresh=a.output/'replayed-original-audit.json';argv=[sys.executable,'-B',str(ROOT/'Tests/Production/ReloadMath/audit_native.py'),'--capture',str(folder/'equivalence'),'--baseline',str(folder/'baseline'),'--output',str(fresh)]
    with (a.output/'replayed-original-audit.log').open('wb') as stream:
        process=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
    require(process.returncode==0 and load(fresh)==load(folder/'original-audit.json') and sha(fresh)==sha(folder/'original-audit.json'),'Actual unchanged original auditor must reproduce the complete original report byte for byte')
    config=load(folder/'configuration-input-controls.json');require(config['status']=='passed' and config['kind']=='native' and config['producer_commit']==pin['source'] and config['owning_capture_unchanged'] is True,'Original actual startup configuration controls required')
    from verify_published_original_pool import inspect_signed_indexes
    pool=payload/'original-package-official-pool/Debug-automatic';plan=[row.split('\t') for row in (pool/'exact-original-plan.tsv').read_text().splitlines()];require(len(plan)==402,'Exactly402 original signed package blobs required')
    signed=inspect_signed_indexes(pool,plan,a.output/'original-snapshot-signature-audit')
    actual_inventory=(pool/'actual-system-packages.txt').read_bytes();require(actual_inventory==(pool/'original-system-packages.txt').read_bytes() and hashlib.sha256(actual_inventory).hexdigest()=='0ae6765d460a0d744c48afdb242257d02a29da4845cf7e8b7fda42004e164900','All488 actual installed original package versions must remain unchanged')
    materialized,missing=bundle.inventory(ROOT,[ROOT/n for n in selected]);require(not missing and materialized=={n:index['files'][n] for n in selected} and sha(archive)==pin['archive_sha256'] and all(observed_sha(n)==d for n,d in report['guarded_files_sha256'].items()),'Every original source, full archive, actual physical output, runtime, binary, data and alias must remain unchanged after independent audit')
    atomic_json(a.output/'full-outer-members.json',members);atomic_json(a.output/'original-raw-index.json',index)
    result=dict(protocol='phase6-published-independent-three-world-numerical-observer-equivalence-v1',status='independently-verified-published-native-observer-equivalence-only',auditor_source=os.environ['GITHUB_SHA'],original_capture_source=pin['source'],original_run_id=pin['run_id'],original_artifact=api['artifact'],full_published_archive_sha256=sha(archive),all_original_outer_members_verified=len(members),original_raw_index_sha256=sha(base/'raw-index.json'),all_original_logical_files_verified=len(index['files']),complete_original_raw_retention=restored,original_auditor_report_reproduced_byte_for_byte=True,original_auditor_report_sha256=sha(fresh),original_compiler=compiled,actual_original_worlds=actual,original_source_controls_passed=controls['tests_run'],original488_package_inventory_sha256=hashlib.sha256(actual_inventory).hexdigest(),signed_snapshot_independent_audit=signed,new_simulator_processes=0,all_original_sources_runtime_data_sanitizers_and_acceptance_unchanged=True,numerical_observer_equivalence_qualified=True,normal_admission_qualified=False,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False)
    atomic_json(a.output/'verification.json',result);print(result['status'])


if __name__=='__main__':main()
