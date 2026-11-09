#!/usr/bin/env python3
"""Inspect the actual rejected source inventories without changing any original capture."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from contracts import ROOT,require,sha,load

SOURCE='f9bf6c7814965cd897f349f97890d9e005cbb66d'
PREFIX='Tests/Production/RemainingStockPersistence/'


def main():
    base=ROOT/'out/original-source-inventory';api=load(base/'api.json');run=api['run'];jobs=api['jobs']
    require(run['id']==42515116858 and run['head_sha']==SOURCE and run['status']=='completed' and run['conclusion']=='failure' and
            len(jobs)==4 and all(j['head_sha']==SOURCE and j['status']=='completed' and j['conclusion']=='success' and 'windows-2025' in j['labels'] for j in jobs),
            'Exact rejected original cohort with four completed stock jobs required')
    tracked=set(subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',SOURCE,'--',PREFIX],text=True).splitlines())
    nested={name for name in tracked if '/' in name[len(PREFIX):]}
    require(len(nested)==5 and all(name.startswith(PREFIX+'LocalVM/') for name in nested),'Exact original recursive inventory requirement changed')
    result=dict(status='inspected-original-source-inventory-gap-only',original_capture_source=SOURCE,original_run_id=42515116858,
        original_captures_modified=False,missing_hashes_manufactured=False,source_guard_weakened=False,
        simulation_executed=False,old_reload_qualification_granted=False,phase6_complete=False,profiles={})
    for artifact in api['artifacts']:
        profile=artifact['name'].removeprefix('matched-clock-remaining-stock-v2-');archive=base/(artifact['name']+'.zip')
        require(archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],
                'Actual original source inventory ZIP differs from its API bytes')
        with zipfile.ZipFile(archive) as source:
            raw=source.read('remaining-stock-persistence/capture.json');report=json.loads(raw)
        require(report['producer_commit']==SOURCE and report['configuration']+'-'+report['math_profile']==profile and
                report['status']=='captured-awaiting-independent-persistence-audit' and not report['failures'],
                'Actual complete original reload source inventory required')
        hashes=report['source_raw_sha256'];missing=tracked-set(hashes)
        require(missing==nested,'Original source inventory gap differs from the exact five nested transport files')
        for name,value in hashes.items():
            require('..' not in Path(name).parts and not Path(name).is_absolute(),'Unsafe captured source path')
            raw_source=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+name]).replace(b'\r\n',b'\n')
            require(value in {hashlib.sha256(raw_source).hexdigest(),hashlib.sha256(raw_source.replace(b'\n',b'\r\n')).hexdigest()},
                    'An actually recorded original source hash differs from its immutable owning source')
        result['profiles'][profile]=dict(capture_sha256=hashlib.sha256(raw).hexdigest(),recorded_sources=len(hashes),
            required_recursive_sources=len(tracked),missing_recorded_source_paths=sorted(missing),original_archive_sha256=artifact['digest'],
            existing_recorded_source_hashes_verified=True,recollection_required=True)
        print(profile+' actual rejected inventory: '+json.dumps(result['profiles'][profile]),flush=True)
    require(set(result['profiles'])=={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')},'All four actual original source inventories required')
    audit=load(base/'audit-api.json');archive=base/'failed-audit.zip'
    require(audit['run']['id']==42542101820 and audit['run']['head_sha']=='9af22bbd320b54025e9345f6bfbd05260d2287e8' and
            audit['run']['status']=='completed' and audit['run']['conclusion']=='failure' and
            audit['artifact']['id']==13641389794 and archive.stat().st_size==1037728 and
            sha(archive)=='3c32b79bd721a020de1a4594224a0769e8685ca5b20e019f76e46cf4dc9428da',
            'Actual preserved failed independent audit artifact required')
    with zipfile.ZipFile(archive) as source:
        writer=json.loads(source.read('original-stock-audit/independent/writer-audit.json'))
        cohort=json.loads(source.read('original-stock-audit/independent/original-persistence-audit.json'))
    require(writer['status']=='passed' and writer['producer_commit']==SOURCE and writer['processes']==304 and writer['presentations']==304*960 and
            cohort['status']=='failed' and cohort['error']=='Complete immutable Windows persistence observer closure missing',
            'Preserved original writer success and reload provenance failure must remain explicit')
    result['previous_writer_audit']=dict(status='passed-original-writers-only',processes=304,independent_audit_run_id=42542101820)
    result['previous_reload_audit']=dict(status='rejected-incomplete-source-inventory',error=cohort['error'])
    (base/'inventory-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
