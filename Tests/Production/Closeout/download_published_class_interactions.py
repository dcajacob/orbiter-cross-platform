#!/usr/bin/env python3
"""Stream exactly one already completed original interaction artifact on its independent hosted worker."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from contracts import ROOT,PROFILES,require,sha,atomic_json
from inspect_published_class_interactions import LOCK,validate_api,load


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=PROFILES,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual separate standard hosted worker required; no local bulk download')
    lock=load(LOCK);require(a.profile in lock['profiles'] and shutil.which('gh'),'Exact completed profile and existing official GitHub CLI required')
    pin=lock['profiles'][a.profile];base=ROOT/'out/class-interaction-published'/a.profile
    require(not base.exists(),'Fresh independent published interaction download required');base.mkdir(parents=True)
    prefix='repos/dcajacob/orbiter-cross-platform/actions/'
    def api(path):return json.loads(subprocess.check_output(['gh','api',prefix+path],timeout=90))
    repository=json.loads(subprocess.check_output(['gh','api','repos/dcajacob/orbiter-cross-platform'],timeout=90))
    require(repository['private'] is False and repository['full_name']=='dcajacob/orbiter-cross-platform','Exact already-public repository required')
    run=api('runs/'+str(lock['run_id']));jobs=api('runs/'+str(lock['run_id'])+'/jobs?per_page=100');artifact=api('artifacts/'+str(pin['artifact_id']))
    require(jobs['total_count']==len(jobs['jobs'])==5,'Complete original job page required')
    record=dict(repository=lock['repository'],run=run,jobs=jobs['jobs'],artifact=artifact);atomic_json(base/'api.json',record);validate_api(record,a.profile)
    archive=base/'producer.zip';partial=base/'producer.zip.partial';log=base/'download.log';started=time.monotonic_ns()
    argv=['gh','api',prefix+'artifacts/'+str(pin['artifact_id'])+'/zip'];receipt=dict(argv=argv,source=lock['source'],
        original_run_id=lock['run_id'],original_artifact_id=pin['artifact_id'],expected_bytes=pin['archive_bytes'],
        expected_sha256=pin['archive_sha256'],streamed_to_file=True,bulk_local_transfer=False,phase6_complete=False)
    try:
        with partial.open('xb') as output,log.open('w') as errors:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=output,stderr=errors);receipt['actual_pid']=child.pid
            try:receipt['actual_returncode']=child.wait(timeout=2400)
            except subprocess.TimeoutExpired:child.kill();receipt.update(actual_returncode=child.wait(),timed_out=True);raise
        require(receipt['actual_returncode']==0,'Original interaction artifact streaming failed; partial output retained')
        receipt['actual_bytes']=partial.stat().st_size;receipt['actual_sha256']=sha(partial)
        require(receipt['actual_bytes']==pin['archive_bytes'] and receipt['actual_sha256']==pin['archive_sha256'],
                'Every streamed original artifact byte must match the published API digest before decoding')
        partial.rename(archive);receipt['status']='downloaded-exact-complete-original-interaction-profile-only'
    except BaseException as error:receipt.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:
        receipt.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));atomic_json(base/'download.json',receipt)
    print(receipt['status'])

if __name__=='__main__':main()
