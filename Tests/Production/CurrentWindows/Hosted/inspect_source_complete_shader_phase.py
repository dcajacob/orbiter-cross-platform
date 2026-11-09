"""Independently bind a hosted phase's API, collector, process and raw-export receipts."""
import hashlib
import json
from pathlib import Path,PureWindowsPath
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_complete_shader_provider import require,sha,validate,selection,reference_receipts
from execute_source_complete_shader_phase import terminal

CAPTURE='eaf9b0a802af9f8a1b57a0721818224340ac22af'
RUN=42590249236
APPLICATION='c08f93151827949ee3ad498f8021f35c11753fde'
EXPECTED={(c,m,p) for c in ('Debug','Release') for m in ('automatic','sse2') for p in ('stock','reload')}
REQUIRED_STEPS=(
    'Retain the separate immutable current application source owner',
    'Restore every exact SDK member and independently re-read all original source and unit receipts',
    'Verify the same immutable application and SDK from their separate source checkout',
    'Restore the original passive observer without recompilation or simulation',
    'Restore exact audited reference members and preserve every original transport and save byte',
    'Bind every missing renderer shader to the exact immutable compiled C08 source',
    'Stage every original current-stock data file and planetary input',
    'Stage the exact original software renderer DLLs and notices',
    'Prepare every exact original saved input and immutable runtime role for this complete phase',
    'Execute all 38 scenes twice in the inherited ordinary runner session',
    'Run actions/upload-artifact@v7')


def load(path):return json.loads(Path(path).read_text())


def api_identity(record,cell):
    require(cell in EXPECTED and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),
            'Exact authorized current phase repository and cell required')
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(type(run['id']) is int and run['id']==RUN and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and
            run['head_sha']==CAPTURE and run['head_branch']=='qualification/current-stock-capture-v4' and
            run['path']=='.github/workflows/phase6-current-shader-stock.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Complete immutable current eight-cell producer required')
    names={'Source-complete current stock '+' '.join(key) for key in EXPECTED}
    require(len(jobs)==9 and {j['name'] for j in jobs}==names|{'readiness'} and
            all(j['run_id']==run['id'] and j['head_sha']==CAPTURE and j['status']=='completed' and j['conclusion']=='success' for j in jobs),
            'Every actual current phase and readiness job must have completed successfully')
    for job in jobs:
        require(('ubuntu-24.04' if job['name']=='readiness' else 'windows-2025') in job['labels'],
                'Only the declared standard current qualification runners are accepted')
        if job['name']=='readiness':
            gate=[step for step in job['steps'] if step['name']=='Require the complete successful immutable independent original audit']
            require(len(gate)==1 and gate[0]['status']=='completed' and gate[0]['conclusion']=='success',
                    'Actual successful source-complete original audit readiness gate required')
            continue
        for name in REQUIRED_STEPS:
            steps=[s for s in job['steps'] if s['name']==name]
            require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success',
                    'Actual current collection step incomplete: '+name)
    job=next(j for j in jobs if j['name']=='Source-complete current stock '+' '.join(cell))
    require(type(artifact['id']) is int and artifact['id']>0 and artifact['name']=='shader-source-complete-current-stock-'+'-'.join(cell) and
            artifact['expired'] is False and type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<4*1024**3 and
            re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and artifact['workflow_run']['id']==run['id'] and
            artifact['workflow_run']['head_sha']==CAPTURE,'Exact successful current cell API artifact required')
    return job


def collector_sources(record,owner=ROOT):
    require(record['protocol']=='phase6-hosted-current-stock-runner-v1' and record['commit']==CAPTURE and
            record['legacy_worker_sha256_lf']=='dddbbf40656524ffa2dddcfcd745767ed270d3d46109917c2da3a89f66a15c51',
            'Exact conserved current collector manifest required')
    paths=subprocess.check_output(['git','-C',str(owner),'ls-tree','-r','--name-only',CAPTURE,'--','Tests/Production/CurrentWindows','Tests/Production/Closeout'],text=True).splitlines()
    expected={name for name in paths if name.endswith('.py')}|{
        'Tests/Production/Closeout/LocalVM/stock_runtime_worker_v3.py',
        'Tests/Production/Closeout/LocalVM/static_binary_link_staging_v2.py'}
    require(set(record['files_sha256'])==expected,'Complete exact current collector source closure required')
    for name,value in record['files_sha256'].items():
        body=subprocess.check_output(['git','-C',str(owner),'show',CAPTURE+':'+name]).replace(b'\r\n',b'\n')
        require(value in {hashlib.sha256(body).hexdigest(),hashlib.sha256(body.replace(b'\n',b'\r\n')).hexdigest()},
                'Actual collector differs from its immutable LF/CRLF owning source: '+name)
    return record['files_sha256']


