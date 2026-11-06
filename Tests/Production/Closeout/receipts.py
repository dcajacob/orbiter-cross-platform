"""Read v2 local Windows launch receipts; historical v1 readers remain immutable."""
import base64
import json
from pathlib import Path
import re
import uuid

from contracts import case_ids, load, require, sha
from LocalVM.runtime_descriptor_v2 import validate, windows_path, capture_selection


def pid(value):
    return type(value) is int and value > 0


def inspect_launch(root, trusted_scripts):
    root = Path(root)
    config = load(root/'request.json')
    roots = validate(config)
    records = {name:load(root/(name+'.json')) for name in
               ('system-launch','bootstrap-started','bootstrap-result','worker-result','guest-job','guest-result','vm')}
    system = records['system-launch']; started = records['bootstrap-started']
    finished = records['bootstrap-result']; worker = records['worker-result']
    job = records['guest-job']; terminal = records['guest-result']; vm = records['vm']
    request_sha = sha(root/'request.json')
    require(type(config['active_session']) is int and config['active_session'] > 0 and
            re.fullmatch('[A-Za-z0-9-]+',config['name']) and re.fullmatch('[A-Za-z0-9]+',config['desktop']),
            'Actual normal-user session and private desktop required')
    require(all(value['request_sha256'] == request_sha for value in (system,started,finished,worker)),
            'Launch request hash binding differs')
    require(system['status'] == 'launched-normal-user-bootstrap' and
            system['active_session'] == config['active_session'] and pid(system['actual_bootstrap_pid']) and
            system['no_desktop_switch'] is True, 'Normal-user launcher receipt incomplete')
    require(started['status'] == 'actual-private-worker-started' and
            finished['status'] == 'actual-private-worker-finished' and
            finished['actual_worker_exitcode'] == 0 and finished['private_desktop_closed'] is True and
            pid(started['actual_worker_pid']) and started['actual_worker_pid'] == finished['actual_worker_pid'],
            'Private worker must finish and close its desktop')
    for record in (started,finished):
        require(record['context'] == dict(session=config['active_session'],window_station='WinSta0',desktop='Default') and
                record['desktop'] == config['desktop'] and record['no_desktop_switch'] is True and
                record['bootstrap_sha256'] == config['bootstrap_sha256'], 'Bootstrap context or identity differs')
    require(worker['context'] == dict(session=config['active_session'],window_station='WinSta0',desktop=config['desktop']) and
            worker['source'] == config['source_commit'] and worker['roles'] == config['roles'] and
            worker['transport_protocol'] == config['transport_protocol'] and
            worker['script_sha256'] == config['worker_sha256'] and
            worker['configuration'] == config['configuration'] and worker['math_profile'] == config['math_profile'],
            'Worker context, runtime roles or profile differs')
    require(all(worker[name] is False for name in ('cloud_builds_used','native_admission_qualified','phase6_complete')),
            'Local collector cannot claim hosted compute or acceptance')
    require(system['launcher_sha256'] == trusted_scripts['system_user_launcher_v1.py'], 'Launcher source differs')
    for name,digest in trusted_scripts.items():
        require(sha(root/'scripts'/name) == digest, 'Retained runner bytes differ: '+name)
    scripts = windows_path(config['worker_script']).parent
    for role in ('worker','bootstrap'):
        path = windows_path(config[role+'_script'])
        require(path.parent == scripts and path.name in trusted_scripts and
                config[role+'_sha256'] == trusted_scripts[path.name], 'Executed runner identity differs: '+role)
    require(windows_path(config['bootstrap_script']).name == 'private_desktop_bootstrap_v1.py',
            'Bootstrap role was substituted')
    require(pid(job['pid']) and windows_path(job['guest_script']) == scripts/'system_user_launcher_v1.py' and
            job['script_sha256'] == system['launcher_sha256'] and
            len(job['argv']) == 3 and job['argv'][0] == '-B' and
            windows_path(job['argv'][1]) == scripts/'system_user_launcher_v1.py' and
            windows_path(job['argv'][2]) == windows_path(config['request_path']),
            'Actual guest-agent launcher invocation differs')
    require(terminal['exited'] is True and terminal['exitcode'] == 0 and
            json.loads(base64.b64decode(terminal['out-data'],validate=True)) == system,
            'Actual terminal guest-agent result differs')
    require(vm['hypervisor'] == 'libvirt/kvm' and vm['domain_name'] == job['domain'] and
            vm['guest_os_id'] == 'mswindows' and vm['guest_arch'] in ('x86_64','AMD64') and
            str(uuid.UUID(vm['domain_uuid'])) == vm['domain_uuid'] == job['domain_uuid'],
            'Local Windows VM identity differs')
    preflight = worker['root_preflight']
    require(preflight['status'] == 'passed-actual-Windows-root-and-capacity-preflight' and
            preflight['protocol'] == config['transport_protocol'] and
            preflight['roots'] == {name:str(path) for name,path in roots.items()} and
            preflight['free_bytes'] >= preflight['minimum_free_bytes'] == config['minimum_free_bytes'] and
            preflight['share_witness_sha256'] == config['share_witness']['sha256'],
            'Actual declared root/share/capacity preflight differs')
    return config,worker,vm


