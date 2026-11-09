#!/usr/bin/env python3
"""Run one owned ordinary-session worker and retain its real exit and closed phase scope."""
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
from source_complete_shader_provider import require,sha,validate


def terminal(cfg,worker,pid,worker_sha,request_sha):
    ids=cfg['capture_scope']['cases'];mode=cfg['math_profile'];phase=cfg['phase']
    require(len(ids)==len(set(ids))==38 and worker['status']=='captured-current-Windows-stock-phase-awaiting-independent-audit' and
            worker['transport_protocol']==cfg['transport_protocol'] and worker['configuration']==cfg['configuration'] and
            worker['math_profile']==mode and worker['phase']==worker['captured_phase']==phase and worker['source']==cfg['source_commit'] and
            worker['roles']==cfg['roles'] and worker['request_sha256']==request_sha and worker['script_sha256']==worker_sha and
            worker['cloud_builds_used'] is True and worker['diagnostic_only'] is False and worker['cases_requested']==ids and
            worker['repeats']==2 and worker['frames']==960 and worker['actual_processes']==76 and worker['successful_presents']==76*960 and
            worker['owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged'] is True and
            worker['simulation_comparison_and_independent_audit_pending'] is True and
            worker['native_admission_qualified'] is False and worker['phase6_complete'] is False,
            'Actual complete closed same-source hosted phase required')
    context=worker['context'];require(context['actual_pid']==pid and context['inherited_context_only'] is True and
            context['window_station'] and context['desktop'],'Actual inherited worker context/PID required')
    expected={(identity,repeat) for identity in ids for repeat in (1,2)};receipts=worker['actual_process_receipts']
    require(len(receipts)==76 and {(r['case'],r['repeat']) for r in receipts}==expected and
            all(r['phase']==phase and r['math_profile']==mode and type(r['timing']['actual_pid']) is int and
                r['timing']['actual_pid']>0 and r['timing']['actual_returncode']==0 and r['timing']['timed_out'] is False for r in receipts),
            'Every actual simulator process/repetition/phase/exit receipt required')
    require(set(worker['cases'])=={mode+'-'+phase+'-'+identity for identity in ids} and
            all(len(item['runs'])==2 for item in worker['cases'].values()),'Complete current hosted case/repetition coverage required')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request',type=lambda v:Path(v).resolve());a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and a.request.is_relative_to(ROOT/'out/current-stock-requests'),
            'Actual GitHub Windows owned stock phase request required')
    cfg=json.loads(a.request.read_text());validate(cfg);share=a.request.parent;manifest=Path(cfg['roles']['runner']['manifest_path'])
    require(sha(manifest)==cfg['roles']['runner']['manifest_sha256'],'Actual runner manifest changed')
    runners=json.loads(manifest.read_text());require(runners['commit']==cfg['github']['collector_commit']==os.environ['GITHUB_SHA'],
            'Actual immutable hosted collector differs')
    guarded={str(ROOT/name):value for name,value in runners['files_sha256'].items()}
    for item in cfg['windows_save_inputs']:guarded[item['path']]=item['sha256']
    for name in ('reference_transport','reference_audit','reference_persistence_audit','reference_restoration'):
        guarded[cfg[name]['path']]=cfg[name]['sha256']
    from retry_reference_proof import guarded as retry_guarded
    guarded.update(retry_guarded(cfg))
    from current_client_shaders import guarded as shader_guarded
    guarded.update(shader_guarded(cfg))
    guarded[str(a.request)]=sha(a.request);guarded[str(manifest)]=sha(manifest)
    require(all(sha(name)==value for name,value in guarded.items()),'Actual collector/reference/request bytes changed before worker launch')
    worker=Path(__file__).with_name('source_complete_shader_worker.py');argv=[sys.executable,'-B',str(worker),str(a.request)];receipt=share/'runner-result.json'
    require(not receipt.exists(),'Fresh owned worker receipt required')
    record=dict(protocol='phase6-hosted-current-stock-owned-worker-v1',status='running',argv=argv,cwd=str(ROOT),
        source_commit=os.environ['GITHUB_SHA'],github=cfg['github'],request_sha256=sha(a.request),worker_sha256=sha(worker),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase6_complete=False,native_admission_qualified=False)
    def save():receipt.write_text(json.dumps(record,indent=2)+'\n')
    started=time.monotonic_ns();log=share/'worker-console.log';save()
    try:
        with log.open('w') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stream,stderr=subprocess.STDOUT)
            record['actual_worker_pid']=child.pid;save()
            try:record['actual_worker_exitcode']=child.wait(timeout=18000)
            except subprocess.TimeoutExpired:
                record['timed_out']=True
                subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],check=False,stdout=stream,stderr=subprocess.STDOUT)
                record['actual_worker_exitcode']=child.wait(timeout=30);raise
        record['worker_console_sha256']=sha(log);require(record['actual_worker_exitcode']==0,'Actual current stock worker failed')
        outcome=json.loads((share/'worker-result.json').read_text())
        terminal(cfg,outcome,child.pid,sha(worker),sha(a.request))
        require(all(sha(name)==value for name,value in guarded.items()),'Actual collector/reference/request bytes changed during worker execution')
        sdk=json.loads((ROOT/'out/current-windows-sdk/restoration.json').read_text())
        require(all(sha(Path(sdk['runtime'])/name)==value for name,value in sdk['runtime_files_sha256'].items()),'Actual immutable current SDK changed')
        record.update(status='completed-one-current-stock-phase-awaiting-independent-audit',actual_simulator_processes=76,
            worker_result_sha256=sha(share/'worker-result.json'),guarded_sources_and_references_unchanged=True,
            independent_physical_camera_frame_and_saved_state_comparisons_pending=True)
    except BaseException as error:
        record.update(status='failed-or-incomplete-unqualified',error=str(error));print(log.read_text(errors='replace')[-16000:] if log.exists() else str(error),flush=True);raise
    finally:record['elapsed_ns']=time.monotonic_ns()-started;save()
    print(record['status'])


if __name__=='__main__':main()
