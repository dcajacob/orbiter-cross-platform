#!/usr/bin/env python3
"""Independently audit current-Windows API startup and real local launch receipts."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

from prepare import ROOT, ORIGINAL, EARTH, corrected, digest, require
from startup_contract import events, corrected_log, inspect_windows_roster

sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import load, sha, atomic_json
from receipts import inspect_launch, windows_path

SOURCES = {
    'capture_api.py': ['GeneralApiCorrection/capture_windows.py'],
    'runtime_descriptor_v2.py': ['Closeout/LocalVM/runtime_descriptor_v2.py'],
    'runtime_descriptor_v3.py': ['Closeout/LocalVM/runtime_descriptor_v3.py'],
    'static_binary_link_staging_v1.py': ['RemainingStockPersistence/LocalVM/static_binary_link_staging_v1.py'],
    **{name:[folder+'/LocalVM/'+name for folder in ('CurrentWindows','RemainingStockPersistence')]
       for name in ('win_local_process_v1.py','system_user_launcher_v1.py','private_desktop_bootstrap_v1.py')}}


def immutable(commit, name):
    return subprocess.check_output(['git','-C',str(ROOT),'show',commit+':Tests/Production/'+name])


def audit(capture, job, terminal, vm, observer, application, output):
    require(not output.exists(), 'Fresh independent Windows audit directory required')
    output.mkdir(parents=True)
    retained=output/'capture';shutil.copytree(capture,retained)
    cfg=load(retained/'request.json')
    for role,name in [('system-launch','system-launch'),('bootstrap-started','bootstrap-started'),('bootstrap-result','bootstrap-result')]:
        shutil.copy2(retained/(cfg['name']+'-'+role+'.json'),retained/(name+'.json'))
    for source,name in [(job,'guest-job.json'),(terminal,'guest-result.json'),(vm,'vm.json'),
                        (terminal.with_name(terminal.name+'.binding.json'),'guest-result.binding.json')]:
        shutil.copy2(source,retained/name)
    bound=load(retained/'guest-result.binding.json');guest=load(retained/'guest-job.json')
    require(bound==dict(job_sha256=sha(retained/'guest-job.json'),terminal_sha256=sha(retained/'guest-result.json'),
                        actual_guest_pid=guest['pid'],domain_uuid=guest['domain_uuid']), 'Actual terminal receipt binding differs')
    runners=load(retained/'runners.json');trusted=runners['files_sha256']
    require(set(trusted)==set(SOURCES) and runners['commit']==cfg['roles']['runner']['commit'] and
            sha(retained/'runners.json')==cfg['roles']['runner']['manifest_sha256'], 'Runner role/source closure differs')
    origins={}
    for name,candidates in SOURCES.items():
        matches=[candidate for candidate in candidates if digest(immutable(runners['commit'],candidate))==trusted[name]]
        require(matches, 'Runner does not match its immutable owning source: '+name)
        origins[name]=matches[0]
    cfg,worker,actual_vm=inspect_launch(retained,trusted)
    require(cfg['cohort']=='current-windows' and cfg['source_role']=='application' and
            cfg['capture_scope']==dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']) and
            cfg['math_profile']=='matrix' and cfg['roles']['application']['commit']==cfg['roles']['sdk']['commit'],
            'Current-Windows API-only scope required')
    require(worker['status']=='captured-current-Windows-original-and-corrected-api-diagnostic-only' and
            worker['actual_processes']==8 and worker['observer_equivalence'] is True and
            worker['owning_runtime_sdk_provider_unchanged'] is True and worker['diagnostic_only'] is True,
            'Closed complete current-Windows API capture required')
    exports=worker['export_files_sha256'];export=retained/'export'
    require(set(exports)=={p.relative_to(export).as_posix() for p in export.rglob('*') if p.is_file()}, 'Raw API export closure differs')
    require(all(sha(export/name)==checksum for name,checksum in exports.items()), 'Raw API export hash differs')
    # Independently re-read the actual preserved application and SDK archive.
    buildpath=application/'build-status.json';build=load(buildpath);item=build['configurations'][cfg['configuration']]
    require(sha(buildpath)==cfg['application_build_manifest_sha256'] and build['source_commit']==cfg['source_commit'] and
            build['owning_sources_unchanged'] is True and item['status']=='built', 'Current application build identity differs')
    archive=application/('runtime-'+cfg['configuration']+'.zip')
    with zipfile.ZipFile(archive) as z:
        body=z.read('test-runtime.json');sdk=json.loads(body)
        require(digest(body)==cfg['roles']['sdk']['manifest_sha256']==item['sdk_manifest_sha256'] and
                sdk['source_commit']==cfg['source_commit'] and
                set(z.namelist())==set(sdk['files'])|{'test-runtime.json'} and len(z.namelist())==len(set(z.namelist())),
                'Actual retained application/SDK manifest or archive closure differs')
        for name,checksum in sdk['files'].items():
            require(digest(z.read(name))==checksum, 'Actual retained application/SDK file differs: '+name)
        require(digest(z.read(ORIGINAL).replace(b'\r\n',b'\n'))==digest((ROOT/ORIGINAL).read_bytes()) and
                digest(z.read('Config/Earth.cfg').replace(b'\r\n',b'\n'))==digest((ROOT/EARTH).read_bytes()),
                'Actual original script or locked SPICE Earth differs')
    (output/'sdk-manifest.json').write_bytes(body);shutil.copy2(buildpath,output/'application-build.json')
    prepared_path=observer/(observer.name+'-status.json');prepared=load(prepared_path)
    require(sha(prepared_path)==cfg['roles']['observer']['manifest_sha256'] and
            prepared['status']=='prepared-passive-observer-only' and
            prepared['sdk']['manifest_sha256']==digest(body), 'Observer exact SDK/build role differs')
    obs=prepared['observer'];binary=observer/'ProductionGeneralApiObserver.dll'
    require(obs['kind']=='general-api' and obs['source_commit']==cfg['roles']['observer']['commit'] and
            obs['sdk_source_commit']==cfg['source_commit'] and obs['configuration']==cfg['configuration'] and
            sha(binary)==obs['sha256'] and digest(immutable(obs['source_commit'],'GeneralApiCorrection/Observer.cpp'))==obs['source_sha256'],
            'Actual observer DLL or immutable owning source differs')
    require(all(command['actual_returncode']==0 and type(command['actual_pid']) is int and command['actual_pid']>0 and
                sha(observer/(command['label']+'.log'))==command['log_sha256'] for command in prepared['commands']),
            'Actual observer compiler process/log receipt differs')
    shutil.copytree(observer,output/'observer-build')
    expected_script,unused=corrected((ROOT/ORIGINAL).read_bytes(),(ROOT/EARTH).read_bytes(),'v2')
    expected={(mode,test,observation) for mode in ('automatic','sse2') for test in ('original','corrected') for observation in ('off','on')}
    require(set(worker['cases'])=={'-'.join(key) for key in expected}, 'API matrix omitted or substituted a case')
    results={}
    for mode,test,observation in sorted(expected):
        name='-'.join((mode,test,observation));folder=export/name;record=worker['cases'][name]
        timing=load(folder/'process-timing.json');identity=load(folder/'api-observer.json');invocation=load(folder/'invocation.json')
        actual=load(folder/'diagnostic-invocation.json')
        require(timing==record['process'] and timing['timed_out'] is False and type(timing['actual_pid']) is int and
                timing['actual_pid']>0 and timing['actual_returncode']==0 and timing['timeout_seconds']==900 and
                type(timing['elapsed_wall_ns']) is int and timing['elapsed_wall_ns']>0 and
                load(folder/'process-result.json')==dict(returncode=0), 'Actual API simulator PID/exit/timeout receipt differs')
        require(identity==record['observer'] and identity['actual_pid']==timing['actual_pid'] and
                identity['initial_fma3']==1 and identity['active_fma3']==(0 if mode=='sse2' else 1) and
                identity['observation_enabled'] is (observation=='on') and identity['mxcsr_control']==8064,
                'Actual API observer/CPU mode differs')
        provider=windows_path(identity['dispatch_provider'])
        require(str(provider.parent).lower()=='c:\\windows\\system32' and
                provider.name.lower()==('ucrtbased.dll' if cfg['configuration']=='Debug' else 'ucrtbase.dll') and
                len(record['provider_sha256'])==64, 'Actual API CRT provider differs')
        guestfolder=windows_path(cfg['output'])/name
        argv=[str(guestfolder/'Orbiter.exe'),'--scenariox=Tests\\GeneralApiTest','--fixedstep=0.015625','--maxframes=60']
        require(invocation['argv']==argv==actual['argv'] and windows_path(record['folder'])==guestfolder and
                actual['stager_manifest_sha256']==sha(folder/'invocation.json') and
                actual['stager_cockpit_driver_is_inactive'] is True and actual['actual_api_observer_sha256']==obs['sha256'] and
                (actual['profile'],actual['variant'],actual['observation'])==(mode,test,observation), 'Actual API dispatch/module invocation differs')
        script=(folder/ORIGINAL).read_bytes();scenario=(folder/'Scenarios/Tests/GeneralApiTest.scn').read_bytes()
        require(script.replace(b'\r\n',b'\n')==((ROOT/ORIGINAL).read_bytes() if test=='original' else expected_script) and
                digest(script)==record['script_sha256']==actual['script_sha256'] and
                digest(scenario.replace(b'\r\n',b'\n'))==record['scenario_sha256_lf']==cfg['scenario_sha256_lf'],
                'Actual API script or unchanged scenario differs')
        config=(folder/'staged-Orbiter.cfg').read_text()
        require('  ProductionGeneralApiObserver\n' in config and '  OGLClient\n' in config and
                '  ProductionBehaviorDriver\n' not in config, 'Actual active modules differ')
        text=(folder/'Orbiter.log').read_text(errors='replace');assertions=events(text)
        require(assertions==record['assertion_events'], 'Recorded API assertions differ from raw log')
        roster=inspect_windows_roster(folder,observation=='on')
        if test=='corrected':
            corrected_log(text)
            require(record['script_result']=='passed-corrected-test' and record['graphics'] is None and
                    not (folder/'graphics-lifecycle.json').exists(), 'Original Windows abrupt startup-exit behavior changed')
        else:
            require(record['script_result']=='failed-inherited-assertion' and 'Assertion failed' in text and
                    assertions[-1]=='Test: planet status' and assertions.count(' - passed')==10 and
                    '=== All tests passed ===' not in text, 'Original failing API script was not preserved as failed')
            require(load(folder/'graphics-lifecycle.json')==record['graphics']==
                    dict(rendered_frames=60,successful_presents=60,context_deleted=True), 'Original API failure capture was incomplete')
        results[name]=dict(actual_pid=timing['actual_pid'],script_result=record['script_result'],
                           assertion_events=assertions,roster=roster,active_fma3=identity['active_fma3'],provider_sha256=record['provider_sha256'])
    for mode in ('automatic','sse2'):
        for test in ('original','corrected'):
            a=mode+'-'+test+'-off';b=mode+'-'+test+'-on'
            require(results[a]['assertion_events']==results[b]['assertion_events'] and
                    worker['cases'][a]['graphics']==worker['cases'][b]['graphics'], 'Observation changed actual API behavior')
            if test=='original':
                require((export/a/'Scenarios/(Current state).scn').read_bytes()==(export/b/'Scenarios/(Current state).scn').read_bytes(),
                        'Observation changed original final saved state')
    protected={str(p):sha(p) for p in output.rglob('*') if p.is_file()}
    protected[str(archive)]=sha(archive)
    result=dict(protocol='audited-current-windows-general-api-v1',status='passed-current-Windows-api-diagnostic-only',
        configuration=cfg['configuration'],profiles=[cfg['configuration']+'-'+mode for mode in ('automatic','sse2')],
        roles=cfg['roles'],vm=actual_vm,actual_processes=8,results=results,runner_source_origins=origins,
        evidence_sha256=protected,normal_admission_qualified=False,phase6_complete=False,
        scope='GeneralApiTest original failure, corrected startup exit and passive-observer equivalence only')
    require(all(sha(p)==checksum for p,checksum in protected.items()), 'Windows API evidence changed during independent audit')
    atomic_json(output/'audit.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','job','terminal','vm','observer','application','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=audit(a.capture,a.job,a.terminal,a.vm,a.observer,a.application,a.output)
    print(json.dumps(dict(status=result['status'],profiles=result['profiles'],actual_processes=result['actual_processes'])))
