#!/usr/bin/env python3
"""Verify/stage accepted original cockpit controls without refreshing them."""
import argparse,hashlib,json,shutil,subprocess,sys,urllib.request,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent)]
from frozen import metadata as parent_metadata
from mesa_runtime import require,digest
RELEASE='https://github.com/dcajacob/orbiter-cross-platform/releases/download/production-windows-cockpit-controls-v1/'

def metadata():
    record=json.loads((HERE/'Reference/provenance.json').read_text());parent=parent_metadata(HERE.parent/'Cockpit/Reference/provenance.json')
    require(record['status']=='accepted' and record['automatic_refresh'] is False,'Original controls are not accepted')
    require(record['application_source']==parent['application_source'] and record['parent_reference_run']==parent['run_id'],'Original control runtime identity changed')
    require(record['budgets']==parent['budgets'] and record['image_ssim_minimum']==.98,'Original control budgets changed')
    require(record['frames']==60 and record['fixed_step']==.25 and record['epoch']==51982.5,'Original control clock changed')
    require(set(record['artifacts'])=={'Debug','Release','comparison'} and len(record['cases'])==5,'Incomplete original control references')
    for name,checksum in record['input_files_sha256_lf'].items():
        path=(ROOT/name).resolve();require(ROOT in path.parents,'Original control input path escaped repository')
        content=path.read_bytes().replace(b'\r\n',b'\n');require(hashlib.sha256(content).hexdigest()==checksum,'Frozen original control producer input changed: '+name)
        historical=subprocess.check_output(['git','-C',str(ROOT),'show',record['source_commit']+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(historical).hexdigest()==checksum,'Original control producer source differs: '+name)
    return record

def obtain(entry,cache,offline):
    name=entry['name']+'.zip';require(Path(name).name==name,'Invalid original control archive filename');target=cache/name
    if not target.exists():
        require(not offline,'Offline original control archive missing: '+name);cache.mkdir(parents=True,exist_ok=True);temporary=cache/(name+'.partial')
        try:
            with urllib.request.urlopen(RELEASE+name,timeout=120) as source,temporary.open('wb') as output:shutil.copyfileobj(source,output)
            require(digest(temporary)==entry['sha256'],'Downloaded original control archive differs');temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
    require(digest(target)==entry['sha256'],'Cached original control archive differs: '+name);return target

def stage(record,cache,output,offline=False):
    require(not output.exists(),'Original control output exists; replacement is forbidden')
    archives={key:obtain(value,cache,offline) for key,value in record['artifacts'].items()};output.mkdir(parents=True)
    for config in ('Debug','Release'):
        with zipfile.ZipFile(archives[config]) as archive:
            for name,checksum in record['reference_files_sha256'][config].items():
                path=(output/config/name).resolve();require((output/config).resolve() in path.parents,'Original control reference path escaped output')
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read('out/control-reference/'+name))
                require(digest(path)==checksum,'Frozen original control file differs: '+name)
    with zipfile.ZipFile(archives['comparison']) as archive:
        comparison=json.loads(archive.read('cockpit-control-comparison.json'));require(comparison['status']=='passed' and set(comparison['cases'])==set(record['cases']),'Incomplete accepted original control comparison')
    (output/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    return dict(status='passed',run_id=record['run_id'],cases=len(record['cases']))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path);p.add_argument('--output',type=Path);p.add_argument('--offline',action='store_true');a=p.parse_args();record=metadata()
    require(bool(a.cache)==bool(a.output),'--cache and --output must be provided together')
    print(json.dumps(stage(record,a.cache,a.output,a.offline) if a.cache else dict(status='passed',run_id=record['run_id'])))
if __name__=='__main__':main()
