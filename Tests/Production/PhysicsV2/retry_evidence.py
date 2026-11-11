#!/usr/bin/env python3
"""Repeat only the timed-out pure evidence reader under its original Python environment."""
import datetime,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,load,atomic_json


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux','Hosted evidence replay only')
    profile=os.environ['PROFILE'];package=ROOT/'out/phase6-physics-v2-native'/profile;folder=ROOT/'out/physics-v2-unit-recheck'/profile;folder.mkdir(parents=True,exist_ok=False)
    selected=[t for t in load(package/'registered-unit-tests.json')['tests'] if t['name']=='Production.NativeCelestialEvidence'];require(len(selected)==1,'Exact original failed test inventory entry required');test=selected[0]
    command=test['command'];expected=ROOT/'Tests/Production/SpiceModules/Verification/verify.py'
    require(len(command)==3 and Path(command[0]).is_file() and command[1]=='-B' and Path(command[2]).resolve()==expected and expected.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show','6a2cbf646428339e0414b781b39943a34cbc2b7e:Tests/Production/SpiceModules/Verification/verify.py']),'Unchanged actual original pure evidence-reader command required')
    properties={p['name']:p['value'] for p in test['properties']};require(properties['TIMEOUT']==60,'Keep original60second test deadline')
    # This reader hashes existing ZIP/CSV evidence only and loads no instrumented
    # extension. Preserve the normal Python allocator; native tests keep ASan/UBSan.
    env=dict(os.environ)
    for name in ('LD_PRELOAD','PYTHONMALLOC'):env.pop(name,None)
    guarded={str(expected):sha(expected),str(package/'engine-tests.xml'):sha(package/'engine-tests.xml'),str(package/'complete-unit-verification.json'):sha(package/'complete-unit-verification.json')}
    report=dict(status='running',physics_version='assembly-contact-v2',profile=profile,command=command,original_timeout_seconds=60,original_failure_preserved=True,original_native_sanitizers_unchanged=True,prior_guarded_files_sha256=guarded,qualification_granted=False)
    atomic_json(folder/'verification.json',report);started=time.monotonic_ns()
    try:
        with (folder/'original-reader.log').open('wb') as stream:
            child=subprocess.Popen(command,cwd=properties['WORKING_DIRECTORY'],env=env,stdout=stream,stderr=subprocess.STDOUT);report['actual_pid']=child.pid
            try:report['actual_returncode']=child.wait(timeout=60)
            except subprocess.TimeoutExpired:child.kill();child.wait();report.update(timed_out=True,actual_returncode=child.returncode);raise
        require(report['actual_returncode']==0,'Unchanged original evidence reader failed or exceeded its original deadline')
        require(all(sha(p)==h for p,h in guarded.items()),'Prior original failure/source evidence changed')
        report.update(status='passed-original-evidence-reader-with-original60second-deadline',actual_elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(folder/'original-reader.log'),original32tests_complete_with_prior31passes=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:atomic_json(folder/'verification.json',report)


if __name__=='__main__':main()
