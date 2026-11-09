#!/usr/bin/env python3
"""Re-read actual hosted Windows API results with every original case assertion unchanged."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PureWindowsPath
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/GeneralApiCorrection'),
             str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import require,sha,load,validate,APPLICATION
from execute_hosted_general_api import terminal
from prepare import ORIGINAL,EARTH,corrected,digest
from startup_contract import events,corrected_log,inspect_windows_roster
from restore_sdk import validate_api,PINS
LEGACY=ROOT/'Tests/Production/GeneralApiCorrection/audit_windows.py'
LEGACY_SHA256_LF='8d8d723228f1130d481f4f943ad83ddfcadf9454d45ffb808d54d09a3a9ea986'


def windows_path(value):
    require(isinstance(value, str) and not any(ord(c) < 32 for c in value), 'Invalid Windows path')
    path = PureWindowsPath(value)
    require(path.is_absolute() and re.fullmatch('[A-Za-z]:', path.drive) and '..' not in path.parts and
            not any(':' in part for part in path.parts[1:]), 'Absolute local-volume Windows path required')
    return path


def original_case_body():
    body=LEGACY.read_bytes().replace(b'\r\n',b'\n')
    require(hashlib.sha256(body).hexdigest()==LEGACY_SHA256_LF,'Original actual Windows API case auditor changed')
    text=body.decode();start=text.index('    expected_script,unused=corrected(');end=text.index('    protected=',start)
    return text[start:end]


def inspect_cases(cfg,worker,export,obs):
    namespace=dict(globals())
    exec(compile('def cases(cfg,worker,export,obs):\n'+original_case_body()+'    return results\n',str(LEGACY),'exec'),namespace)
    return namespace['cases'](cfg,worker,export,obs)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--output',type=lambda v:Path(v).resolve(),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and not a.output.exists(),'Fresh actual hosted Windows independent API audit required')
    cfg=load(a.request);validate(cfg);require(cfg['github']['collector_commit']==os.environ['GITHUB_SHA'],'Actual source-bound hosted API audit required')
    share=a.request.parent;worker=load(share/'worker-result.json');owned=load(share/'runner-result.json')
    worker_file=Path(__file__).with_name('general_api_worker.py')
    require(owned['protocol']=='phase6-hosted-current-GeneralApi-owned-worker-v1' and
            owned['status']=='completed-current-Windows-GeneralApi-awaiting-independent-audit' and
            owned['actual_worker_exitcode']==0 and owned['source_commit']==cfg['github']['collector_commit'] and
            owned['github']==cfg['github'] and owned['request_sha256']==sha(a.request) and owned['worker_sha256']==sha(worker_file) and
            owned['worker_result_sha256']==sha(share/'worker-result.json') and owned['worker_console_sha256']==sha(share/'worker-console.log') and
            owned['argv']==[sys.executable,'-B',str(worker_file),str(a.request)] and owned['cwd']==str(ROOT) and
            type(owned['actual_worker_pid']) is int and owned['actual_worker_pid']>0 and owned['elapsed_ns']>0 and owned['guarded_sources_requests_and_roles_unchanged'] is True and
            owned.get('timed_out',False) is False,'Actual owned API worker PID/exit/request/source/log receipts required')
    terminal(cfg,worker,owned['actual_worker_pid'],sha(worker_file),sha(a.request))
    require(sha(cfg['roles']['runner']['manifest_path'])==cfg['roles']['runner']['manifest_sha256'],'Actual API runner role changed')
    runner=load(cfg['roles']['runner']['manifest_path']);require(runner['commit']==cfg['github']['collector_commit'],'Actual runner source role differs')
    for name,value in runner['files_sha256'].items():
        path=ROOT/name;original=subprocess.check_output(['git','-C',str(ROOT),'show',runner['commit']+':'+name])
        require(sha(path)==value and path.read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),'Actual immutable API runner/helper bytes differ')
    sdk_root=ROOT/'out/current-windows-sdk';payload=sdk_root/'source-artifact';runtime=Path(cfg['preserved']);source=Path(cfg['source'])
    sdk_api=ROOT/'out/current-sdk-source/api.json';record=load(sdk_api);validate_api(record,cfg['configuration'])
    ident,size,checksum=PINS[cfg['configuration']];outer=ROOT/'out/current-sdk-source/producer.zip'
    require(outer.stat().st_size==size and sha(outer)==checksum,'Actual original source SDK API ZIP differs')
    buildpath=payload/'current-application.json';build=load(buildpath);item=build['configurations'][cfg['configuration']]
    require(sha(buildpath)==cfg['application_build_manifest_sha256'] and build['protocol']=='phase6-github-current-application-v1' and
            build['source_commit']==APPLICATION and build['owning_sources_unchanged'] is True and item['status']=='built' and
            Path(item['runtime'])==runtime,'Actual closed original C08 application receipt differs')
    archive=payload/'runtime.zip';require(sha(archive)==build['runtime_archive_sha256'] and archive.stat().st_size==build['runtime_archive_bytes'],
            'Actual sealed inner SDK archive differs')
    with zipfile.ZipFile(archive) as incoming:
        body=incoming.read('test-runtime.json');sealed=json.loads(body)
        require(digest(body)==item['sdk_manifest_sha256']==cfg['roles']['sdk']['manifest_sha256']==cfg['roles']['application']['manifest_sha256'] and
                sealed['source_commit']==APPLICATION and set(incoming.namelist())==set(sealed['files'])|{'test-runtime.json'} and
                len(incoming.namelist())==len(set(incoming.namelist())),'Actual complete original SDK manifest/member closure differs')
        for name,value in sealed['files'].items():require(digest(incoming.read(name))==value and sha(runtime/name)==value,'Actual original SDK archive or runtime byte differs')
        require(digest(incoming.read(ORIGINAL).replace(b'\r\n',b'\n'))==digest((ROOT/ORIGINAL).read_bytes().replace(b'\r\n',b'\n')) and
                digest(incoming.read('Config/Earth.cfg').replace(b'\r\n',b'\n'))==digest((ROOT/EARTH).read_bytes().replace(b'\r\n',b'\n')),
                'Actual original API script or locked SPICE Earth configuration differs')
    require(sha(runtime/'test-runtime.json')==digest(body),'Actual original SDK manifest changed')
    for name,value in build['source_guard_sha256_lf'].items():
        actual=(source/name).read_bytes().replace(b'\r\n',b'\n');immutable=subprocess.check_output(['git','-C',str(source),'show',APPLICATION+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(actual).hexdigest()==value==hashlib.sha256(immutable).hexdigest(),'Complete original application source closure differs')
    helper=source/'Tests/Production/CurrentWindows/retain_hosted_sdk.py'
    require(helper.read_bytes().replace(b'\r\n',b'\n')==subprocess.check_output(['git','-C',str(source),'show',APPLICATION+':Tests/Production/CurrentWindows/retain_hosted_sdk.py']).replace(b'\r\n',b'\n'),'Original SDK reader changed')
    spec=importlib.util.spec_from_file_location('original_current_API_sdk_reader',helper);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    units=reader.unit_result(load(payload/'registered-tests.json'),payload/'runtime-ctest.xml')
    require(units==item['tests'] and units['executed_processes']==28,'Every original C08 Windows unit/compiler receipt required')
    prepared=load(cfg['roles']['observer']['manifest_path']);obs=prepared['observer'];observer=Path(cfg['build'])
    require(sha(cfg['roles']['observer']['manifest_path'])==cfg['roles']['observer']['manifest_sha256'] and
            prepared['status']=='prepared-passive-observer-only' and prepared['sdk']['manifest_sha256']==digest(body) and
            obs['kind']=='general-api' and obs['source_commit']==obs['sdk_source_commit']==APPLICATION and obs['configuration']==cfg['configuration'] and
            sha(obs['binary'])==obs['sha256'] and obs['source_sha256']==digest(subprocess.check_output(['git','-C',str(source),'show',APPLICATION+':Tests/Production/GeneralApiCorrection/Observer.cpp'])),
            'Fresh actual API observer source/binary and exact compiled SDK differ')
    for command in prepared['commands']:
        require(command['actual_returncode']==0 and command['actual_pid']>0 and sha(observer/(command['label']+'.log'))==command['log_sha256'],'Actual API observer compiler process/log receipt differs')
    require(prepared['commands'] and prepared['compiler']['sha256']==sha(prepared['compiler']['path']),'Actual observed MSVC compiler identity differs')
    export=Path(cfg['export']);exports=worker['export_files_sha256']
    require(set(exports)=={x.relative_to(export).as_posix() for x in export.rglob('*') if x.is_file()} and
            all(sha(export/name)==value for name,value in exports.items()),'Complete actual raw API export byte closure differs')
    results=inspect_cases(cfg,worker,export,obs)
    from general_api_shaders import verify,inspect_staged
    verify(cfg)
    from inactive_stager_fixture import verify_staged as verify_inactive_fixture
    for name,item in worker['cases'].items():
        inspect_staged(export/name,cfg)
        verify_inactive_fixture(export/name,cfg)
        require(sha(item['observer']['dispatch_provider'])==item['provider_sha256'],'Actual observed system CRT provider byte changed')
    protected={str(x):sha(x) for folder in (share,export,observer) for x in folder.rglob('*') if x.is_file()}
    for path in (sdk_api,outer,buildpath,archive,runtime/'test-runtime.json',Path(cfg['variant']['manifest'])):protected[str(path)]=sha(path)
    require(all(sha(x)==value for x,value in protected.items()),'Actual API evidence changed during independent read')
    a.output.mkdir(parents=True)
    report=dict(protocol='audited-hosted-current-Windows-GeneralApi-v1',status='passed-current-Windows-api-diagnostic-only',
        configuration=cfg['configuration'],profiles=[cfg['configuration']+'-'+m for m in ('automatic','sse2')],roles=cfg['roles'],
        github=cfg['github'],transport_protocol=cfg['transport_protocol'],inherited_runner_context=worker['context'],actual_processes=8,results=results,
        inactive_stager_fixture=cfg['inactive_stager_fixture'],inactive_same_SDK_fixture_verified=True,original_staging_hash_guard_preserved=True,
        original_actual_case_auditor_sha256_lf=LEGACY_SHA256_LF,original_case_auditor_body_unchanged=True,
        compiled_application_source=APPLICATION,original_sdk_artifact_id=ident,original_sdk_archive_sha256=checksum,
        all_28_original_Windows_unit_receipts_preserved=True,observer_equivalence=True,
        evidence_sha256=protected,normal_admission_qualified=False,complete_general_api_qualification=False,phase6_complete=False,
        scope='Fresh hosted original failure, corrected API startup exit and passive-observer equivalence only')
    (a.output/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],profiles=report['profiles'],actual_processes=8)))


if __name__=='__main__':main()