def inspect_full38_processes(decoded, config, worker):
    """Check exact process coverage separately from simulation/state/image auditors."""
    require(worker['status'] == 'completed-local-Windows-all38-stock-and-exact-save-reload-candidate' and
            worker['actual_processes'] == 152 and worker['successful_presents'] == 145920,
            'Completed full38 worker required')
    expected = {(phase,case,repeat) for phase in ('stock','reload') for case in case_ids() for repeat in (1,2)}
    require(not capture_selection(config)['diagnostic_only'] and worker.get('diagnostic_only',False) is False,
            'Selected captures cannot satisfy a full38 process gate')
    count=inspect_processes(decoded,config,worker,expected)
    return dict(status='audited-full38-process-receipts-only',actual_processes=count,
                complete_simulation_audit_pending=True,phase6_complete=False)


def inspect_selected_processes(decoded, config, worker):
    selection=capture_selection(config)
    require(selection['diagnostic_only'] and worker['diagnostic_only'] is True and
            worker['status']=='completed-local-Windows-selected-stock-and-exact-save-reload-diagnostic-only' and
            worker['cases_requested']==selection['cases'] and
            worker['actual_processes']==selection['expected_processes'] and
            worker['successful_presents']==selection['expected_presents'],
            'Completed explicitly selected diagnostic worker required')
    expected={(phase,case,repeat) for phase in ('stock','reload') for case in selection['cases'] for repeat in (1,2)}
    count=inspect_processes(decoded,config,worker,expected)
    return dict(status='audited-selected-process-receipts-diagnostic-only',actual_processes=count,
                diagnostic_only=True,complete_simulation_audit_pending=True,phase6_complete=False)


def inspect_processes(decoded,config,worker,expected):
    seen = set()
    folders = {'stock':'remaining-stock-repaired','reload':'remaining-stock-persistence'}
    for item in worker['actual_process_receipts']:
        key = (item['phase'],item['case'],item['repeat'])
        require(type(item['repeat']) is int and key in expected and key not in seen,
                'Process coverage omitted, duplicated or substituted')
        folder = folders[key[0]]+'/'+key[1]+'-'+str(key[2])
        require(windows_path(item['folder']) == windows_path(config['output'])/folder,
                'Process output root differs')
        timing = load(Path(decoded)/folder/'process-timing.json')
        require(timing == item['timing'] and pid(timing['actual_pid']) and timing['actual_returncode'] == 0 and
                timing['timed_out'] is False and timing['timeout_seconds'] == 900 and
                type(timing['elapsed_wall_ns']) is int and timing['elapsed_wall_ns'] > 0,
                'Actual simulator PID/exit/timing differs')
        require(load(Path(decoded)/folder/'graphics-lifecycle.json') ==
                dict(rendered_frames=960,successful_presents=960,context_deleted=True),
                'Simulator graphics lifetime incomplete')
        seen.add(key)
    require(seen == expected, 'Every declared simulator process receipt required')
    return len(seen)
