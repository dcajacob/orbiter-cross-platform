"""Audit retained local Windows VM execution without inventing GitHub identities."""
import base64
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import subprocess
import uuid

from observations import require, sha
import transport

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROTOCOL='remaining-stock-local-windows-vm-transport-v1'
RUNNERS=('full38_local_runtime_worker_v1.py','static_binary_link_staging_v1.py',
         'win_local_process_v1.py','private_desktop_bootstrap_v1.py','system_user_launcher_v1.py')
PHASES={'stock':'remaining-stock-repaired','reload':'remaining-stock-persistence'}


def load(path):return json.loads(Path(path).read_text())

def positive_pid(value):return type(value) is int and value>0

def windows_path(value):
    require(isinstance(value,str),'Local VM Windows path must be a string')
    path=PureWindowsPath(value)
    require(path.is_absolute() and re.fullmatch('[A-Za-z]:',path.drive) and '..' not in path.parts,
            'Local VM path must be an absolute local Windows volume path')
    return path


def source_pins(commit):
    require(isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit),'Immutable local runner commit required')
    result={}
    for name in RUNNERS:
        blob=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+
            (HERE/'LocalVM'/name).relative_to(ROOT).as_posix()])
        require(b'\r' not in blob,'Local VM runner Git blobs must retain exact LF bytes')
        result[name]=hashlib.sha256(blob).hexdigest()
    return result


