"""Actual inherited standard Windows runner identity for fresh General API diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
from source_complete_shader_provider import context,local_path
PROTOCOL='phase6-github-current-GeneralApi-v2-inactive-fixture'
APPLICATION='c08f93151827949ee3ad498f8021f35c11753fde'
REPOSITORY='dcajacob/orbiter-cross-platform'
ROOTS={'source','preserved','build','data','planets','mesa','output','export'}


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load(path):return json.loads(Path(path).read_text())


def validate(cfg):
    require(cfg['transport_protocol']==PROTOCOL and cfg['cohort']=='current-windows' and cfg['source_role']=='application',
            'Explicit actual hosted current API transport required')
    require(not set(cfg)&{'domain_uuid','nonce','desktop','active_session','share_witness','bootstrap_script','interactive_launch'},
            'VM/private-desktop metadata cannot identify a hosted API capture')
    workspace=local_path(cfg['workspace']);roots={k:local_path(v) for k,v in cfg['roots'].items()}
    require(set(roots)==ROOTS and all(v.is_relative_to(workspace) and v!=workspace for v in roots.values()),
            'All explicit API roots must remain below the actual workspace')
    for key,value in roots.items():
        require(local_path(cfg[key])==value and not any(ord(c)<32 for c in cfg[key]),'Declared API root differs')
    for writable in ('output','export'):
        for key,value in roots.items():
            if key!=writable:require(not roots[writable].is_relative_to(value) and not value.is_relative_to(roots[writable]),
                                     'Writable API root overlaps another owning role')
    require(set(cfg['roles'])=={'application','sdk','observer','runner'},'Explicit actual application/SDK/observer/runner roles required')
    require(cfg['configuration'] in ('Debug','Release') and cfg['name']==cfg['configuration']+'-GeneralApi' and
            cfg['math_profile']=='matrix' and cfg['capture_scope']==dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']),
            'Complete original/corrected observer-off/on two-math-profile API diagnostic required')
    require(cfg['source_commit']==APPLICATION==cfg['roles']['application']['commit']==cfg['roles']['sdk']['commit']==cfg['roles']['observer']['commit'],
            'Actual same-source C08 application/SDK/API observer required')
    for role,item in cfg['roles'].items():
        require(re.fullmatch('[0-9a-f]{40}',item['commit']) and re.fullmatch('[0-9a-f]{64}',item['manifest_sha256']),
                'Immutable API role identity required')
        allowed=roots['preserved'] if role in ('application','sdk') else roots['build'] if role=='observer' else workspace
        require(local_path(item['manifest_path']).is_relative_to(allowed),'API role manifest outside its owning root')
    gh=cfg['github'];require(gh['repository']==REPOSITORY and type(gh['run_id']) is int and gh['run_id']>0 and
            type(gh['run_attempt']) is int and gh['run_attempt']==1 and gh['collector_commit']==cfg['roles']['runner']['commit'],
            'Exact actual hosted API run/attempt/collector required')
    require(type(cfg['minimum_free_bytes']) is int and cfg['minimum_free_bytes']>=8*1024**3,'Original capacity reserve required')
    require(local_path(cfg['variant']['manifest']).is_relative_to(workspace/'out/current-api-variant') and
            local_path(cfg['variant']['script']).is_relative_to(workspace/'out/current-api-variant'),
            'Versioned test correction must retain a separate owned input root')
    fixture=cfg['inactive_stager_fixture']
    require(fixture['protocol']=='phase6-inactive-original-C08-stager-fixture-v1' and fixture['compiled_source']==APPLICATION and
            fixture['intended_module_enabled'] is False and fixture['sdk_manifest_sha256']==cfg['roles']['sdk']['manifest_sha256'] and
            local_path(fixture['binary'])==workspace/'out/current-stock-preparation/observer/ProductionCockpitDriver.dll' and
            local_path(fixture['restoration_path'])==workspace/'out/current-observer-restoration/restoration.json',
            'Exact separately declared inactive original fixture and same SDK required')
    from general_api_shaders import validate_paths
    validate_paths(cfg,workspace)
    return workspace,roots


def preflight(cfg):
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Windows' and
            os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('ImageOS') in {'win25','win25-vs2026'},
            'Actual ordinary standard GitHub Windows2025 session required')
    workspace,roots=validate(cfg);gh=cfg['github']
    require(workspace==local_path(os.environ['GITHUB_WORKSPACE']) and gh['collector_commit']==os.environ['GITHUB_SHA'] and
            gh['run_id']==int(os.environ['GITHUB_RUN_ID']) and gh['run_attempt']==int(os.environ['GITHUB_RUN_ATTEMPT']),
            'Actual inherited runner workspace/run/source differs')
    for key,pure in roots.items():
        path=Path(pure)
        if key in ('output','export'):require(not path.exists() and not path.is_symlink() and path.parent.is_dir() and path.parent.resolve()==path.parent,'Fresh actual API capture/export root required')
        else:require(path.is_dir() and path.resolve()==path,'Missing or redirected API protected root')
    for role,item in cfg['roles'].items():require(sha(item['manifest_path'])==item['manifest_sha256'],'Actual API role manifest changed')
    require(sha(cfg['application_build_manifest'])==cfg['application_build_manifest_sha256'] and
            sha(cfg['variant']['manifest'])==cfg['variant']['manifest_sha256'],'Actual SDK or versioned test correction changed')
    from general_api_shaders import verify
    shaders=verify(cfg)
    free=shutil.disk_usage(Path(roots['output']).parent).free;require(free>=cfg['minimum_free_bytes'],'Original API capture free-space reserve unavailable')
    return dict(status='passed-actual-inherited-GitHub-Windows-GeneralApi-preflight',protocol=PROTOCOL,
                actual_context=context(),actual_free_bytes=free,shader_inputs=shaders,
                no_VM_or_private_desktop_setup_used=True,qualification_granted=False)
