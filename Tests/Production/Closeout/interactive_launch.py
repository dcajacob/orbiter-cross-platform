"""Validate ordinary-session launch evidence separately from simulator gates."""
from pathlib import Path, PureWindowsPath
import re
import uuid

from contracts import load, require, sha
from LocalVM.runtime_descriptor_v2 import windows_path

PROTOCOL = 'phase6-interactive-windows-launch-v1'
RUNNER = 'interactive_runner_v1.py'
HELPER = 'windows_session_v1.py'
LEGACY = {'win_local_process_v1.py', 'system_user_launcher_v1.py', 'private_desktop_bootstrap_v1.py'}


def validate(config):
    launch = config['interactive_launch']
    require(launch['protocol'] == PROTOCOL and re.fullmatch('[0-9a-f]{32}', launch['nonce']),
            'Explicit nonce-bound interactive launch required')
    require(type(config['active_session']) is int and config['active_session'] > 0 and config['desktop'] == 'Default',
            'Existing visible Windows user session required')
    require(re.fullmatch('[A-Za-z0-9-]+', config['name']), 'Safe qualification job name required')
    scripts = windows_path(config['worker_script']).parent
    require(windows_path(config['bootstrap_script']) == scripts / RUNNER,
            'Interactive runner role differs')
    require(windows_path(config['request_path']).parent == scripts.parent,
            'Request must be beside its declared scripts directory')
    windows_path(launch['python'])
    result = PureWindowsPath(launch['worker_result'])
    require(len(result.parts) == 1 and result.suffix == '.json' and result.name not in
            ('request.json', 'runners.json', 'interactive-started.json', 'interactive-result.json'),
            'Worker result must be a separate local JSON filename')
    require(str(uuid.UUID(launch['domain_uuid'])) == launch['domain_uuid'] and
            isinstance(launch['domain_name'], str) and launch['domain_name'], 'Explicit local VM identity required')
    if 'scene_workers' in config or windows_path(config['worker_script']).name == 'full38_runtime_worker_v2.py':
        require(type(config.get('scene_workers')) is int and config['scene_workers'] == 1,
                'Interactive scene execution must be serial')
    return launch


def sources(files, legacy):
    """Old immutable packages keep their original helper and launcher closure."""
    result = dict(legacy)
    if RUNNER in files:
        result = {name: origin for name, origin in result.items() if name not in LEGACY}
        result[RUNNER] = 'Closeout/LocalVM/' + RUNNER
        result[HELPER] = 'Closeout/LocalVM/' + HELPER
    elif HELPER in files:
        result[HELPER] = 'Closeout/LocalVM/' + HELPER
    require(set(files) == set(result), 'Runner source/file closure differs')
    return result


def inspect(root, trusted_scripts, roots):
    root = Path(root)
    cfg = load(root / 'request.json')
    launch = validate(cfg)
    started = load(root / 'interactive-started.json')
    finished = load(root / 'interactive-result.json')
    worker = load(root / launch['worker_result'])
    vm = load(root / 'vm.json')
    expected_context = dict(session=cfg['active_session'], window_station='WinSta0', desktop='Default')
    require(not set(trusted_scripts) & LEGACY and {RUNNER, HELPER} <= set(trusted_scripts),
            'Interactive package must contain only its ordinary-session launch helpers')
    require({path.name for path in (root / 'scripts').iterdir()} == set(trusted_scripts),
            'Retained interactive script directory has undeclared files')
    manifest = load(root / 'runners.json')
    require(manifest['files_sha256'] == trusted_scripts and manifest['commit'] == cfg['roles']['runner']['commit'] and
            sha(root / 'runners.json') == cfg['roles']['runner']['manifest_sha256'],
            'Actual interactive runner manifest differs')
    for name, checksum in trusted_scripts.items():
        require(Path(name).name == name and sha(root / 'scripts' / name) == checksum,
                'Retained interactive runner bytes differ: ' + name)
    require(cfg['bootstrap_sha256'] == trusted_scripts[RUNNER] and
            cfg['worker_sha256'] == trusted_scripts[windows_path(cfg['worker_script']).name],
            'Executed interactive runner/worker source differs')
    request_hash = sha(root / 'request.json')
    for record in (started, finished):
        require(record['protocol'] == PROTOCOL and record['nonce'] == launch['nonce'] and
                record['request_sha256'] == request_hash and record['context'] == expected_context and
                record['platform'] == 'win32' and record['elevated'] is False and
                record['actual_machine_uuid'] == launch['domain_uuid'] and
                record['runner_sha256'] == trusted_scripts[RUNNER] and
                record['helper_sha256'] == trusted_scripts[HELPER] and
                record['worker_sha256'] == cfg['worker_sha256'] and
                record['scripts_sha256'] == trusted_scripts and
                type(record['actual_runner_pid']) is int and record['actual_runner_pid'] > 0 and
                type(record['actual_worker_pid']) is int and record['actual_worker_pid'] > 0 and
                record['actual_worker_pid'] != record['actual_runner_pid'] and
                record['worker_start_identity']['kind'] == 'windows-process-creation-filetime' and
                type(record['worker_start_identity']['value']) is int and record['worker_start_identity']['value'] > 0 and
                windows_path(record['python']) == windows_path(launch['python']) and
                record['worker_argv'] == ['-B', cfg['worker_script'], cfg['request_path']],
                'Actual interactive session/source/PID/start/arguments binding differs')
    require(started['status'] == 'started-interactive-windows-worker' and
            finished['status'] == 'completed-interactive-windows-worker' and
            all(finished[key] == value for key, value in started.items() if key != 'status') and
            finished['actual_worker_returncode'] == 0 and finished['inputs_unchanged'] is True and
            type(finished['elapsed_wall_ns']) is int and finished['elapsed_wall_ns'] > 0 and
            finished['worker_result_sha256'] == sha(root / launch['worker_result']) and
            finished['worker_log_sha256'] == sha(root / 'interactive-worker.log'),
            'Actual interactive worker must complete with unchanged inputs and retained output')
    require(worker['context'] == expected_context and worker['request_sha256'] == request_hash and
            worker['source'] == cfg['source_commit'] and worker['roles'] == cfg['roles'] and
            worker['transport_protocol'] == cfg['transport_protocol'] and worker['script_sha256'] == cfg['worker_sha256'] and
            worker['configuration'] == cfg['configuration'] and worker['math_profile'] == cfg['math_profile'] and
            all(worker[name] is False for name in ('cloud_builds_used', 'native_admission_qualified', 'phase6_complete')),
            'Interactive worker context, runtime roles, profile or qualification flags differ')
    preflight = worker['root_preflight']
    require(preflight['status'] == 'passed-actual-Windows-root-and-capacity-preflight' and
            preflight['protocol'] == cfg['transport_protocol'] and
            preflight['roots'] == {name: str(path) for name, path in roots.items()} and
            preflight['free_bytes'] >= preflight['minimum_free_bytes'] == cfg['minimum_free_bytes'] and
            preflight['share_witness_sha256'] == cfg['share_witness']['sha256'],
            'Actual interactive root/share/capacity preflight differs')
    require(vm['hypervisor'] == 'libvirt/kvm' and vm['guest_os_id'] == 'mswindows' and
            vm['guest_arch'] in ('x86_64', 'AMD64') and vm['domain_name'] == launch['domain_name'] and
            vm['domain_uuid'] == launch['domain_uuid'], 'Interactive local Windows VM identity differs')
    return cfg, worker, vm
