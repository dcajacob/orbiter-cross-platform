#!/usr/bin/env python3
"""Preserve explicitly accepted client artifacts in immutable release storage."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile

from mesa_runtime import digest,require

ROOT=Path(__file__).resolve().parent


def api(path):
    return json.loads(subprocess.check_output(['gh','api',path]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    reference=ROOT/'ClientReference/provenance.json'
    metadata=json.loads(reference.read_text())
    require(metadata['status']=='accepted' and metadata['automatic_refresh'] is False,'client evidence is not accepted')
    repo=os.environ['GH_REPO'];require(repo=='dcajacob/orbiter-cross-platform','unapproved release destination')
    run=api(f'repos/{repo}/actions/runs/{metadata["run_id"]}')
    require(run['conclusion']=='success' and run['head_sha']==metadata['source_commit'],'accepted client workflow/source differs')
    require(run['path']=='.github/workflows/production-client.yml','wrong accepted workflow')
    args.output.mkdir(parents=True,exist_ok=False)
    files={}
    for entry in metadata['artifacts'].values():
        name=entry['name']+'.zip';require(Path(name).name==name,'invalid artifact filename')
        current=api(f'repos/{repo}/actions/artifacts/{entry["id"]}')
        require(current['name']==entry['name'] and current['digest']=='sha256:'+entry['sha256'],'accepted artifact identity differs')
        destination=args.output/name
        with destination.open('wb') as output:
            subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{entry["id"]}/zip'],stdout=output,check=True)
        require(digest(destination)==entry['sha256'],'original client artifact ZIP digest differs')
        # Retain representative captures separately for easy inspection too.
        if entry['name']=='real-client-Release':
            with zipfile.ZipFile(destination) as archive:
                image=archive.read('out/client-execution/scene/scene.png')
                (args.output/'scene.png').write_bytes(image)
    with (args.output/'workflow-logs.zip').open('wb') as output:
        subprocess.run(['gh','api',f'repos/{repo}/actions/runs/{metadata["run_id"]}/logs'],stdout=output,check=True)
    (args.output/'provenance.json').write_bytes(reference.read_bytes())
    (args.output/'README.md').write_bytes((ROOT/'ClientReference/README.md').read_bytes())
    (args.output/'ATTRIBUTION.md').write_bytes((ROOT.parent.parent/'OVP/OGLClient/ATTRIBUTION.md').read_bytes())
    for p in sorted(args.output.iterdir()):
        if p.is_file():files[p.name]=digest(p)
    (args.output/'files.json').write_text(json.dumps(dict(schema=1,run_id=metadata['run_id'],files_sha256=files),indent=2)+'\n')
    print('Verified and preserved original hosted client ZIPs, captures, source provenance and logs')


if __name__=='__main__':main()