def inspect_staging(cfg,worker):
    protocol='phase6-guarded-local-staging-v2'
    receipt=worker['staging_receipt'];controls=worker['staging_controls']
    require(cfg['staging_protocol']==receipt['protocol']==controls['protocol']==protocol and
            controls['status']=='passed-real-local-volume-copy-cache-and-hardlink-byte-equivalence',
            'Actual versioned local-volume staging controls missing')
    counts=receipt['linked_input_counts'];total=receipt['actual_link_count'];samples=receipt['link_samples']
    require(counts and all(type(v) is int and v>0 for v in counts.values()) and
            type(total) is int and total==sum(counts.values()) and
            receipt['link_sample_limit']==128 and len(samples)==min(total,128),
            'Actual staging totals or explicitly bounded sample scope differs')
    output=PureWindowsPath(cfg['output']);cache=output/'immutable-input-cache-v2'
    for path,checksum in receipt['cache_files_sha256'].items():
        value=PureWindowsPath(path)
        require(re.fullmatch('[0-9a-f]{64}',checksum) and value.parent==cache and value.name==checksum,
                'Guarded staging cache identity/path differs')
    for sample in samples:
        require(sample['source'] in counts and PureWindowsPath(sample['target']).is_relative_to(output) and
                (sample['linked_source']==sample['source'] or
                 PureWindowsPath(sample['linked_source']).is_relative_to(cache)),
                'Actual staging sample escaped its source/output/cache binding')
    return dict(protocol=protocol,actual_link_count=total,link_samples=len(samples),
                cache_files=len(receipt['cache_files_sha256']))


def process_receipts(cfg,worker,export):
    mode=cfg['math_profile'];phase=cfg['phase'];ids=cfg['capture_scope']['cases'];seen=set()
    expected={(identity,repeat) for identity in ids for repeat in (1,2)}
    for item in worker['actual_process_receipts']:
        key=(item['case'],item['repeat']);require(key in expected and key not in seen,'Missing/duplicate actual current process')
        seen.add(key);relative=mode+'-'+phase+'/'+key[0]+'-'+str(key[1]);timing=load(export/relative/'process-timing.json')
        require(timing==item['timing'] and item['math_profile']==mode and item['phase']==phase and
                timing['actual_returncode']==0 and timing['timed_out'] is False and timing['timeout_seconds']==900 and
                type(timing['actual_pid']) is int and timing['actual_pid']>0 and
                type(timing['elapsed_wall_ns']) is int and timing['elapsed_wall_ns']>0 and
                PureWindowsPath(item['folder'])==PureWindowsPath(cfg['output'])/relative,
                'Actual current raw process/PID/path/exit/timeout receipt differs')
    require(len(ids)==38 and len(worker['actual_process_receipts'])==76 and seen==expected,
            'All 38 original scenes and both actual process repetitions required')
    return len(seen)


