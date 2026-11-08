#!/usr/bin/env python3
"""Build the unchanged passive full-stock observer against a restored exact current SDK."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from restore_sdk import PRODUCER
from provider import context,require,sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    parser.add_argument('--source-owner',type=lambda p:Path(p).resolve(),required=True);a=parser.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual standard GitHub Windows preparation required')
    base=ROOT/'out/current-stock-preparation';base.mkdir(parents=True,exist_ok=True)
    result=base/'preparation.json';require(not result.exists(),'Fresh observer preparation receipt required')
    sdk_root=ROOT/'out/current-windows-sdk';restored=json.loads((sdk_root/'restoration.json').read_text())
    require(restored['status']=='restored-and-verified-current-sdk-only' and restored['compiled_source']==PRODUCER and
            restored['configuration']==a.configuration and Path(restored['source_owner'])==a.source_owner,
            'Exact independently restored source-bound SDK required')
    runtime=Path(restored['runtime']);guard=dict(restored['runtime_files_sha256'])
    require(all(sha(runtime/name)==value for name,value in guard.items()),'Restored current runtime changed before observer build')
    environment=base/'inherited-compiler-env.cmd';environment.write_text('@echo off\nset\n')
    request=base/'observer-request.json';work=base/'observer'
    cfg=dict(name='observer',work=str(work),prepared_source=str(a.source_owner),source_commit=PRODUCER,
        sdk_source_commit=PRODUCER,git=shutil.which('git'),compiler_environment=str(environment),preserved=str(runtime),
        configuration=a.configuration,observer_kind='remaining-stock',run_crt=False)
    require(cfg['git'] and not request.exists(),'Actual inherited Git tool and fresh request required');request.write_text(json.dumps(cfg,indent=2)+'\n')
    command=[sys.executable,'-B',str(a.source_owner/'Tests/Production/CurrentWindows/prepare_observer.py'),str(request)]
    receipt=dict(protocol='phase6-github-current-stock-preparation-v1',status='preparing-passive-observer-only',
        compiled_application_source=PRODUCER,observer_source=PRODUCER,collector_source=os.environ['GITHUB_SHA'],
        configuration=a.configuration,command=dict(argv=command),inherited_context=context(),
        sdk_restoration_sha256=sha(sdk_root/'restoration.json'),phase6_complete=False,native_admission_qualified=False,
        stock_simulation_executed=False)
    def save():result.write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    try:
        with (base/'observer-prepare.log').open('w') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT);receipt['command']['actual_pid']=child.pid;save()
            receipt['command']['actual_returncode']=child.wait()
        receipt['command']['log_sha256']=sha(base/'observer-prepare.log');save()
        require(receipt['command']['actual_returncode']==0,'Actual passive stock observer preparation failed')
        built=json.loads((work/'observer-build.json').read_text());observer=built['observer']
        require(built['status']=='prepared-passive-observer-only' and observer['kind']=='remaining-stock' and
                observer['sdk_source_commit']==PRODUCER and observer['source_commit']==PRODUCER and
                observer['configuration']==a.configuration and built['sdk']['manifest_sha256']==sha(runtime/'test-runtime.json') and
                sha(observer['binary'])==observer['sha256'],'Actual passive observer/current SDK identity differs')
        variant=built['observer_source_variant'];original=(a.source_owner/'Tests/Production/RemainingStock/Driver.cpp').read_bytes().replace(b'\r\n',b'\n')
        anchor=b'require(frames==60,"Incomplete original stock observation")';require(original.count(anchor)==1,'Original finalized-frame assertion anchor differs')
        compiled=original.replace(anchor,b'require(frames==960,"Incomplete repaired stock observation")')
        require((work/'Driver-960.cpp').read_bytes()==compiled and
                variant['only_change']=='Validate 960 finalized ticks instead of 60; all observation calls and delays unchanged',
                'Passive stock observer changed beyond its existing 960-tick assertion')
        require(all(sha(runtime/name)==value for name,value in guard.items()),'Actual SDK runtime changed during passive observer build')
        shutil.copy2(sdk_root/'source-artifact/current-application.json',base/'application-build.json')
        shutil.copy2(sdk_root/'restoration.json',base/'sdk-restoration.json')
        shutil.copy2(ROOT/'out/current-sdk-source/api.json',base/'sdk-source-api.json')
        receipt.update(status='prepared-current-SDK-passive-stock-observer-only',observer_binary_sha256=observer['sha256'],
            observer_build_sha256=sha(work/'observer-build.json'),application_build_sha256=sha(base/'application-build.json'),
            sdk_manifest_sha256=sha(runtime/'test-runtime.json'),owning_runtime_and_sources_unchanged=True,
            complete_stock_capture_and_independent_audit_pending=True)
    except BaseException as error:receipt.update(status='failed',error=str(error));raise
    finally:save()
    print(receipt['status'])


if __name__=='__main__':main()
