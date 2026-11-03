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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','assets','modules','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--runtime-source-commit',required=True)
    a=p.parse_args();require(not a.output.exists(),'Stock audit output exists')
    require(re.fullmatch('[0-9a-f]{40}',a.runtime_source_commit),'Runtime source must be an immutable full commit')
    report=json.loads((a.capture/'stock-scenarios.json').read_text())
    current=corpus(a.assets,a.modules)
    require(report['scenario_count']==157 and set(report['cases'])==set(current['cases']), 'Stock corpus is incomplete')
    require(report['lock_sha256']==current['lock_sha256'],'Frozen source lock differs')
    for source,checksum in report['source_sha256'].items():
        if source=='Src/Orbiter/Production/NativeApplication.cpp':
            data=subprocess.check_output(['git','-C',str(ROOT),'show',a.runtime_source_commit+':'+source])
            actual=hashlib.sha256(data).hexdigest()
        else:actual=digest(ROOT/source)
        require(actual==checksum,'Stock observer or pinned runtime source differs: '+source)
    summary=dict(attempted=0,passed=0,failed=0,inventory_ready=0,source_metadata_mismatches=0)
    failures={};runs=[]
    for name,case in report['cases'].items():
        require(case['status'] in ('passed','failed') and 'output' in case,'Scenario was skipped: '+name)
        require(all(case[key]==current['cases'][name][key] for key in
            ('sha256_lf','sha256_raw','ships','locked_inventory_metadata_differs','inventory_ready','dependency_problems')),
            'Stock identity or dependency data differs: '+name)
        out=a.capture/case['output']
        for file,checksum in case.get('files_sha256',{}).items():
            require(digest(out/file)==checksum,'Stock attempt artifact changed: '+str(out/file))
        require('returncode' in case,'Attempt did not terminate normally or report its exit: '+name)
        actual=json.loads(json.dumps(inspect(out,case,case['returncode'])))
        require(all(case[k]==v for k,v in actual.items()),'Recomputed stock outcome differs: '+name)
        summary['attempted']+=1;summary[case['status']]+=1
        summary['inventory_ready']+=case['inventory_ready']
        summary['source_metadata_mismatches']+=case['locked_inventory_metadata_differs']
        if case['status']=='failed':failures[name]=case['problems']
        runs.append(dict(scenario=name,status=case['status'],output=case['output'],
                         finalized_ticks=case['finalized_ticks'],vessels=case['declared_vessels'],
                         files_sha256=case['files_sha256']))
    require(summary==report['summary'],'Stock summary differs')
    result=dict(status='passed' if not failures else 'audited-incomplete',phase6_complete=False,
                capture_sha256=digest(a.capture/'stock-scenarios.json'),source_sha256=digest(Path(__file__)),
                runtime_source_commit=a.runtime_source_commit,summary=summary,failures=failures,runs=runs)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],summary=summary)))


if __name__=='__main__':main()
