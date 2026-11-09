"""Strict ordinary GitHub-runner identities, roots and complete single-lane scope."""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys

PROTOCOL='phase6-github-current-stock-source-complete-v3'
REPOSITORY='dcajacob/orbiter-cross-platform'
ROOT_NAMES={'source','preserved','build','data','planets','mesa','output','export'}
ROLES={'application','sdk','observer','runner'}


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def local_path(value):
    require(type(value) is str,'Explicit Windows path required')
    path=PureWindowsPath(value)
    require(path.is_absolute() and re.fullmatch('[A-Za-z]:',path.drive) and '..' not in path.parts and
            all(':' not in part for part in path.parts[1:]),'Absolute local Windows drive path required')
    return path


def validate(cfg):
    require(cfg['transport_protocol']==PROTOCOL and cfg['cohort']=='current-windows' and cfg['source_role']=='application',
            'Explicit hosted current-application transport required')
    require(not set(cfg)&{'domain_uuid','nonce','desktop','active_session','share_witness','bootstrap_script'},
            'VM and private-desktop claims cannot identify a hosted capture')
    workspace=local_path(cfg['workspace']);roots={name:local_path(value) for name,value in cfg['roots'].items()}
    require(set(roots)==ROOT_NAMES and all(path.is_relative_to(workspace) and path!=workspace for path in roots.values()),
            'Complete explicit roots below the actual runner workspace required')
    for name,path in roots.items():require(local_path(cfg[name])==path,'Declared root differs: '+name)
    for writable in ('output','export'):
        for name,path in roots.items():
            if name!=writable:require(not roots[writable].is_relative_to(path) and not path.is_relative_to(roots[writable]),
                                      'Capture/export overlaps another declared root: '+name)
    require(set(cfg['roles'])==ROLES,'Independent application, SDK, observer and collector roles required')
    for name,role in cfg['roles'].items():
        require(re.fullmatch('[0-9a-f]{40}',role['commit']) and re.fullmatch('[0-9a-f]{64}',role['manifest_sha256']),
                'Immutable actual runtime role required: '+name)
        allowed=roots['preserved'] if name in ('application','sdk') else roots['build'] if name=='observer' else workspace
        require(local_path(role['manifest_path']).is_relative_to(allowed),'Role manifest outside its owning root: '+name)
    require(cfg['source_commit']==cfg['roles']['application']['commit']==cfg['roles']['sdk']['commit'],
            'Actual current application and SDK producer differ')
    gh=cfg['github']
    require(gh['repository']==REPOSITORY and type(gh['run_id']) is int and gh['run_id']>0 and
            type(gh['run_attempt']) is int and gh['run_attempt']>0 and gh['collector_commit']==cfg['roles']['runner']['commit'],
            'Actual authorized GitHub run/collector identity required')
    require(cfg['configuration'] in ('Debug','Release') and cfg['math_profile'] in ('automatic','sse2') and cfg['phase'] in ('stock','reload') and
            type(cfg['scene_workers']) is int and cfg['scene_workers']==1 and type(cfg['minimum_free_bytes']) is int and cfg['minimum_free_bytes']>=8*1024**3,
            'One complete profile, one serial scene worker and unchanged capacity reserve required')
    return workspace,roots


def selection(cfg,config):
    validate(cfg);scope=cfg['capture_scope'];ids=[case['id'] for case in config['cases']]
    require(len(ids)==len(set(ids))==38 and scope==dict(kind='complete',gate='remaining-stock',cases=ids) and
            config['frames']==960,'All 38 complete original scenes and unchanged finalized ticks required')
    return list(config['cases']),False


