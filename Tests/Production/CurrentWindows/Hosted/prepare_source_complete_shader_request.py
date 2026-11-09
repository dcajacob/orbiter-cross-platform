#!/usr/bin/env python3
"""Name every exact audited original save and immutable role for one complete hosted phase."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/Closeout/LocalVM')]
from source_complete_shader_provider import PROTOCOL,require,sha,selection,validate,reference_receipts
from restore_sdk import PRODUCER as APPLICATION
from restore_source_complete_retry_reference import ORIGINAL,AUDITOR,audit_receipts
from static_binary_link_staging_v2 import PROTOCOL as STAGING_PROTOCOL


def load(path):return json.loads(Path(path).read_text())


def paired_inputs(config,capture_root,configuration,mode,expected_capture_sha256,members):
    require(configuration in ('Debug','Release') and mode in ('automatic','sse2') and config['frames']==960,'Known complete current stock profile required')
    ids=[case['id'] for case in config['cases']];require(len(ids)==len(set(ids))==38,'All 38 original cases required')
    manifest=Path(capture_root)/'capture.json';capture=load(manifest)
    require(sha(manifest)==expected_capture_sha256 and capture['producer_commit']==ORIGINAL and
            capture['configuration']==configuration and capture['math_profile']==mode and capture['protocol']=='remaining-stock-matched-clock-v2' and
            capture['status']=='captured-awaiting-independent-audit' and capture['diagnostic_only'] is False and
            capture['cases_requested']==ids and set(capture['cases'])==set(ids) and not capture['failures'],
            'Exact independently audited complete same-profile original parent capture required')
    result=[]
    for case in config['cases']:
        require(len(capture['cases'][case['id']]['runs'])==2,'Both actual original parent repetitions required')
        for repeat in (1,2):
            relative=case['id']+'-'+str(repeat)+'/Scenarios/(Current state).scn';path=Path(capture_root)/relative
            expected=members['remaining-stock-repaired/'+relative]
            require(sha(path)==expected,'Actual exact original saved input differs from its independently audited API member')
            result.append(dict(configuration=configuration,math_profile=mode,case=case['id'],repeat=repeat,path=str(path),sha256=expected,
                parent_capture_sha256=expected_capture_sha256,parent_producer_commit=ORIGINAL,
                parent_run=case['id']+'-'+str(repeat)))
    require(len(result)==76 and len({(r['case'],r['repeat']) for r in result})==76,'Complete exact saved-input closure required')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    p.add_argument('--phase',choices=('stock','reload'),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual standard GitHub Windows request preparation required')
    collector=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(collector==os.environ['GITHUB_SHA'],'Actual current collector source differs')
    source=ROOT/'application-source';sdk=ROOT/'out/current-windows-sdk';runtime=sdk/'runtime';build=ROOT/'out/current-stock-preparation/observer'
    restored=load(sdk/'restoration.json');observer_restored=load(ROOT/'out/current-observer-restoration/restoration.json')
    require(restored['status']=='restored-and-verified-current-sdk-only' and restored['compiled_source']==APPLICATION and
            restored['configuration']==a.configuration and Path(restored['source_owner'])==source and
            observer_restored['status']=='restored-original-passive-observer-only' and observer_restored['compiled_application_source']==APPLICATION and
            observer_restored['compiled_observer_source']==APPLICATION and observer_restored['configuration']==a.configuration,
            'Separately verified exact SDK and passive observer restorations required')
    reference=ROOT/'out/original-stock-audit';reference_restoration=load(ROOT/'out/reference-audit-restoration/restoration.json')
    require(reference_restoration['protocol']=='phase6-source-complete-original-reference-retry-restoration-v3' and
            reference_restoration['status']=='restored-exact-original-cohort-after-verified-audit-retry-only' and
            reference_restoration['original_capture_source']==ORIGINAL and reference_restoration['original_auditor_source']==AUDITOR and
            reference_restoration['original_windows_processes']==608 and reference_restoration['original_saves_relabelled'] is False,
            'Complete restored independently audited original reference required')
    transport=reference/'transport/download.json';writer=reference/'independent/writer-audit.json';cohort=reference/'independent/original-persistence-audit.json'
    audit_receipts(load(transport),load(writer),load(cohort),sha(transport),sha(writer))
    require(reference_restoration['original_transport_sha256']==sha(transport) and
            reference_restoration['original_writer_audit_sha256']==sha(writer) and
            reference_restoration['original_cohort_audit_sha256']==sha(cohort),'Restored original audit receipts changed')
    sys.path.insert(0,str(source/'Tests/Production/RemainingStockRepaired'));import protocols
    case_file=source/'Tests/Production/RemainingStock/cases.json';raw=case_file.read_bytes().replace(b'\r\n',b'\n')
    require(raw==subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL+':Tests/Production/RemainingStock/cases.json']).replace(b'\r\n',b'\n'),
            'Current and original complete stock inventories differ')
    config=protocols.load(load(case_file),protocols.V2);profile=a.configuration+'-'+a.math_profile
    binding=reference_restoration['original_api_archive_bindings'][profile];parent=reference/'transport'/profile/'remaining-stock-repaired'
    saves=paired_inputs(config,parent,a.configuration,a.math_profile,load(writer)['profiles'][profile]['capture_sha256'],binding['decoded_members_sha256'])
    name=profile+'-'+a.phase;share=ROOT/'out/current-stock-requests'/name
    require(not share.exists(),'Fresh hosted stock request directory required');share.mkdir(parents=True)
    roots=dict(source=source,preserved=runtime,build=build,data=ROOT/'out/current-stock-data',planets=ROOT/'out/current-stock-planets',
        mesa=ROOT/'out/current-stock-mesa',output=ROOT/'out/current-stock-captures'/name,export=ROOT/'out/current-stock-exports'/name)
    for key in ('output','export'):roots[key].parent.mkdir(parents=True,exist_ok=True)
    for key in ('output','export'):
        require(not roots[key].is_relative_to(reference) and not reference.is_relative_to(roots[key]),'Writable phase root overlaps original reference')
    phase_cell=name
    names=set(subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only','HEAD','--','Tests/Production/CurrentWindows','Tests/Production/Closeout'],text=True).splitlines())
    names={name for name in names if name.endswith('.py')}|{'Tests/Production/Closeout/LocalVM/stock_runtime_worker_v3.py',
        'Tests/Production/Closeout/LocalVM/static_binary_link_staging_v2.py'}
    files={}
    for name in sorted(names):
        path=ROOT/name;body=subprocess.check_output(['git','-C',str(ROOT),'show',collector+':'+name]).replace(b'\r\n',b'\n')
        require(path.read_bytes().replace(b'\r\n',b'\n')==body,'Actual hosted helper differs from its immutable collector: '+name);files[name]=sha(path)
    runner=share/'runners.json';runner.write_text(json.dumps(dict(protocol='phase6-hosted-current-stock-runner-v1',commit=collector,
        files_sha256=files,legacy_worker_sha256_lf='dddbbf40656524ffa2dddcfcd745767ed270d3d46109917c2da3a89f66a15c51'),indent=2)+'\n')
    sdk_manifest=runtime/'test-runtime.json';observer_manifest=build/'observer-build.json'
    roles={name:dict(commit=APPLICATION,manifest_path=str(sdk_manifest),manifest_sha256=sha(sdk_manifest)) for name in ('application','sdk')}
    roles['observer']=dict(commit=APPLICATION,manifest_path=str(observer_manifest),manifest_sha256=sha(observer_manifest))
    roles['runner']=dict(commit=collector,manifest_path=str(runner),manifest_sha256=sha(runner))
    application_build=ROOT/'out/current-stock-preparation/application-build.json'
    from retry_reference_proof import inventory
    shader_plan=ROOT/'out/current-shader-delivery'/(phase_cell+'.json')
    cfg=dict(name=phase_cell,renderer_shader_delivery=dict(path=str(shader_plan),sha256=sha(shader_plan)),reference_retry_inputs=inventory(ROOT/'out'),transport_protocol=PROTOCOL,cohort='current-windows',source_role='application',source_commit=APPLICATION,
        workspace=str(ROOT),roots={key:str(path) for key,path in roots.items()},roles=roles,
        github=dict(repository='dcajacob/orbiter-cross-platform',run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),collector_commit=collector),
        configuration=a.configuration,math_profile=a.math_profile,phase=a.phase,scene_workers=1,minimum_free_bytes=8*1024**3,
        staging_protocol=STAGING_PROTOCOL,capture_scope=dict(kind='complete',gate='remaining-stock',cases=[case['id'] for case in config['cases']]),
        git=shutil.which('git'),application_build_manifest=str(application_build),application_build_manifest_sha256=sha(application_build),
        windows_save_inputs=saves,reference_transport=dict(path=str(transport),sha256=sha(transport)),reference_audit=dict(path=str(writer),sha256=sha(writer)),
        reference_persistence_audit=dict(path=str(cohort),sha256=sha(cohort)),reference_restoration=dict(path=str(ROOT/'out/reference-audit-restoration/restoration.json'),sha256=sha(ROOT/'out/reference-audit-restoration/restoration.json')),
        **{key:str(path) for key,path in roots.items()})
    require(cfg['git'],'Actual inherited Git tool required');validate(cfg);selection(cfg,config);reference_receipts(cfg)
    request=share/'request.json';request.write_text(json.dumps(cfg,indent=2)+'\n');print(str(request))


if __name__=='__main__':main()
