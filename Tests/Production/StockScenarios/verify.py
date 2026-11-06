#!/usr/bin/env python3
"""Audit all 157 attempts without converting expected dependency failures into passes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from inventory import ROOT,corpus,digest,require
from run import inspect
from run import api_admission
import intentional_exit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','assets','modules','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--runtime-source-commit',required=True)
    p.add_argument('--runtime-owner',type=Path,default=ROOT)
    p.add_argument('--stock-exit-reference',type=Path)
    p.add_argument('--general-api-qualification',type=Path)
    p.add_argument('--diagnostic-case',action='append',help='Explicit selected audit; cannot produce full stock acceptance')
    a=p.parse_args();require(not a.output.exists(),'Stock audit output exists')
    require(re.fullmatch('[0-9a-f]{40}',a.runtime_source_commit),'Runtime source must be an immutable full commit')
    report=json.loads((a.capture/'stock-scenarios.json').read_text())
    owner=a.runtime_owner.resolve()
    require(report.get('runtime_owner',str(ROOT))==str(owner),'Actual retained runtime owner differs')
    api_reference=api_admission.reference(a.general_api_qualification)
    if 'general_api_qualification' in report:
        require(api_reference is not None and report['general_api_qualification']==dict(path=api_reference['path'],
            sha256=api_reference['sha256'],protocol=api_reference['body']['protocol'],variant='general-api-spice-test-correction-v2'),
            'Actual versioned API qualification differs')
    else:require(api_reference is None,'Cannot apply the corrected API policy retrospectively')
    current=corpus(a.assets,a.modules)
    require(report['scenario_count']==157 and set(report['cases'])==set(current['cases']), 'Stock corpus is incomplete')
    require(report['lock_sha256']==current['lock_sha256'],'Frozen source lock differs')
    requested=list(report['cases']) if a.diagnostic_case is None else a.diagnostic_case
    require(requested and len(requested)==len(set(requested)) and set(requested)<=set(report['cases']), 'Invalid stock audit selection')
    diagnostic=a.diagnostic_case is not None
    require(report.get('diagnostic_only',False) is diagnostic, 'Full/selected stock audit scope differs')
    require(report.get('cases_requested',requested)==[name for name in report['cases'] if name in requested], 'Recorded stock selection differs')
    build_path=Path(report['build_record_path'])
    build=json.loads(build_path.read_text())
    binaries=build['runtime_files_sha256']
    executable=next(owner/name for name in binaries if Path(name).name=='orbiter-production')
    renderer=next(owner/name for name in binaries if name.endswith('/NativeModules/Graphics/OGLClient.so'))
    identity=intentional_exit.build_identity(executable,renderer.parent.parent,build_path,a.runtime_source_commit,owner)
    require(identity==report['runtime_identity'],'Recomputed stock build identity differs')
    if identity['sanitizer_linked']:
        require(all(report['runtime_environment'][key]==value for key,value in dict(
            ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1').items()),'Stock sanitizer execution settings differ')
    for name,checksum in report['protected_files_sha256'].items():
        require(digest(Path(name))==checksum,'Protected stock source or runtime changed: '+name)
    if 'stock_exit_reference' in report:
        reference=intentional_exit.audit_reference(a.stock_exit_reference,a.output.with_name(a.output.stem+'-original.json'))
        require(reference['producer_commit']==report['stock_exit_reference']['producer_commit'],
                'Stock exit original producer differs')
    for source,checksum in report['source_sha256'].items():
        commit=a.runtime_source_commit if source=='Src/Orbiter/Production/NativeApplication.cpp' else report['observer_commit']
        require(re.fullmatch('[0-9a-f]{40}',commit),'Stock observer producer must be an immutable full commit')
        data=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+source])
        actual=hashlib.sha256(data).hexdigest()
        require(actual==checksum,'Stock observer or pinned runtime source differs: '+source)
    summary=dict(attempted=0,passed=0,failed=0,
        inventory_ready=sum(case['inventory_ready'] for case in current['cases'].values()),
        source_metadata_mismatches=sum(case['locked_inventory_metadata_differs'] for case in current['cases'].values()))
    failures={};runs=[]
    for name,case in report['cases'].items():
        require(all(case[key]==current['cases'][name][key] for key in
            ('sha256_lf','sha256_raw','ships','locked_inventory_metadata_differs','inventory_ready','dependency_problems')),
            'Stock identity or dependency data differs: '+name)
        if name not in requested:
            require(case['status']=='not-run' and 'output' not in case,'Unexpected attempt outside declared stock audit scope')
            continue
        require(case['status'] in ('passed','failed') and 'output' in case,'Scenario was skipped: '+name)
        require(all(case[key]==current['cases'][name][key] for key in
            ('sha256_lf','sha256_raw','ships','locked_inventory_metadata_differs','inventory_ready','dependency_problems')),
            'Stock identity or dependency data differs: '+name)
        out=a.capture/case['output']
        if report.get('execution_protocol')=='normal-stock-capture-v2':
            receipt=json.loads((out/'process-receipt.json').read_text())
            require(receipt['terminal'] is True and receipt['cancelled'] is False and
                    type(receipt['actual_collector_pid']) is int and receipt['actual_collector_pid']>0 and
                    receipt['actual_returncode']==case['returncode'],'Actual normal-stock process receipt incomplete')
        for file,checksum in case.get('files_sha256',{}).items():
            require(digest(out/file)==checksum,'Stock attempt artifact changed: '+str(out/file))
        require('returncode' in case,'Attempt did not terminate normally or report its exit: '+name)
        actual=json.loads(json.dumps(inspect(out,case,case['returncode'],name,a.stock_exit_reference,identity['profile'],api_reference)))
        require(all(case[k]==v for k,v in actual.items()),'Recomputed stock outcome differs: '+name)
        summary['attempted']+=1;summary[case['status']]+=1
        if case['status']=='failed':failures[name]=case['problems']
        runs.append(dict(scenario=name,status=case['status'],output=case['output'],
                         finalized_ticks=case['finalized_ticks'],vessels=case['declared_vessels'],
                         files_sha256=case['files_sha256']))
    require(summary==report['summary'],'Stock summary differs')
    status=('audited-selected-stock-scenarios-diagnostic-only' if not failures else 'audited-selected-incomplete') if diagnostic else ('passed' if not failures else 'audited-incomplete')
    result=dict(status=status,phase6_complete=False,diagnostic_only=diagnostic,cases_requested=requested,
                capture_sha256=digest(a.capture/'stock-scenarios.json'),source_sha256=digest(Path(__file__)),
                runtime_source_commit=a.runtime_source_commit,summary=summary,failures=failures,runs=runs)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],summary=summary)))


if __name__=='__main__':main()