def complete_phase_matrix(records,case_ids):
    expected={(c,m,p) for c in ('Debug','Release') for m in ('automatic','sse2') for p in ('stock','reload')}
    require(len(case_ids)==len(set(case_ids))==38 and len(records)==8,'Complete eight-cell current-stock phase matrix required')
    seen=set();sources=set()
    for report in records:
        key=(report['configuration'],report['math_profile'],report['captured_phase'])
        require(key in expected and key not in seen and report['phase']==key[2] and
                report['transport_protocol']==PROTOCOL and report['status']=='captured-current-Windows-stock-phase-awaiting-independent-audit',
                'Missing, duplicate or substituted current-stock phase')
        require(report['actual_processes']==76 and report['successful_presents']==76*960 and
                report['owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged'] is True and
                report['simulation_comparison_and_independent_audit_pending'] is True and
                report['phase6_complete'] is False and report['native_admission_qualified'] is False,
                'Complete original run counts, guards and pending audit status required')
        require(set(report['cases'])=={key[1]+'-'+key[2]+'-'+name for name in case_ids} and
                all(len(case['runs'])==2 for case in report['cases'].values()),'Complete two-repeat original case coverage required')
        require(re.fullmatch('[0-9a-f]{40}',report['source']),'Immutable current application source required')
        seen.add(key);sources.add(report['source'])
    require(seen==expected and len(sources)==1,'Complete matching current application source across both phases required')
    return dict(cells=8,actual_processes=608,successful_presents=608*960,source_commit=sources.pop(),
                physical_comparisons_and_independent_audit_pending=True,phase6_complete=False)


