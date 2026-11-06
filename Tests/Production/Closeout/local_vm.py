#!/usr/bin/env python3
"""Submit one pinned script to the local libvirt guest, then retain its terminal receipt."""
import argparse
import json
from pathlib import Path, PureWindowsPath
import subprocess

from contracts import atomic_json, load, require, sha


def virsh(domain, request):
    output = subprocess.check_output(['virsh','-c','qemu:///session','qemu-agent-command',domain,
                                     json.dumps(request)],text=True)
    return json.loads(output)['return']


def submit(domain, expected_uuid, python, local_script, guest_script, arguments, output):
    require(not output.exists(), 'Fresh guest job receipt required; never relaunch an existing job')
    actual_uuid = subprocess.check_output(['virsh','-c','qemu:///session','domuuid',domain],text=True).strip()
    require(actual_uuid == expected_uuid, 'Actual local VM UUID differs')
    guest_script = str(PureWindowsPath(guest_script))
    argv = ['-B',guest_script,*arguments]
    request = dict(execute='guest-exec',arguments={'path':python,'arg':argv,'capture-output':True})
    report = dict(domain=domain,domain_uuid=actual_uuid,guest_script=guest_script,argv=argv,
                  script_sha256=sha(local_script),request=request,status='submitting')
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
    check=sub.add_parser('poll');check.add_argument('--job',type=Path,required=True)
    check.add_argument('--terminal',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='submit':
        result=submit(args.domain,args.uuid,args.python,args.script_local,args.script_guest,args.arg,args.output)
        print(json.dumps(dict(status=result['status'],pid=result['pid'])))
    else:
        result=poll(args.job,args.terminal)
        print(json.dumps({k:v for k,v in result.items() if k not in ('out-data','err-data')}))


if __name__=='__main__':main()
