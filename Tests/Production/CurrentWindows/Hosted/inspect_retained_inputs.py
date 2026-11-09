#!/usr/bin/env python3
"""Independently inspect closed Windows SDK/observer bytes on Linux without executing them."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from restore_sdk import ROOT,PRODUCER as APPLICATION,PINS as SDK_PINS,validate_api as sdk_api,unpack,require,sha
from restore_observer import PRODUCER as PREPARATION,PINS as OBSERVER_PINS,validate_api as observer_api,verify_variant


def load(path):return json.loads(Path(path).read_text())


def executed_runtime(files,observer_sha):
    target='Modules/Plugin/ProductionCockpitDriver.dll'
    require({'Orbiter.exe','Modules/Plugin/OGLClient.dll'}<=set(files) and len(observer_sha)==64 and all(c in '0123456789abcdef' for c in observer_sha),'Exact passive observer replacement role required')
    return dict(files)|{target:observer_sha}


def inspect(configuration,sdk_record,sdk_archive,observer_record,observer_archive,owner,output):
    sdk_api(sdk_record,configuration);observer_api(observer_record,configuration)
    for archive,pin in ((sdk_archive,SDK_PINS[configuration]),(observer_archive,OBSERVER_PINS[configuration])):
        require(archive.stat().st_size==pin[1] and sha(archive)==pin[2],'Actual retained current-input API archive differs')
    require(not output.exists(),'Fresh independent retained-input inspection required');output.mkdir(parents=True)
    sdk_payload=output/'sdk-source';sdk_outer=unpack(sdk_archive,sdk_payload);report=load(sdk_payload/'current-application.json');item=report['configurations'][configuration]
    require(report['protocol']=='phase6-github-current-application-v1' and report['status']=='built-and-client-tested-awaiting-complete-stock-qualification' and
            report['source_commit']==APPLICATION and report['owning_sources_unchanged'] is True and item['status']=='built' and
            report['phase6_complete'] is False and report['native_admission_qualified'] is False,'Original current SDK status/source differs')
    archive=sdk_payload/'runtime.zip';require(sha(archive)==report['runtime_archive_sha256'] and archive.stat().st_size==report['runtime_archive_bytes'],
            'Complete sealed current SDK archive differs')
    runtime=output/'runtime';unpack(archive,runtime,item['runtime_files_sha256'])
    require(sha(runtime/'test-runtime.json')==item['sdk_manifest_sha256'] and
            subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],text=True).strip()==APPLICATION,'Exact immutable SDK source owner/manifest required')
    helper=owner/'Tests/Production/CurrentWindows/retain_hosted_sdk.py'
    frozen=subprocess.check_output(['git','-C',str(owner),'show',APPLICATION+':Tests/Production/CurrentWindows/retain_hosted_sdk.py']).replace(b'\r\n',b'\n')
    require(helper.read_bytes().replace(b'\r\n',b'\n')==frozen,'Original independent SDK byte/source reader changed')
    spec=importlib.util.spec_from_file_location('independent_current_sdk_'+configuration,helper);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    require(reader.source_files(APPLICATION)==report['source_guard_sha256_lf'] and
            reader.runtime_files(runtime,APPLICATION)==item['runtime_files_sha256'],'Complete actual application/SDK/source closure differs')
    tests=reader.unit_result(load(sdk_payload/'registered-tests.json'),sdk_payload/'runtime-ctest.xml')
    require(tests==item['tests'] and tests['executed_processes']==28 and sha(sdk_payload/'build-inputs.json')==item['build_inputs_sha256'],
            'Original complete passed current Windows unit/compiler receipts differ')
    observer_payload=output/'observer-source';observer_outer=unpack(observer_archive,observer_payload);prepared=observer_payload/'current-stock-preparation'
    prep=load(prepared/'preparation.json');work=prepared/'observer';built=load(work/'observer-build.json');observer=built['observer']
    require(prep['status']=='prepared-current-SDK-passive-stock-observer-only' and prep['collector_source']==PREPARATION and
            prep['compiled_application_source']==prep['observer_source']==APPLICATION and prep['configuration']==configuration and
            prep['stock_simulation_executed'] is False and prep['phase6_complete'] is False and prep['native_admission_qualified'] is False and
            prep['observer_build_sha256']==sha(work/'observer-build.json') and prep['application_build_sha256']==sha(sdk_payload/'current-application.json'),
            'Original exact-SDK passive preparation receipt differs')
    require(built['status']=='prepared-passive-observer-only' and built['source_commit']==APPLICATION and
            observer['kind']=='remaining-stock' and observer['configuration']==configuration and observer['source_commit']==observer['sdk_source_commit']==APPLICATION and
            observer['sha256']==prep['observer_binary_sha256']==sha(work/'ProductionCockpitDriver.dll') and
            built['sdk']['manifest_sha256']==prep['sdk_manifest_sha256']==item['sdk_manifest_sha256'],'Actual passive observer/SDK source/binary identity differs')
    original=owner/'Tests/Production/RemainingStock/Driver.cpp';verify_variant(original.read_bytes(),(work/'Driver-960.cpp').read_bytes(),built['observer_source_variant'])
    normalized=original.read_bytes().replace(b'\r\n',b'\n');allowed={hashlib.sha256(normalized).hexdigest(),hashlib.sha256(normalized.replace(b'\n',b'\r\n')).hexdigest()}
    require(observer['source_sha256']==built['observer_source_variant']['original_sha256'] and observer['source_sha256'] in allowed,
            'Original passive observer source provenance differs')
    require(built['commands'] and all(c['actual_returncode']==0 and type(c['actual_pid']) is int and c['actual_pid']>0 and
            sha(work/(c['label']+'.log'))==c['log_sha256'] for c in built['commands']),'Original actual passive compiler receipts differ')
    require(all(sha(sdk_payload/name)==value for name,value in sdk_outer.items()) and
            all(sha(observer_payload/name)==value for name,value in observer_outer.items()) and
            reader.runtime_files(runtime,APPLICATION)==item['runtime_files_sha256'],'Retained original SDK/preparation bytes changed during inspection')
    return dict(protocol='phase6-independent-current-input-inspection-v1',status='inspected-immutable-Windows-build-and-observer-bytes-only',
        configuration=configuration,compiled_application_source=APPLICATION,compiled_observer_source=APPLICATION,preparation_source=PREPARATION,
        sdk_manifest_sha256=item['sdk_manifest_sha256'],original_sdk_manifest_sha256=sha(sdk_payload/'current-application.json'),
        runtime_local=str(runtime),runtime_original_path=item['runtime'],runtime_files_sha256=item['runtime_files_sha256'],
        executed_runtime_files_sha256=executed_runtime(item['runtime_files_sha256'],observer['sha256']),observer=observer,
        observer_manifest_sha256=sha(work/'observer-build.json'),observer_local=str(work/'ProductionCockpitDriver.dll'),
        observer_build=built,tests=tests,owning_source_files=len(report['source_guard_sha256_lf']),
        original_sdk_api_sha256=sdk_record['artifact']['digest'],original_observer_api_sha256=observer_record['artifact']['digest'],
        Windows_code_executed_by_auditor=False,phase6_complete=False,native_admission_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-api','sdk-archive','observer-api','observer-archive','source-owner','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args()
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true','Independent hosted Linux byte inspection only')
    result=inspect(a.configuration,load(a.sdk_api),a.sdk_archive,load(a.observer_api),a.observer_archive,a.source_owner,a.output)
    result['auditor_source']=os.environ['GITHUB_SHA'];(a.output/'inspection.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