def context():
    """Observe the inherited station/desktop; never create or switch either."""
    require(sys.platform=='win32','Actual Windows context required')
    import ctypes
    from ctypes import wintypes
    user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user.GetProcessWindowStation.argtypes=[];user.GetProcessWindowStation.restype=wintypes.HANDLE
    kernel.GetCurrentThreadId.argtypes=[];kernel.GetCurrentThreadId.restype=wintypes.DWORD
    user.GetThreadDesktop.argtypes=[wintypes.DWORD];user.GetThreadDesktop.restype=wintypes.HANDLE
    user.GetUserObjectInformationW.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    user.GetUserObjectInformationW.restype=wintypes.BOOL
    kernel.ProcessIdToSessionId.argtypes=[wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype=wintypes.BOOL
    def name(handle):
        require(handle,'Actual inherited object handle missing');size=wintypes.DWORD()
        user.GetUserObjectInformationW(handle,2,None,0,ctypes.byref(size))
        require(0<size.value<65536,'Actual inherited object name size invalid')
        buffer=ctypes.create_unicode_buffer(size.value//ctypes.sizeof(ctypes.c_wchar))
        require(user.GetUserObjectInformationW(handle,2,buffer,ctypes.sizeof(buffer),ctypes.byref(size)),
                'Actual inherited object name could not be observed')
        require(buffer.value,'Empty inherited object name');return buffer.value
    session=wintypes.DWORD();require(kernel.ProcessIdToSessionId(os.getpid(),ctypes.byref(session)),'Actual Windows session could not be observed')
    return dict(actual_pid=os.getpid(),session=session.value,window_station=name(user.GetProcessWindowStation()),
                desktop=name(user.GetThreadDesktop(kernel.GetCurrentThreadId())),inherited_context_only=True)


def preflight(cfg):
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('ImageOS') in {'win25','win25-vs2026'},
            'Actual standard GitHub Windows 2025 runner required')
    workspace,roots=validate(cfg);gh=cfg['github']
    require(workspace==local_path(os.environ['GITHUB_WORKSPACE']) and gh['run_id']==int(os.environ['GITHUB_RUN_ID']) and
            gh['run_attempt']==int(os.environ['GITHUB_RUN_ATTEMPT']) and gh['collector_commit']==os.environ['GITHUB_SHA'],
            'Actual runner workspace/run/attempt/collector differs')
    for name,pure in roots.items():
        path=Path(pure)
        if name in ('output','export'):require(not path.exists() and not path.is_symlink() and path.parent.is_dir() and path.parent.resolve()==path.parent,'Fresh capture/export root required')
        else:require(path.is_dir() and path.resolve()==path,'Missing or redirected protected root: '+name)
    for name,role in cfg['roles'].items():
        require(sha(role['manifest_path'])==role['manifest_sha256'],'Actual role manifest changed: '+name)
    for name in ('reference_transport','reference_audit','reference_persistence_audit','reference_restoration'):
        require(local_path(cfg[name]['path']).is_relative_to(workspace) and sha(cfg[name]['path'])==cfg[name]['sha256'],
                'API-bound original Windows reference evidence changed')
    transport=json.loads(Path(cfg['reference_transport']['path']).read_text());audit=json.loads(Path(cfg['reference_audit']['path']).read_text())
    require(transport['protocol']=='remaining-stock-source-complete-hosted-transport-v2' and transport['status']=='passed' and
            audit['status']=='passed' and audit['producer_commit']==transport['source_commit'] and
            audit['download_manifest_sha256']==cfg['reference_transport']['sha256'] and audit['processes']==304 and
            audit['presentations']==304*960 and set(audit['profiles'])=={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')},
            'Complete independently audited original Windows writer cohort required')
    reference=reference_receipts(cfg)
    free=shutil.disk_usage(Path(roots['output']).parent).free
    require(free>=cfg['minimum_free_bytes'],'Complete stock capacity reserve unavailable')
    return dict(status='passed-actual-GitHub-Windows-root-and-capacity-preflight',protocol=PROTOCOL,
        github=gh,roots={name:str(path) for name,path in roots.items()},free_bytes=free,
        minimum_free_bytes=cfg['minimum_free_bytes'],actual_inherited_context=context(),
        reference_transport_sha256=cfg['reference_transport']['sha256'],reference_audit_sha256=cfg['reference_audit']['sha256'],
        source_complete_reference=reference)


def reference_receipts(cfg):
    """Bind all four unchanged full-audit receipts to the fresh original source/API cohort."""
    root=Path(__file__).resolve().parents[4]
    sys.path[:0]=[str(Path(__file__).resolve().parent),str(root/'Tests/Production/Closeout')]
    import restore_source_complete_reference as reference
    import source_complete_original_transport as transport
    names=('reference_transport','reference_audit','reference_persistence_audit','reference_restoration')
    for name in names:
        require(sha(cfg[name]['path'])==cfg[name]['sha256'],'Complete source-bound original reference receipt changed: '+name)
    manifest,writer,cohort,restored=[json.loads(Path(cfg[name]['path']).read_text()) for name in names]
    reference.audit_receipts(manifest,writer,cohort,cfg['reference_transport']['sha256'],cfg['reference_audit']['sha256'])
    run=transport.run_identity(manifest['workflow_run'])
    require(run['id']==transport.RUN and run['head_sha']==reference.ORIGINAL,
            'Exact complete original source/API cohort required at capture preflight')
    require(restored['protocol']=='phase6-source-complete-original-reference-restoration-v2' and
            restored['status']=='restored-exact-independently-audited-original-cohort-only' and
            restored['original_capture_source']==reference.ORIGINAL and restored['original_auditor_source']==reference.AUDITOR and
            restored['restorer_source']==cfg['roles']['runner']['commit'] and restored['original_windows_processes']==608 and
            restored['original_transport_sha256']==cfg['reference_transport']['sha256'] and
            restored['original_writer_audit_sha256']==cfg['reference_audit']['sha256'] and
            restored['original_cohort_audit_sha256']==cfg['reference_persistence_audit']['sha256'] and
            set(restored['original_api_archive_bindings'])==reference.PROFILES and
            restored['original_saves_relabelled'] is False and restored['current_or_native_qualification_granted'] is False and
            restored['phase6_complete'] is False and restored['native_admission_qualified'] is False,
            'Complete same-collector immutable original restoration and pending candidate acceptance required')
    return dict(original_capture_run_id=run['id'],original_capture_source=reference.ORIGINAL,original_auditor_source=reference.AUDITOR,
        original_transport_sha256=cfg['reference_transport']['sha256'],original_writer_audit_sha256=cfg['reference_audit']['sha256'],
        original_cohort_audit_sha256=cfg['reference_persistence_audit']['sha256'],
        original_restoration_sha256=cfg['reference_restoration']['sha256'],original_windows_processes=608,
        current_or_native_qualification_granted=False,phase6_complete=False)
