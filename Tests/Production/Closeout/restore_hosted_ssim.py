#!/usr/bin/env python3
"""Restore the exact verified scalar arithmetic artifact; no image budget is changed."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from contracts import ROOT,require,sha,load
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
from restore_sdk import unpack
from ssim_kernel import bind

SOURCE='6f7fe42c71e30ddb4f3fa80425c3779ef1ba82ea'
RUN=42537676857
DIGEST='7812112f08d08dfb1d4540e644a54613b516fc4af6f9be8dd7384e19bc190185'


def validate_api(record):
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==RUN and run['head_sha']==SOURCE and
            run['head_branch']=='qualification/hosted-ssim-controls' and run['path']=='.github/workflows/phase6-hosted-ssim-controls.yml' and
            run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','Exact successful scalar control producer required')
    require(artifact['id']==13639682979 and artifact['name']=='hosted-bit-identical-scalar-ssim-controls' and artifact['expired'] is False and
            artifact['size_in_bytes']==3935729 and artifact['digest']=='sha256:'+DIGEST and artifact['workflow_run']['id']==RUN and
            artifact['workflow_run']['head_sha']==SOURCE,'Exact closed scalar verification API artifact required')
    require(len(jobs)==1 and jobs[0]['id']==128905495973 and jobs[0]['run_id']==RUN and jobs[0]['head_sha']==SOURCE and
            jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and 'ubuntu-24.04' in jobs[0]['labels'],
            'Actual successful standard-runner scalar control job required')
    for name in ('Prove exact original scalar arithmetic on five controls and two real nonidentical full-frame pairs','Run actions/upload-artifact@v7'):
        steps=[s for s in jobs[0]['steps'] if s['name']==name]
        require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','Actual scalar verification step differs: '+name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and sys.platform=='linux','Hosted Linux scalar restoration only')
    api=load(a.api);validate_api(api);require(a.archive.stat().st_size==3935729 and sha(a.archive)==DIGEST,'Actual scalar API ZIP differs')
    base=ROOT/'out/hosted-ssim-restoration';target=ROOT/'out/hosted-ssim-controls'
    require(not base.exists() and not target.exists(),'Fresh scalar source and runtime destinations required');base.mkdir(parents=True)
    source=base/'source-artifact';outer=unpack(a.archive,source);shutil.copytree(source/'hosted-ssim-controls',target)
    record=load(target/'verification.json');executable=target/'ssim';require(Path(record['executable'])==executable,'Original scalar executable path must be retained')
    expected={str(ROOT/name) for name in ('Tests/Production/Closeout/ssim_kernel.cpp','Tests/Production/Closeout/ssim_kernel.py','Tests/Production/Client/compare_client.py')}
    expected|={str(target/name) for name in ('ssim','compile.log','original-source-api.json','original-001.rgba','original-002.rgba','original-003.rgba','original-004.rgba')}
    require(set(record['guarded_files_sha256'])==expected and record['producer_source']==SOURCE and
            record['masks'] is False and record['rescaling'] is False and record['budgets_changed'] is False and
            record['actual_capture_sources_and_budgets_unchanged'] is True and record['phase6_complete'] is False and
            record['native_admission_qualified'] is False,'Closed unchanged scalar source/input closure required')
    require(len(record['comparisons'])==7 and {v['name'] for v in record['comparisons']}=={*(f'small-{n}' for n in range(5)),'full-1','full-2'} and
            all(v['width']==1280 and v['height']==720 and v['left_sha256']!=v['right_sha256'] for v in record['comparisons'] if v['name'].startswith('full-')),
            'Both complete nonidentical frames and all five original arithmetic controls required')
    require(sha(executable)==record['guarded_files_sha256'][str(executable)],'Verified scalar binary changed');executable.chmod(0o755)
    spec=importlib.util.spec_from_file_location('restored_retained_ssim_reference',ROOT/'Tests/Production/Client/compare_client.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    _,binding=bind(target/'verification.json',sha(target/'verification.json'),reader.image_ssim)
    require(all(sha(source/name)==value for name,value in outer.items()),'Original scalar verification source archive members changed')
    receipt=dict(protocol='phase6-hosted-verified-scalar-restoration-v1',status='restored-verified-scalar-arithmetic-controls-only',
        original_producer_source=SOURCE,original_run_id=RUN,original_artifact_id=13639682979,original_api_archive_sha256=DIGEST,
        restorer_source=os.environ['GITHUB_SHA'],source_api_sha256=sha(a.api),binding=binding,phase6_complete=False,
        native_admission_qualified=False,budgets_changed=False,masks=False,rescaling=False)
    (base/'restoration.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])


if __name__=='__main__':main()
