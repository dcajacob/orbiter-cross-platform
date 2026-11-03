#!/usr/bin/env python3
"""Verify, stage or preserve explicitly accepted additional Windows captures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE/'Cockpit'),str(HERE)]
from frozen import metadata as cockpit_metadata
from mesa_runtime import digest,require

SUITES={
    'ui-timing':('CockpitUITiming','production-windows-cockpit-ui-timing-v1'),
    'lua':('LuaRuntime','production-windows-lua-aap-v1'),
}
REPOSITORY='dcajacob/orbiter-cross-platform'


def metadata(suite):
    directory=HERE/SUITES[suite][0]
    record=json.loads((directory/'Reference/provenance.json').read_text())
    parent=cockpit_metadata(HERE/'Cockpit/Reference/provenance.json')
    require(record['status']=='accepted' and record['automatic_refresh'] is False,'Reference is not accepted')
    for key in ('application_source','frames','fixed_step','budgets','image_ssim_minimum'):
        require(record[key]==parent[key],'Original reference contract changed: '+key)
    require(record['epoch']==json.loads((HERE/'Cockpit/cases.json').read_text())['epoch'],'Original reference epoch differs')
    require(record['parent_reference_run']==parent['run_id'],'Parent runtime identity differs')
    require(set(record['artifacts'])=={'Debug','Release','comparison'},'Incomplete original artifacts')
    cases=json.loads((directory/'cases.json').read_text())['cases']
    require(record['cases']==[case['id'] for case in cases],'Original case identities changed')
    workflow=subprocess.check_output(['git','-C',str(ROOT),'show',record['source_commit']+':'+record['workflow']])
    require(hashlib.sha256(workflow.replace(b'\r\n',b'\n')).hexdigest()==record['workflow_sha256_lf'],'Original capture workflow differs')
    for name,checksum in record['input_files_sha256_lf'].items():
        path=(ROOT/name).resolve()
        require(ROOT in path.parents,'Original input path escaped repository')
        current=path.read_bytes().replace(b'\r\n',b'\n')
        original=subprocess.check_output(['git','-C',str(ROOT),'show',record['source_commit']+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(current).hexdigest()==checksum and original==current,'Original producer input differs: '+name)
    if suite=='lua':
        require(record['qualified_host']=='windows-2025' and record['workflow_conclusion']=='failure',
                'Lua reference qualification host/run scope changed')
        require(set(record['diagnostic_files_sha256'])=={'Debug','Release'},'Missing original SSE2 captures')
        for name in ('comparison.json','diagnostic-sse2-comparison.json'):
            comparison=json.loads((directory/'Reference'/name).read_text())
            profile='original-default' if name=='comparison.json' else 'diagnostic-sse2'
            require(comparison['status']=='passed' and comparison['exact_lua_execution'] and
                    comparison['math_profile']==profile and set(comparison['cases'])==set(record['cases']),
                    'Incomplete original Lua comparison: '+name)
        for build in ('Debug','Release'):
            for profile,enabled in (('control-reference','1'),('diagnostic-sse2','0')):
                require(record['runtime_profiles'][build][profile]['asin_runtime']['fma3_enabled']==enabled,
                        'Original Lua CPU profile identity differs')
    return record


def verify_lua_run(record,run,jobs):
    """Qualify the pinned 2025 pair while retaining the 2022 failed comparison."""
    require(run['status']=='completed' and run['conclusion']==record['workflow_conclusion'],
            'Original Lua matrix qualification outcome differs')
    expected={
        'Original Lua and AAP Debug and Release on windows-2025':'success',
        'Original Lua and AAP Debug and Release on windows-2022':'success',
        'Original Lua and AAP Debug/Release parity on windows-2025':'success',
        'Original Lua and AAP Debug/Release parity on windows-2022':'failure',
    }
    declared=record['qualified_jobs']
    require({item['name']:item['conclusion'] for item in declared}==expected and len(declared)==4,
            'Original Lua qualification requires both complete captures and the selected host comparison')
    actual={item['id']:item for item in jobs}
    require(set(actual)=={item['id'] for item in declared},'Original Lua matrix job identities differ')
    for item in declared:
        job=actual[item['id']]
        require(job['name']==item['name'] and job['status']=='completed' and job['conclusion']==item['conclusion'],
                'Original Lua qualification job differs: '+item['name'])
        if item['conclusion']=='failure':
            require([step['name'] for step in job['steps'] if step['conclusion']=='failure']==
                    ['Apply the unchanged default-profile reference gate'],
                    'Legacy Lua failure exceeded its declared default-profile comparison')


def obtain(entry,cache,tag,offline):
    name=entry['name']+'.zip'
    require(Path(name).name==name,'Invalid reference archive name')
    cache.mkdir(parents=True,exist_ok=True);target=cache/name
    if not target.exists():
        require(not offline,'Offline reference archive missing: '+name)
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            partial=Path(temporary)/name
            with urllib.request.urlopen(f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}',timeout=120) as source,partial.open('wb') as stream:
                shutil.copyfileobj(source,stream)
            require(digest(partial)==entry['sha256'],'Downloaded reference archive differs: '+name)
            partial.replace(target)
    require(target.stat().st_size==entry['size_bytes'] and digest(target)==entry['sha256'],'Cached reference archive differs: '+name)
    return target


def stage(suite,record,cache,output,offline):
    require(not output.exists(),'Reference output exists; replacement is forbidden')
    archives={key:obtain(entry,cache,SUITES[suite][1],offline) for key,entry in record['artifacts'].items()}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        staged=Path(temporary)/'reference';staged.mkdir()
        for build in ('Debug','Release'):
            with zipfile.ZipFile(archives[build]) as archive:
                prefix='out/control-reference/'
                members=[item.filename[len(prefix):] for item in archive.infolist() if item.filename.startswith(prefix) and not item.is_dir()]
                require(len(members)==len(set(members)) and set(members)==set(record['reference_files_sha256'][build]),'Reference member inventory differs')
                for name,checksum in record['reference_files_sha256'][build].items():
                    target=(staged/build/name).resolve()
                    require((staged/build).resolve() in target.parents,'Invalid reference member path')
                    data=archive.read('out/control-reference/'+name)
                    require(hashlib.sha256(data).hexdigest()==checksum,'Original capture differs: '+name)
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                if suite=='lua':
                    prefix='out/diagnostic-sse2/'
                    files=record['diagnostic_files_sha256'][build]
                    members=[item.filename[len(prefix):] for item in archive.infolist() if item.filename.startswith(prefix) and not item.is_dir()]
                    require(len(members)==len(set(members)) and set(members)==set(files),'Original SSE2 member inventory differs')
                    destination=(staged/'diagnostic-sse2'/build).resolve()
                    for name,checksum in files.items():
                        target=(destination/name).resolve();require(destination in target.parents,'Invalid original SSE2 member path')
                        data=archive.read(prefix+name)
                        require(hashlib.sha256(data).hexdigest()==checksum,'Original SSE2 capture differs: '+name)
                        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        with zipfile.ZipFile(archives['comparison']) as archive:
            comparison=json.loads(archive.read('cockpit-control-comparison.json'))
            require(comparison==json.loads((HERE/SUITES[suite][0]/'Reference/comparison.json').read_text()),'Original comparison report differs')
            require(comparison['status']=='passed' and set(comparison['cases'])==set(record['cases']),'Incomplete original comparison')
            if suite=='lua':
                comparison=json.loads(archive.read('diagnostic-sse2-comparison.json'))
                require(comparison==json.loads((HERE/'LuaRuntime/Reference/diagnostic-sse2-comparison.json').read_text()),
                        'Original SSE2 comparison report differs')
        if suite=='lua':
            for prefix,label in ((staged,'default'),(staged/'diagnostic-sse2','sse2')):
                result=staged/('verified-'+label+'-comparison.json')
                subprocess.run([sys.executable,'-B',str(HERE/'LuaRuntime/compare_lua.py'),
                    '--debug',str(prefix/'Debug'),'--release',str(prefix/'Release'),'--output',str(result)],
                    check=True,stdout=subprocess.DEVNULL)
        (staged/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
        staged.rename(output)


def preserve(suite,record,output):
    require(os.environ.get('GH_REPO')==REPOSITORY,'Unapproved reference storage destination')
    def api(path):
        return json.loads(subprocess.check_output(['gh','api',f'repos/{REPOSITORY}/{path}']))
    run=api('actions/runs/'+str(record['run_id']))
    require(run['head_sha']==record['source_commit'] and run['path']==record['workflow'],'Original capture run identity differs')
    if suite=='lua':verify_lua_run(record,run,api('actions/runs/'+str(record['run_id'])+'/jobs?per_page=100')['jobs'])
    else:require(run['conclusion']=='success','Original capture run did not pass')
    artifacts=api('actions/runs/'+str(record['run_id'])+'/artifacts?per_page=100')['artifacts']
    output.mkdir(parents=True,exist_ok=False)
    entries=list(record['artifacts'].values())+(record.get('diagnostic_artifacts',[]) if suite=='lua' else [])
    for entry in entries:
        artifact=next((item for item in artifacts if item['id']==entry['id']),None)
        require(artifact and artifact['name']==entry['name'] and artifact['digest']=='sha256:'+entry['sha256'] and artifact['size_in_bytes']==entry['size_bytes'],'Original capture artifact differs')
        name=entry['name']+'.zip';require(Path(name).name==name,'Invalid reference archive name')
        target=output/name
        with target.open('wb') as stream:
            subprocess.run(['gh','api',f'repos/{REPOSITORY}/actions/artifacts/{entry["id"]}/zip'],stdout=stream,check=True)
        require(digest(target)==entry['sha256'],'Original archive bytes differ')
    with (output/'workflow-logs.zip').open('wb') as stream:
        subprocess.run(['gh','api',f'repos/{REPOSITORY}/actions/runs/{record["run_id"]}/logs'],stdout=stream,check=True)
    for name in ('README.md','provenance.json','comparison.json'):
        shutil.copy2(HERE/SUITES[suite][0]/'Reference'/name,output/name)
    if suite=='lua':
        shutil.copy2(HERE/'LuaRuntime/Reference/diagnostic-sse2-comparison.json',output/'diagnostic-sse2-comparison.json')
        stage(suite,record,output,output.parent/(output.name+'-verified'),True)
    hashes={p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output/'files.json').write_text(json.dumps(dict(run_id=record['run_id'],files_sha256=hashes),indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite',choices=SUITES)
    parser.add_argument('--cache',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--offline',action='store_true');parser.add_argument('--preserve',type=Path)
    args=parser.parse_args();record=metadata(args.suite)
    require(bool(args.cache)==bool(args.output),'Supply both cache and output for staging')
    require(not args.preserve or not args.cache,'Choose preservation or staging')
    if args.preserve:preserve(args.suite,record,args.preserve)
    elif args.cache:stage(args.suite,record,args.cache,args.output,args.offline)
    print(json.dumps(dict(status='passed',run_id=record['run_id'],suite=args.suite)))

if __name__=='__main__':main()
