#!/usr/bin/env python3
"""Prepare explicit same-SDK observer and ordinary-session API request without a VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import PROTOCOL,APPLICATION,require,sha,load,validate
from inactive_stager_fixture import describe as describe_inactive_fixture


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true','Actual standard GitHub Windows request preparation required')
    collector=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();require(collector==os.environ['GITHUB_SHA'],'Actual immutable API collector differs')
    owner=ROOT/'application-source';runtime=ROOT/'out/current-windows-sdk/runtime';sdk=load(ROOT/'out/current-windows-sdk/restoration.json')
    require(sdk['compiled_source']==APPLICATION and sdk['configuration']==a.configuration and sdk['collector_source']==collector and
            sdk['status']=='restored-and-verified-current-sdk-only' and Path(sdk['runtime'])==runtime and Path(sdk['source_owner'])==owner,
            'Exact successful sealed SDK restoration required')
    require(subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],text=True).strip()==APPLICATION,'Actual separate application source differs')
    name=a.configuration+'-GeneralApi';share=ROOT/'out/current-api-requests'/name;require(not share.exists(),'Fresh actual API request required');share.mkdir(parents=True)
    variant=ROOT/'out/current-api-variant'/name
    subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/GeneralApiCorrection/prepare.py'),'--version','v2','--output',str(variant)],cwd=ROOT,check=True)
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    require(vswhere.is_file(),'Actual standard MSVC discovery tool required')
    installation=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
    require(installation and '\n' not in installation,'One actual MSVC installation required')
    vc=Path(installation)/'Common7/Tools/VsDevCmd.bat';require(vc.is_file(),'Actual MSVC environment script required')
    environment=share/'compiler-environment.bat'
    environment.write_text('@call "'+str(vc)+'" -arch=x64 -host_arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@set\n',encoding='ascii')
    observer=ROOT/'out/current-api-observer'/a.configuration
    observer_request=share/'observer-request.json'
    prepared=dict(name='GeneralApi-'+a.configuration,work=str(observer),prepared_source=str(owner),
        source_commit=APPLICATION,sdk_source_commit=APPLICATION,preserved=str(runtime),configuration=a.configuration,
        observer_kind='general-api',run_crt=False,inputs=str(ROOT/'Tests/Production/GeneralApiCorrection/inputs-v2.json'),
        git=shutil.which('git'),compiler_environment=str(environment))
    require(prepared['git'],'Actual inherited Git required');observer_request.write_text(json.dumps(prepared,indent=2)+'\n')
    subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/CurrentWindows/prepare_observer.py'),str(observer_request)],cwd=ROOT,check=True)
    built=load(observer/'observer-build.json')
    require(built['status']=='prepared-passive-observer-only' and built['observer']['kind']=='general-api' and
            built['observer']['source_commit']==built['observer']['sdk_source_commit']==APPLICATION and
            built['observer']['configuration']==a.configuration and built['sdk']['manifest_sha256']==sha(runtime/'test-runtime.json'),
            'Actual freshly compiled same-SDK passive API observer required')
    roots=dict(source=owner,preserved=runtime,build=observer,data=ROOT/'out/current-stock-data',planets=ROOT/'out/current-stock-planets',
        mesa=ROOT/'out/current-stock-mesa',output=ROOT/'out/current-api-captures'/name,export=ROOT/'out/current-api-exports'/name)
    for key in ('output','export'):roots[key].parent.mkdir(parents=True,exist_ok=True)
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',collector,'--','Tests/Production/GeneralApiCorrection','Tests/Production/CurrentWindows','Tests/Production/Closeout','Tests/Production/RemainingStockPersistence/LocalVM'],text=True).splitlines()
    names=sorted(n for n in names if n.endswith('.py'));files={}
    for relative in names:
        actual=(ROOT/relative).read_bytes();original=subprocess.check_output(['git','-C',str(ROOT),'show',collector+':'+relative])
        require(actual.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),'Actual API runner file differs from its immutable owner')
        files[relative]=sha(ROOT/relative)
    runner=share/'runners.json';runner.write_text(json.dumps(dict(protocol='phase6-hosted-current-GeneralApi-runner-v1',commit=collector,files_sha256=files),indent=2)+'\n')
    manifest=runtime/'test-runtime.json';roles={role:dict(commit=APPLICATION,manifest_path=str(manifest),manifest_sha256=sha(manifest)) for role in ('application','sdk')}
    roles['observer']=dict(commit=APPLICATION,manifest_path=str(observer/'observer-build.json'),manifest_sha256=sha(observer/'observer-build.json'))
    roles['runner']=dict(commit=collector,manifest_path=str(runner),manifest_sha256=sha(runner))
    application=ROOT/'out/current-windows-sdk/source-artifact/current-application.json';plan=ROOT/'out/current-shader-delivery'/(name+'.json')
    cfg=dict(name=name,transport_protocol=PROTOCOL,cohort='current-windows',source_role='application',source_commit=APPLICATION,
        workspace=str(ROOT),roots={k:str(v) for k,v in roots.items()},roles=roles,configuration=a.configuration,math_profile='matrix',
        minimum_free_bytes=8*1024**3,capture_scope=dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']),
        github=dict(repository='dcajacob/orbiter-cross-platform',run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),collector_commit=collector),
        git=prepared['git'],application_build_manifest=str(application),application_build_manifest_sha256=sha(application),
        variant=dict(manifest=str(variant/'variant.json'),manifest_sha256=sha(variant/'variant.json'),script=str(variant/'Script/Tests/GeneralApiTest.lua')),
        scenario_sha256_lf=hashlib.sha256((owner/'Scenarios/Tests/GeneralApiTest.scn').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        inactive_stager_fixture=describe_inactive_fixture(a.configuration),renderer_shader_delivery=dict(path=str(plan),sha256=sha(plan)),**{k:str(v) for k,v in roots.items()})
    validate(cfg);request=share/'request.json';request.write_text(json.dumps(cfg,indent=2)+'\n');print(str(request))


if __name__=='__main__':main()