def inspect(payload,record,cell,inputs,config):
    """Inspect actual decoded bytes; physical/reference/native comparisons remain separate gates."""
    job=api_identity(record,cell);name='-'.join(cell);share=payload/'current-stock-requests'/name
    cfg=load(share/'request.json');worker=load(share/'worker-result.json');runner=load(share/'runner-result.json')
    validate(cfg);selection(cfg,config)
    require((cfg['configuration'],cfg['math_profile'],cfg['phase'])==cell and cfg['name']==name and
            cfg['source_commit']==APPLICATION and cfg['github']==dict(repository='dcajacob/orbiter-cross-platform',
                run_id=record['run']['id'],run_attempt=1,collector_commit=CAPTURE),
            'Actual request/API profile, application and collector identities differ')
    roles=cfg['roles'];manifest=share/'runners.json';files=collector_sources(load(manifest))
    require(sha(manifest)==roles['runner']['manifest_sha256'] and
            roles['application']['commit']==roles['sdk']['commit']==roles['observer']['commit']==APPLICATION and
            inputs['status']=='inspected-immutable-Windows-build-and-observer-bytes-only' and inputs['configuration']==cell[0] and
            inputs['compiled_application_source']==inputs['compiled_observer_source']==APPLICATION and
            roles['application']['manifest_sha256']==roles['sdk']['manifest_sha256']==inputs['sdk_manifest_sha256'] and
            roles['observer']['manifest_sha256']==worker['observer_build_sha256']==inputs['observer_manifest_sha256'] and
            cfg['application_build_manifest_sha256']==inputs['original_sdk_manifest_sha256'] and
            PureWindowsPath(cfg['preserved'])==PureWindowsPath(inputs['runtime_original_path']),
            'Actual independently inspected current application, SDK and passive observer roles differ')
    request_sha=sha(share/'request.json');worker_sha=files['Tests/Production/CurrentWindows/Hosted/source_complete_shader_worker.py']
    require(runner['protocol']=='phase6-hosted-current-stock-owned-worker-v1' and
            runner['status']=='completed-one-current-stock-phase-awaiting-independent-audit' and
            runner['source_commit']==CAPTURE and runner['github']==cfg['github'] and runner['request_sha256']==request_sha and
            runner['worker_sha256']==worker_sha and runner['actual_worker_exitcode']==0 and runner.get('timed_out',False) is False and
            runner['worker_console_sha256']==sha(share/'worker-console.log') and runner['worker_result_sha256']==sha(share/'worker-result.json') and
            runner['guarded_sources_and_references_unchanged'] is True and runner['actual_simulator_processes']==76 and
            runner['independent_physical_camera_frame_and_saved_state_comparisons_pending'] is True and
            runner['phase6_complete'] is False and runner['native_admission_qualified'] is False and
            type(runner['actual_worker_pid']) is int and runner['actual_worker_pid']>0 and
            type(runner['elapsed_ns']) is int and runner['elapsed_ns']>0,'Actual owned current worker exit/source/log receipt differs')
    terminal(cfg,worker,runner['actual_worker_pid'],worker_sha,request_sha)
    preflight=worker['root_preflight']
    require(preflight['status']=='passed-actual-GitHub-Windows-root-and-capacity-preflight' and preflight['protocol']==cfg['transport_protocol'] and
            preflight['github']==cfg['github'] and {k:PureWindowsPath(v) for k,v in preflight['roots'].items()}==
            {k:PureWindowsPath(v) for k,v in cfg['roots'].items()} and preflight['actual_inherited_context']==worker['context'] and
            preflight['minimum_free_bytes']==cfg['minimum_free_bytes'] and preflight['free_bytes']>=cfg['minimum_free_bytes'] and
            all(preflight[key+'_sha256']==cfg[key]['sha256'] for key in ('reference_transport','reference_audit')),
            'Actual inherited current runner root/capacity/reference preflight differs')
    reference=inspect_reference(payload,cfg,preflight)
    export=payload/'current-stock-exports'/name
    actual={p.relative_to(export).as_posix():sha(p) for p in export.rglob('*') if p.is_file()}
    require(actual and actual==worker['export_files_sha256'],'Actual API-decoded complete current raw export differs')
    processes=process_receipts(cfg,worker,export);staging=inspect_staging(cfg,worker)
    from inspect_current_shader_inputs import inspect as inspect_shader_inputs
    shader=inspect_shader_inputs(payload,cfg,inputs,export,config)
    expected_shader={k:shader[k] for k in ('protocol','plan_sha256','compiled_source','actual_original_shader_and_include_count','original_sdk_modified','qualification_granted')}
    require(preflight['same_source_renderer_shaders']==expected_shader,'Actual per-process renderer source/byte proof differs from captured preflight')
    return dict(protocol='phase6-independent-shader-current-closed-phase-v3',status='bound-source-complete-current-API-source-process-and-raw-export-receipts-only',
        configuration=cell[0],math_profile=cell[1],phase=cell[2],actual_processes=processes,job_id=job['id'],
        compiled_application_source=APPLICATION,collector_source=CAPTURE,export=str(export),request=cfg,worker=worker,
        export_files_sha256=actual,staging=staging,source_complete_reference=reference,renderer_shader_inputs=shader,physical_clock_camera_frame_and_saved_state_comparisons_pending=True,
        native_comparisons_pending=True,phase6_complete=False,native_admission_qualified=False)


def inspect_reference(payload,cfg,preflight):
    """Resolve original Windows paths to exact API-decoded receipt members without rewriting captured bytes."""
    names={
        'reference_transport':'original-stock-audit/transport/download.json',
        'reference_audit':'original-stock-audit/independent/writer-audit.json',
        'reference_persistence_audit':'original-stock-audit/independent/original-persistence-audit.json',
        'reference_restoration':'reference-audit-restoration/restoration.json'}
    local=dict(cfg);workspace=PureWindowsPath(cfg['workspace'])
    for name,relative in names.items():
        require(PureWindowsPath(cfg[name]['path'])==workspace/'out'/relative,
                'Source-complete original receipt is outside its exact API-retained member: '+name)
        path=payload/relative
        require(path.is_file() and not path.is_symlink() and sha(path)==cfg[name]['sha256'],
                'Actual API-decoded source-complete original receipt differs: '+name)
        local[name]=dict(cfg[name],path=str(path))
    local['reference_retry_inputs']={}
    for relative,value in cfg['reference_retry_inputs'].items():
        require(PureWindowsPath(value['path'])==workspace/'out'/relative,'Retry member outside its exact retained path')
        path=payload/relative
        require(path.is_file() and not path.is_symlink() and sha(path)==value['sha256'],'Actual retained retry API/source member changed')
        local['reference_retry_inputs'][relative]=dict(value,path=str(path))
    bound=reference_receipts(local)
    require(preflight['source_complete_reference']==bound,
            'Actual worker source-complete original API/full-audit/restoration proof differs from independent raw receipts')
    return bound