def receipt_chain(decoded,profile,trusted_scripts):
    """Verify only the real launch/desktop chain; this earns no full-scope credit."""
    local=decoded/'local-vm';cfg=load(local/'request.json');system=load(local/'system-launch.json')
    started=load(local/'bootstrap-started.json');finished=load(local/'bootstrap-result.json');worker=load(local/'worker-result.json')
    job=load(local/'guest-job.json');terminal=load(local/'guest-result.json');vm=load(local/'vm.json')
    require(cfg['configuration']+'-'+cfg['math_profile']==profile and profile in transport.PROFILES,
            'Local VM request profile differs')
    require(positive_pid(cfg['active_session']) and re.fullmatch('[A-Za-z0-9-]+',cfg['name']) and re.fullmatch('[A-Za-z0-9]+',cfg['desktop']),
            'Normal local VM session/private desktop required')
    request_sha=sha(local/'request.json')
    require(all(r['request_sha256']==request_sha for r in (system,started,finished,worker)),
            'Local VM launch/worker request binding differs')
    require(system['status']=='launched-normal-user-local-runtime-bootstrap' and
            system['active_session']==cfg['active_session'] and positive_pid(system['actual_bootstrap_pid']) and
            system['no_desktop_switch'] is True,'Actual normal-user local VM launch receipt required')
    require(started['status']=='actual-private-runtime-worker-started' and
            finished['status']=='private-runtime-worker-finished' and finished['actual_worker_exitcode']==0 and
            finished['private_desktop_closed'] is True and
            positive_pid(started['actual_worker_pid']) and started['actual_worker_pid']==finished['actual_worker_pid'],
            'Actual local VM worker must finish normally and close its private desktop')
    for record in (started,finished):
        require(record['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop='Default') and
                record['desktop']==cfg['desktop'] and record['no_desktop_switch'] is True,
                'Local VM bootstrap desktop/session differs')
    require(worker.get('context',worker.get('desktop_context'))==dict(
        session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']),
        'Actual local VM worker context differs')
    require(worker['source']==cfg['source_commit'] and worker['configuration']==cfg['configuration'] and
            worker['math_profile']==cfg['math_profile'] and
            all(worker[k] is False for k in ('cloud_builds_used','native_admission_qualified','phase6_complete')),
            'Local VM worker source or qualification flags differ')
    for name,value in trusted_scripts.items():
        require(sha(local/'scripts'/name)==value,'Retained local runner bytes differ: '+name)
    for role in ('worker','bootstrap'):
        name=windows_path(cfg[role+'_script']).name
        require(name in trusted_scripts and cfg[role+'_sha256']==trusted_scripts[name] and
                windows_path(cfg[role+'_script'])==PureWindowsPath('O:/scripts')/name and
                (role!='bootstrap' or name=='private_desktop_bootstrap_v1.py'),
                'Executed local VM script differs from its trusted source: '+role)
    entry=("from system_user_launcher_v1 import main\nmain('O:/"+cfg['name']+"-request.json')\n").encode()
    require((local/'scripts/start.py').read_bytes()==entry and
            job['script_sha256']==hashlib.sha256(entry).hexdigest() and positive_pid(job['pid']) and
            windows_path(job['guest_script'])==PureWindowsPath('O:/scripts/start-'+cfg['name']+'.py'),
            'Actual local guest-agent entry script/identity differs')
    require(terminal['exited'] is True and terminal['exitcode']==0 and
            json.loads(base64.b64decode(terminal['out-data'],validate=True).decode())==system,
            'Actual terminal guest-agent result differs from the local user-launch receipt')
    require(isinstance(vm['domain_uuid'],str) and re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',vm['domain_uuid']) and
            vm['hypervisor']=='libvirt/kvm' and vm['domain_name']==job['domain'] and
            str(uuid.UUID(vm['domain_uuid']))==vm['domain_uuid'] and
            vm['guest_os_id']=='mswindows' and vm['guest_arch'] in ('x86_64','AMD64'),
            'Retained local Windows VM identity differs')
    return cfg,worker,vm


def inspect_profile(decoded,profile,producer,pins,members):
    cfg,worker,vm=receipt_chain(decoded,profile,pins)
    require(cfg['source_commit']==producer and
            windows_path(cfg['worker_script']).name=='full38_local_runtime_worker_v1.py' and
            cfg['staging_script_sha256']==pins['static_binary_link_staging_v1.py'],
            'Complete local full38 producer/runner binding required')
    require(worker['status']=='completed-local-Windows-all38-stock-and-exact-save-reload-candidate' and
            worker['actual_processes']==152 and worker['successful_presents']==145920 and
            worker['script_sha256']==pins['full38_local_runtime_worker_v1.py'] and
            worker['independent_full_persistence_audit_pending'] is True and
            worker['local_transport_admission_pending'] is True,
            'A whole completed local full38 writer/reload profile is required')
    require(windows_path(worker['export'])==windows_path(cfg['export']),'Closed local worker export root differs from request')
    output=windows_path(cfg['output']);build_path=windows_path(cfg['build'])
    parent_path=output/PHASES['stock'];reload_path=output/PHASES['reload']
    require(build_path!=parent_path and not build_path.is_relative_to(output),
            'Local build and capture roots must remain distinct')
    build_root=decoded/'remaining-stock-repaired-build'
    require(worker['build_manifest_sha256']==sha(build_root/'build.json'),
            'Local execution did not use the retained full38 build')
    captures={phase:load(decoded/folder/'capture.json') for phase,folder in PHASES.items()}
    expected_status={'stock':'captured-awaiting-independent-audit','reload':'captured-awaiting-independent-persistence-audit'}
    for phase,capture in captures.items():
        require(capture['status']==expected_status[phase] and capture['producer_commit']==producer and
                capture['configuration']+'-'+capture['math_profile']==profile and
                capture['diagnostic_only'] is False and not capture['failures'] and
                len(capture['cases'])==38 and set(capture['cases'])==set(capture['cases_requested']) and
                len(capture['cases_requested'])==38 and
                all(capture[k] is False for k in ('native_admission_qualified','phase6_complete')),
                'Complete unchanged local full38 capture scope required: '+phase)
    require(set(captures['stock']['cases'])==set(captures['reload']['cases']),
            'Local writer/reload case sets differ')
    require(captures['reload']['parent_capture_sha256']==sha(decoded/PHASES['stock']/'capture.json'),
            'Local reload parent capture differs')
    expected={(phase,case,repeat) for phase,capture in captures.items() for case in capture['cases'] for repeat in (1,2)}
    actual={}
    for receipt in worker['actual_process_receipts']:
        require(type(receipt['repeat']) is int and receipt['repeat'] in (1,2),'Actual local repeat number required')
        key=(receipt['phase'],receipt['case'],receipt['repeat'])
        require(key in expected and key not in actual,'Local full38 process receipt omitted, duplicated or substituted')
        folder=PHASES[key[0]]+'/'+key[1]+'-'+str(key[2]);timing=load(decoded/folder/'process-timing.json')
        require(windows_path(receipt['folder'])==output/PureWindowsPath(folder) and receipt['timing']==timing and
                positive_pid(timing['actual_pid']) and timing['actual_returncode']==0 and
                timing['timed_out'] is False and timing['timeout_seconds']==900 and
                type(timing['elapsed_wall_ns']) is int and timing['elapsed_wall_ns']>0,
                'Actual local full38 process path/PID/exit/timing differs')
        life=load(decoded/folder/'graphics-lifecycle.json')
        require(life==dict(rendered_frames=960,successful_presents=960,context_deleted=True),
                'Actual local full38 render lifetime incomplete')
        actual[key]=timing
    require(set(actual)==expected and len(actual)==152,'All152 actual local process receipts required')
    exports={str(transport.safe(str(PureWindowsPath(n)).replace('\\','/'))):v
             for n,v in worker['export_files_sha256'].items()}
    require(len(exports)==len(worker['export_files_sha256']) and all(n in members and members[n]==v for n,v in exports.items()),
            'Closed local worker export inventory/bytes differ')
    preservation=load(decoded/'local-vm/build-preservation.json');build_status=load(decoded/'local-vm/build-status.json')
    require(preservation['status']=='verified-local-preservation-of-both-completed-full38-build-closures' and
            build_status['status']=='completed-both-local-full38-Windows-builds-and-input-controls' and
            preservation['source']==build_status['source']==producer and
            preservation['build_job_proof_sha256']==sha(decoded/'local-vm/build-status.json'),
            'Completed preserved local build provenance required')
    conf=cfg['configuration'];preserved=preservation['configurations'][conf]
    require(preserved['build_manifest_sha256']==sha(build_root/'build.json')==
            build_status['profiles'][conf]['build_manifest_sha256'] and
            windows_path(build_status['profiles'][conf]['build'])==build_path,
            'Actual local build root/manifest differs')
    build_files={'remaining-stock-repaired-build/'+str(transport.safe(n)):v for n,v in preserved['files_sha256'].items()}
    require(all(n in members and members[n]==v for n,v in build_files.items()),'Preserved local build closure differs')
    configuration='configuration-input-controls.json'
    require(sha(decoded/configuration)==sha(build_root/configuration),
            'Retained local startup controls differ from their original output')
    build_files['remaining-stock-repaired-build/'+configuration]=sha(build_root/configuration)
    local_files={n for n in members if n.startswith('local-vm/')}
    allowed_local={'local-vm/'+n for n in ('request.json','system-launch.json','bootstrap-started.json',
        'bootstrap-result.json','worker-result.json','guest-job.json','guest-result.json','vm.json',
        'build-preservation.json','build-status.json')}|{'local-vm/scripts/'+n for n in (*RUNNERS,'start.py')}
    require(local_files==allowed_local and set(members)==set(exports)|set(build_files)|local_files,
            'Unexpected or missing local execution/archive file closure')
    return dict(vm_uuid=vm['domain_uuid'],actual_processes=152,successful_presents=145920,
                windows_roots={'remaining-stock-repaired':str(parent_path),
                               'remaining-stock-repaired-build':str(build_path)})


def inspect_matrix(manifest,archive_root,decoded,producer):
    require(manifest['status']=='passed' and manifest['protocol']==PROTOCOL and
            manifest['diagnostic_only'] is False and manifest['source_commit']==producer and
            re.fullmatch('[0-9a-f]{40}',producer) and len(manifest['artifacts'])==4 and
            {a['profile'] for a in manifest['artifacts']}==set(decoded)==transport.PROFILES and
            'workflow_run' not in manifest and
            manifest['native_admission_qualified'] is False and manifest['phase6_complete'] is False,
            'Complete four-profile local VM transport required; GitHub identities are not local provenance')
    pins=source_pins(manifest['runner_commit']);result={};archives=set()
    for item in manifest['artifacts']:
        profile=item['profile'];path=str(transport.safe(item['path']))
        require(path not in archives and 'api_artifact' not in item and re.fullmatch('[0-9a-f]{64}',item['sha256']) and
                type(item['bytes']) is int and item['bytes']>0,'Distinct retained local archive identity required')
        archives.add(path);archive=archive_root/path
        members=transport.inspect_archive(archive,decoded[profile],item['sha256'],item['bytes'])
        local=inspect_profile(decoded[profile],profile,producer,pins,members)
        result[profile]=dict(archive=str(archive),archive_sha256=item['sha256'],archive_bytes=item['bytes'],
            decoded_members_sha256=members,execution_kind='local-windows-vm',**local)
    require(len({v['vm_uuid'] for v in result.values()})==1,'Complete local matrix must identify its same actual Windows VM')
    return result
