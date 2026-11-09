#!/usr/bin/env python3
"""Own the actual inherited-session API worker and retain every true process outcome."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from general_api_provider import require,sha,load,validate,preflight


def terminal(cfg,worker,pid,worker_sha,request_sha):
    require(worker['status']=='captured-current-Windows-original-and-corrected-api-diagnostic-only' and
            worker['actual_processes']==8 and worker['observer_equivalence'] is True and worker['owning_runtime_sdk_provider_unchanged'] is True and
            worker['transport_protocol']==cfg['transport_protocol'] and worker['source']==cfg['source_commit'] and worker['roles']==cfg['roles'] and
            worker['configuration']==cfg['configuration'] and worker['math_profile']=='matrix' and worker['request_sha256']==request_sha and
            worker['script_sha256']==worker_sha and worker['cloud_builds_used'] is True and worker['diagnostic_only'] is True and
            worker['native_admission_qualified'] is False and worker['phase6_complete'] is False,'Actual complete hosted API-only worker required')
    actual=worker['context'];require(type(pid) is int and pid>0 and actual['actual_pid']==pid and actual['inherited_context_only'] is True and actual['window_station'] and actual['desktop'],
            'Actual inherited worker context/PID required')
    pre=worker['root_preflight'];require(pre['status']=='passed-actual-inherited-GitHub-Windows-GeneralApi-preflight' and pre['protocol']==cfg['transport_protocol'] and pre['actual_context']==actual and pre['no_VM_or_private_desktop_setup_used'] is True,'Actual inherited worker preflight differs')
    expected={m+'-'+t+'-'+o for m in ('automatic','sse2') for t in ('original','corrected') for o in ('off','on')}
    require(set(worker['cases'])==expected,'Complete original/corrected observer-off/on API matrix required')
    for item in worker['cases'].values():
        timing=item['process'];require(timing['actual_returncode']==0 and timing['timed_out'] is False and timing['actual_pid']>0 and timing['timeout_seconds']==900,
                                      'Actual complete API simulator receipt required')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request',type=lambda v:Path(v).resolve());a=p.parse_args()
    require(a.request.is_relative_to(ROOT/'out/current-api-requests'),'Explicit owned hosted API request required')
    cfg=load(a.request);preflight(cfg);share=a.request.parent;runners=load(cfg['roles']['runner']['manifest_path'])
    require(runners['commit']==cfg['github']['collector_commit']==os.environ['GITHUB_SHA'],'Actual source-bound API runner required')
    protected={str(ROOT/name):v for name,v in runners['files_sha256'].items()}
    protected[str(a.request)]=sha(a.request)
    for item in cfg['roles'].values():protected[item['manifest_path']]=item['manifest_sha256']
    from general_api_shaders import guarded
    from inactive_stager_fixture import guarded as fixture_guarded
    protected.update(fixture_guarded(cfg))
    protected.update(guarded(cfg));require(all(sha(name)==v for name,v in protected.items()),'Actual API source/request/role inputs changed')
    worker=Path(__file__).with_name('general_api_worker.py');argv=[sys.executable,'-B',str(worker),str(a.request)]
    result=share/'runner-result.json';require(not result.exists(),'Fresh owned API worker receipt required')
    report=dict(protocol='phase6-hosted-current-GeneralApi-owned-worker-v1',status='running',argv=argv,cwd=str(ROOT),
        source_commit=os.environ['GITHUB_SHA'],github=cfg['github'],request_sha256=sha(a.request),worker_sha256=sha(worker),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase6_complete=False,native_admission_qualified=False)
    def save():result.write_text(json.dumps(report,indent=2)+'\n')
    log=share/'worker-console.log';started=time.monotonic_ns();save()
    try:
        with log.open('w') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stream,stderr=subprocess.STDOUT);report['actual_worker_pid']=child.pid;save()
            try:report['actual_worker_exitcode']=child.wait(timeout=18000)
            except subprocess.TimeoutExpired:
                report['timed_out']=True;subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=stream,stderr=subprocess.STDOUT,check=False)
                report['actual_worker_exitcode']=child.wait(timeout=30);raise
        require(report['actual_worker_exitcode']==0,'Actual hosted API worker failed');outcome=load(share/'worker-result.json')
        terminal(cfg,outcome,child.pid,sha(worker),sha(a.request))
        require(all(sha(name)==v for name,v in protected.items()),'Actual API source/request/role inputs changed during execution')
        sdk=load(ROOT/'out/current-windows-sdk/restoration.json');require(all(sha(Path(sdk['runtime'])/n)==v for n,v in sdk['runtime_files_sha256'].items()),'Exact original SDK changed during API execution')
        report.update(status='completed-current-Windows-GeneralApi-awaiting-independent-audit',actual_simulator_processes=8,
            worker_result_sha256=sha(share/'worker-result.json'),guarded_sources_requests_and_roles_unchanged=True,
            independent_actual_API_assertion_audit_pending=True)
    except BaseException as error:
        report.update(status='failed-or-incomplete-unqualified',error=str(error));print(log.read_text(errors='replace')[-16000:] if log.exists() else str(error));raise
    finally:
        report.update(elapsed_ns=time.monotonic_ns()-started,worker_console_sha256=sha(log) if log.exists() else None);save()
    print(report['status'])


if __name__=='__main__':main()
