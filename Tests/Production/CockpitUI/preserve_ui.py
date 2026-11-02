#!/usr/bin/env python3
"""Preserve explicitly accepted original UI evidence in immutable storage."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from frozen_ui import HERE,metadata
from mesa_runtime import digest,require

def api(path):return json.loads(subprocess.check_output(['gh','api',path]))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();record=metadata()
    repo=os.environ['GH_REPO'];require(repo=='dcajacob/orbiter-cross-platform','Unapproved original control archive destination')
    run=api(f'repos/{repo}/actions/runs/{record["run_id"]}')
    require(run['conclusion']=='success' and run['head_sha']==record['source_commit'] and run['path']==record['workflow'],'Accepted original control run/source/workflow differs')
    a.output.mkdir(parents=True,exist_ok=False)
    for entry in record['artifacts'].values():
        current=api(f'repos/{repo}/actions/artifacts/{entry["id"]}')
        require(current['name']==entry['name'] and current['digest']=='sha256:'+entry['sha256'],'Accepted original control artifact differs')
        target=a.output/(entry['name']+'.zip')
        with target.open('wb') as output:subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{entry["id"]}/zip'],stdout=output,check=True)
        require(digest(target)==entry['sha256'],'Preserved original control artifact bytes differ')
    with (a.output/'workflow-logs.zip').open('wb') as output:subprocess.run(['gh','api',f'repos/{repo}/actions/runs/{record["run_id"]}/logs'],stdout=output,check=True)
    for name in ('provenance.json','comparison.json','README.md'):shutil.copy2(HERE/'Reference'/name,a.output/name)
    files={path.name:digest(path) for path in sorted(a.output.iterdir()) if path.is_file()}
    (a.output/'files.json').write_text(json.dumps(dict(schema=1,run_id=record['run_id'],files_sha256=files),indent=2)+'\n')
    print('Verified original control captures, exact producer DLL, source/build metadata and complete hosted logs for preservation')
if __name__=='__main__':main()
