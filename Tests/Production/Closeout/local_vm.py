#!/usr/bin/env python3
"""Submit one pinned script to the local libvirt guest, then retain its terminal receipt."""
import argparse
import base64
import json
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import uuid

from contracts import atomic_json, load, require, sha


def virsh(domain, request):
    output = subprocess.check_output(['virsh','-c','qemu:///session','qemu-agent-command',domain,
                                     json.dumps(request)],text=True)
    return json.loads(output)['return']


def submit(domain, expected_uuid, python, local_script, guest_script, arguments, output, receipt_v2=False):
    require(not output.exists(), 'Fresh guest job receipt required; never relaunch an existing job')
    actual_uuid = subprocess.check_output(['virsh','-c','qemu:///session','domuuid',domain],text=True).strip()
    require(actual_uuid == expected_uuid, 'Actual local VM UUID differs')
    guest_script = str(PureWindowsPath(guest_script))
    argv = ['-B',guest_script,*arguments]
    request = dict(execute='guest-exec',arguments={'path':python,'arg':argv,'capture-output':True})
    report = dict(domain=domain,domain_uuid=actual_uuid,guest_script=guest_script,argv=argv,
                  script_sha256=sha(local_script),request=request,status='submitting')
    if receipt_v2:
        nonce=uuid.uuid4().hex;local_script=Path(local_script);local_wrapper=local_script.parent/'guest_job_v2.py'
        wrapper=Path(__file__).parent/'LocalVM/guest_job_v2.py'
        if local_wrapper.exists():require(sha(local_wrapper)==sha(wrapper),'Staged guest wrapper differs')
        else:shutil.copy2(wrapper,local_wrapper)
        guest_parent=PureWindowsPath(guest_script).parent;guest_wrapper=guest_parent/'guest_job_v2.py'
        local_request=local_script.parent/('guest-job-'+nonce+'.json');local_result=local_request.with_suffix('.result.json')
        guest_request=guest_parent/local_request.name;guest_result=guest_parent/local_result.name
        envelope=dict(nonce=nonce,python=python,script=guest_script,script_sha256=report['script_sha256'],argv=argv,
            wrapper_sha256=sha(wrapper),expected_platform='win32',cwd=str(guest_parent),result=str(guest_result))
        atomic_json(local_request,envelope)
        request['arguments']['arg']=['-B',str(guest_wrapper),str(guest_request)]
        report['transport']=dict(protocol='phase6-local-guest-job-v2',nonce=nonce,wrapper_sha256=sha(wrapper),
            request_local=str(local_request),request_guest=str(guest_request),request_sha256=sha(local_request),
            result_local=str(local_result),result_guest=str(guest_result))
    atomic_json(output,report)
    try:
        result = virsh(domain,request)
        require(type(result['pid']) is int and result['pid'] > 0, 'Actual guest-agent process PID required')
        report.update(status='submitted',pid=result['pid'])
    except BaseException as error:
        report.update(status='submission-failed',error=str(error))
        raise
    finally:
        atomic_json(output,report)
    return report


def validate_nonce_receipt(job,record):
    transport=job['transport']
    require(record['protocol']==transport['protocol'] and record['nonce']==transport['nonce'] and
            record['request_sha256']==transport['request_sha256'] and record['wrapper_sha256']==transport['wrapper_sha256'] and
            record['actual_wrapper_pid']==job['pid'] and record['platform']=='win32' and
            record['target_script']==job['guest_script'] and record['target_sha256']==job['script_sha256'] and
            record['target_argv']==job['argv'], 'Nonce-bound guest identity differs')
    if record['status']=='failed':
        require(isinstance(record['error'],str) and record['error'],'Explicit nonce-bound transport failure required')
        return False
    require(record['status']=='completed-nonce-bound-actual-child-exit' and record['target_source_unchanged'] is True and
            type(record['actual_target_pid']) is int and record['actual_target_pid']>0 and
            type(record['actual_target_returncode']) is int and record['actual_target_start_identity']['kind']=='windows-process-creation-filetime' and
            type(record['actual_target_start_identity']['value']) is int and record['actual_target_start_identity']['value']>0,
            'Actual nonce-bound child source/PID/start/exit receipt differs')
    return True


def nonce_terminal(job,raw,terminal_path):
    transport=job['transport'];path=Path(transport['result_local'])
    if not path.exists():
        if raw.get('exited'):
            rejected=terminal_path.with_name(terminal_path.name+'.unmatched-agent-'+sha_bytes(raw)[:16]+'.json')
            if not rejected.exists():atomic_json(rejected,raw)
        return dict(exited=False,awaiting_nonce_bound_receipt=True)
    record=load(path);completed=validate_nonce_receipt(job,record)
    try:matched=raw.get('exited') is True and raw['exitcode']==0 and json.loads(base64.b64decode(raw['out-data'],validate=True))==record
    except (ValueError,KeyError,TypeError):matched=False
    return dict(exited=True,exitcode=record['actual_target_returncode'] if completed else 1,
        **{'out-data':record.get('out-data',''),'err-data':record.get('err-data',base64.b64encode(record.get('error','').encode()).decode())},
        transport_receipt=record,transport_receipt_sha256=sha(path),agent_receipt_matched=matched,agent_terminal=raw,
        terminal_basis='actual-owned-child-exit-and-fresh-nonce-bound-file' if completed else 'nonce-bound-transport-failure')


def sha_bytes(value):
    import hashlib
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def poll(job_path, terminal_path):
    binding_path=terminal_path.with_name(terminal_path.name+'.binding.json')
    if terminal_path.exists():
        binding=load(binding_path)
        require(binding['job_sha256']==sha(job_path) and binding['terminal_sha256']==sha(terminal_path),
                'Closed guest receipt binding differs')
        return load(terminal_path)
    job = load(job_path)
    require(job['status']=='submitted', 'Only an actually submitted guest job can be polled')
    actual_uuid = subprocess.check_output(['virsh','-c','qemu:///session','domuuid',job['domain']],text=True).strip()
    require(actual_uuid == job['domain_uuid'], 'Guest VM identity changed')
    result = virsh(job['domain'],dict(execute='guest-exec-status',arguments=dict(pid=job['pid'])))
    if job.get('transport',{}).get('protocol')=='phase6-local-guest-job-v2':result=nonce_terminal(job,result,terminal_path)
    if result.get('exited') is True:
        atomic_json(terminal_path,result)
        atomic_json(binding_path,dict(job_sha256=sha(job_path),terminal_sha256=sha(terminal_path),
                                      actual_guest_pid=job['pid'],domain_uuid=job['domain_uuid']))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('submit')
    run.add_argument('--domain',required=True);run.add_argument('--uuid',required=True)
    run.add_argument('--python',required=True);run.add_argument('--script-local',type=Path,required=True)
    run.add_argument('--script-guest',required=True);run.add_argument('--arg',action='append',default=[])
    run.add_argument('--output',type=Path,required=True)
    run.add_argument('--receipt-v2',action='store_true',help='Require a fresh nonce-bound actual child receipt; reject stale guest-agent PID results')
    check=sub.add_parser('poll');check.add_argument('--job',type=Path,required=True)
    check.add_argument('--terminal',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='submit':
        result=submit(args.domain,args.uuid,args.python,args.script_local,args.script_guest,args.arg,args.output,args.receipt_v2)
        print(json.dumps(dict(status=result['status'],pid=result['pid'])))
    else:
        result=poll(args.job,args.terminal)
        print(json.dumps({k:v for k,v in result.items() if k not in ('out-data','err-data','agent_terminal','transport_receipt')}))


if __name__=='__main__':main()
