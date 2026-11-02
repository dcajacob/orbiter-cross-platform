#!/usr/bin/env python3
"""Preserve accepted cockpit captures and their exact binaries in release storage."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from frozen import ROOT,metadata
from mesa_runtime import digest,require

def api(path):return json.loads(subprocess.check_output(['gh','api',path]))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();reference=Path(__file__).with_name('Reference');record=metadata(reference/'provenance.json')
    repo=os.environ['GH_REPO'];require(repo=='dcajacob/orbiter-cross-platform','Unapproved cockpit archive destination')
    run=api(f'repos/{repo}/actions/runs/{record["run_id"]}')
    require(run['conclusion']=='success' and run['head_sha']==record['source_commit'],'Accepted cockpit run/source differs')
    require(run['path']=='.github/workflows/production-cockpit-reference.yml','Wrong cockpit reference workflow')
    a.output.mkdir(parents=True,exist_ok=False)
    entries=list(record['artifacts'].values())+list(record['runtime_artifacts'].values())
    for entry in entries:
        name=entry['name']+'.zip';require(Path(name).name==name,'Invalid cockpit artifact filename')
        current=api(f'repos/{repo}/actions/artifacts/{entry["id"]}')
        require(current['name']==entry['name'] and current['digest']=='sha256:'+entry['sha256'],'Accepted cockpit artifact identity differs')
        target=a.output/name
        with target.open('wb') as stream:subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{entry["id"]}/zip'],stdout=stream,check=True)
        require(digest(target)==entry['sha256'],'Accepted cockpit artifact bytes differ')
    with (a.output/'workflow-logs.zip').open('wb') as stream:
        subprocess.run(['gh','api',f'repos/{repo}/actions/runs/{record["run_id"]}/logs'],stdout=stream,check=True)
    for name in ('provenance.json','README.md'):shutil.copy2(reference/name,a.output/name)
    shutil.copy2(ROOT/'OVP/OGLClient/ATTRIBUTION.md',a.output/'ATTRIBUTION.md')
    with zipfile.ZipFile(a.output/(record['artifacts']['Release']['name']+'.zip')) as archive:
        for case in ('dg_panel','dg_vc','dgs_panel','dgs_vc'):
            (a.output/(case+'.png')).write_bytes(archive.read('out/cockpit-reference/'+case+'-1/instrument-50.png'))
    files={p.name:digest(p) for p in sorted(a.output.iterdir()) if p.is_file()}
    (a.output/'files.json').write_text(json.dumps(dict(schema=1,run_id=record['run_id'],files_sha256=files),indent=2)+'\n')
    print('Verified original Windows cockpit artifacts, exact application/client/driver binaries and logs for immutable release archival')
if __name__=='__main__':main()
