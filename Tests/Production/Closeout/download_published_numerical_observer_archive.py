#!/usr/bin/env python3
"""Stream the exact source-bound published observer archive on a standard hosted worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from contracts import ROOT,require,load,sha,atomic_json
from inspect_published_numerical_observers import validate_api

REPOSITORY='dcajacob/orbiter-cross-platform'
GH=['gh','api','--hostname','github.com']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lock',type=Path,required=True);p.add_argument('--output',type=lambda s:Path(s).resolve(),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh actual standard hosted same-repository transport only; no local raw download')
    pin=load(a.lock);require(type(pin['archive_bytes']) is int and 0<pin['archive_bytes']<8*1024**3,'Exact bounded published archive required')
    out=a.output;out.mkdir(parents=True);repo='repos/'+REPOSITORY;run=repo+'/actions/runs/'+str(pin['run_id']);artifact=repo+'/actions/artifacts/'+str(pin['artifact_id'])
    def get(path):return json.loads(subprocess.check_output([*GH,path],timeout=60))
    api=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=get(run),jobs=get(run+'/jobs?per_page=100')['jobs'],artifact=get(artifact));atomic_json(out/'api.json',api);validate_api(api,pin)
    argv=['timeout','--foreground','900',*GH,artifact+'/zip'];report=dict(protocol='phase6-streamed-exact-published-numerical-observer-archive-v1',source=os.environ['GITHUB_SHA'],artifact_id=pin['artifact_id'],expected_bytes=pin['archive_bytes'],expected_sha256=pin['archive_sha256'],archive_api_sha256=sha(out/'api.json'),argv=argv,attempts=[],qualification_granted=False,phase6_complete=False)
    def save():atomic_json(out/'download.json',report)
    save()
    for attempt in range(1,4):
        partial=out/('download-attempt-'+str(attempt)+'.partial.zip');log=out/('download-attempt-'+str(attempt)+'.log');h=hashlib.sha256();count=0
        with partial.open('xb') as target,log.open('xb') as errors:
            child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=errors,cwd=ROOT)
            try:
                with child.stdout as stream:
                    for body in iter(lambda:stream.read(1024*1024),b''):
                        target.write(body);h.update(body);count+=len(body)
                        require(count<=pin['archive_bytes'],'Published stream exceeded exact bound; partial preserved')
            finally:
                if child.poll() is None:
                    try:child.wait(timeout=3)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                report['attempts'].append(dict(attempt=attempt,actual_pid=child.pid,actual_returncode=child.returncode,bytes=count,sha256=h.hexdigest(),log_sha256=sha(log)));save()
        if child.returncode==0:
            require(count==pin['archive_bytes'] and h.hexdigest()==pin['archive_sha256'] and sha(partial)==pin['archive_sha256'],'Actual complete published ZIP digest and size required')
            partial.rename(out/'producer.zip');report['status']='exact-published-raw-zip-verified';save();return
        message=log.read_text(errors='replace');require(attempt<3 and any('HTTP '+str(code) in message for code in (502,503,504)),'Exact artifact transport failed; original partial bytes/log/exit retained')


if __name__=='__main__':main()
