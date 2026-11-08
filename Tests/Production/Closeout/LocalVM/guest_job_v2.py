"""Bind a real child exit to a fresh job nonce instead of trusting a recycled agent PID."""
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)


def start_identity(process):
    if sys.platform=='win32':
        from ctypes import wintypes as W
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetProcessTimes.argtypes=[W.HANDLE,*([ctypes.POINTER(W.FILETIME)]*4)];kernel.GetProcessTimes.restype=W.BOOL
        creation,exit_time,kernel_time,user_time=(W.FILETIME() for unused in range(4))
        require(kernel.GetProcessTimes(int(process._handle),*(ctypes.byref(value) for value in
                (creation,exit_time,kernel_time,user_time))), 'Actual Windows child creation time required')
        return dict(kind='windows-process-creation-filetime',value=(creation.dwHighDateTime<<32)|creation.dwLowDateTime)
    fields=Path('/proc/'+str(process.pid)+'/stat').read_text().rsplit(')',1)[1].split()
    return dict(kind='linux-process-start-ticks-control-only',value=int(fields[19]))


def main():
    path=Path(sys.argv[1]);cfg=json.loads(path.read_text());output=Path(cfg['result'])
    require(not output.exists(),'Fresh nonce-bound guest receipt required')
    report=dict(protocol='phase6-local-guest-job-v2',nonce=cfg['nonce'],request_sha256=sha(path),
        wrapper_sha256=sha(__file__),actual_wrapper_pid=os.getpid(),platform=sys.platform,
        target_script=cfg['script'],target_sha256=cfg['script_sha256'],target_argv=cfg['argv'],
        actual_target_pid=None,actual_target_returncode=None,started_wall_ns=time.time_ns())
    try:
        require(sys.platform==cfg['expected_platform'] and sha(__file__)==cfg['wrapper_sha256'] and
                sha(cfg['script'])==cfg['script_sha256'] and Path(sys.executable).resolve()==Path(cfg['python']).resolve(),
                'Actual platform, wrapper, Python or target script differs')
        process=subprocess.Popen([sys.executable,*cfg['argv']],cwd=cfg['cwd'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        report['actual_target_pid']=process.pid;report['actual_target_start_identity']=start_identity(process)
        stdout,stderr=process.communicate()
        report.update(actual_target_returncode=process.returncode,**{'out-data':base64.b64encode(stdout).decode(),
            'err-data':base64.b64encode(stderr).decode()})
        require(sha(cfg['script'])==cfg['script_sha256'],'Target script changed during execution')
        report.update(status='completed-nonce-bound-actual-child-exit',target_source_unchanged=True,finished_wall_ns=time.time_ns())
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:
        temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(output)
        print(json.dumps(report),flush=True)


if __name__=='__main__':main()
