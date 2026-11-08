#!/usr/bin/env python3
"""Reject damaged copies of a real corrected API run through the normal stock inspector."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production/StockScenarios'))
from inventory import digest,require
from run import inspect,api_admission


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','qualification','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh normal API admission controls output required')
    a.capture=a.capture.resolve();a.qualification=a.qualification.resolve()
    report=json.loads((a.capture/'stock-scenarios.json').read_text());name='Tests/GeneralApiTest.scn';case=report['cases'][name]
    require(case['status']=='passed' and report['diagnostic_only'] is True,'Actual passed selected normal API capture required')
    source=a.capture/case['output'];profile=report['runtime_identity']['profile'];selected=api_admission.reference(a.qualification)
    before={str(p):digest(p) for p in source.rglob('*') if p.is_file()}
    positive=inspect(source,case,0,name,None,profile,selected)
    require(positive['status']=='passed','Actual corrected normal API run rejected')
    controls=['ordinary_partial_exit','missing_qualification','wrong_scenario_hash','wrong_profile','wrong_math',
              'missing_assertion','missing_vessel','unclean_context','nonzero_exit','overwritten_save',
              'changed_private_script','incomplete_asset_manifest','missing_pid','cancelled_process']
    with tempfile.TemporaryDirectory(prefix='phase6-api-admission-real-controls-') as temp:
        for control in controls:
            out=Path(temp)/control;out.mkdir()
            for path in source.iterdir():
                if path.is_file():(out/path.name).symlink_to(path.resolve())
            def replace(name,body):
                path=out/name;path.unlink(missing_ok=True);path.write_bytes(body)
            def write(name,body):replace(name,(json.dumps(body,indent=2)+'\n').encode())
            argv=json.loads((source/'invocation.json').read_text());argv[argv.index('--save')+1]=str(out/'saved.scn');write('invocation.json',argv)
            actual_case=copy.deepcopy(case);scenario=name;reference=selected;actual_profile=profile;code=0
            if control=='ordinary_partial_exit':scenario='2024 Edition/Spotlights.scn'
            elif control=='missing_qualification':reference=None
            elif control=='wrong_scenario_hash':actual_case['sha256_lf']='0'*64
            elif control=='wrong_profile':actual_profile='Debug-other'
            elif control=='wrong_math':write('numerics.json',dict(math='wrong-mode'))
            elif control=='missing_assertion':
                text=(source/'console.log').read_text();replace('console.log',text.replace(' - passed',' - omitted',1).encode())
            elif control=='missing_vessel':replace('flight-state.csv',(source/'flight-state.csv').read_bytes().splitlines(keepends=True)[0])
            elif control=='unclean_context':write('graphics-lifecycle.json',dict(rendered_frames=0,successful_presents=0,context_deleted=False))
            elif control=='nonzero_exit':code=1
            elif control=='overwritten_save':replace('saved.scn',b'overwritten\n')
            elif control=='changed_private_script':
                original=Path(argv[argv.index('--assets')+1]);assets=out/'changed-assets'
                shutil.copytree(original,assets,copy_function=lambda source,target:Path(target).symlink_to(Path(source).resolve()))
                target=assets/'Script/Tests/GeneralApiTest.lua';target.unlink();target.write_text('oapi.exit(0)\n')
                argv[argv.index('--assets')+1]=str(assets);argv[argv.index('--scenario')+1]=str(assets/'Scenarios/Tests/GeneralApiTest.scn');write('invocation.json',argv)
                manifest=json.loads((source/'api-asset-variant.json').read_text());manifest['variant_assets']=str(assets);write('api-asset-variant.json',manifest)
            elif control=='incomplete_asset_manifest':
                manifest=json.loads((source/'api-asset-variant.json').read_text());manifest['files_sha256'].pop(next(iter(manifest['files_sha256'])));write('api-asset-variant.json',manifest)
            elif control in ('missing_pid','cancelled_process'):
                receipt=json.loads((source/'process-receipt.json').read_text());receipt['actual_collector_pid']=0 if control=='missing_pid' else receipt['actual_collector_pid'];receipt['cancelled']=control=='cancelled_process';write('process-receipt.json',receipt)
            rejected=inspect(out,actual_case,code,scenario,None,actual_profile,reference)
            require(rejected['status']=='failed','Damaged API admission evidence accepted: '+control)
    require(all(digest(Path(path))==value for path,value in before.items()),'Actual normal API capture changed during negative controls')
    result=dict(status='passed-real-normal-api-admission-controls',controls=controls,profile=profile,
                actual_positive=positive,capture_sha256=digest(a.capture/'stock-scenarios.json'),
                source_sha256=digest(Path(__file__)),unchanged_original_capture=True,normal_stock_admission_qualified=False,phase6_complete=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(str(len(controls))+' damaged real API admission controls rejected')


if __name__=='__main__':main()
