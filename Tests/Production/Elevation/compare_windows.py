#!/usr/bin/env python3
"""Compare both original Windows terrain configurations before extraction."""
import argparse
import hashlib
import json
from pathlib import Path
from capture import compare,protocol,require

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug',type=Path,required=True)
    parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();lock=protocol();reports=[]
    for directory,configuration in [(args.debug,'Debug'),(args.release,'Release')]:
        report=json.loads((directory/'capture.json').read_text())
        require(report['status']=='passed' and report['configuration']==configuration and
            report['runtime_source']==lock['runtime_source'],'invalid original terrain capture')
        reports.append(report)
        for mode in (1,2):require((directory/f'mode-{mode}-trace-1.csv').read_bytes()==
            (directory/f'mode-{mode}-trace-2.csv').read_bytes(),'original Windows terrain repeat differs')
    require(reports[0]['source']==reports[1]['source'] and reports[0]['protocol_sha256_lf']==reports[1]['protocol_sha256_lf'],
        'different observer/protocol sources')
    results={str(mode):compare((args.debug/f'mode-{mode}-trace-1.csv').read_bytes(),
        (args.release/f'mode-{mode}-trace-1.csv').read_bytes()) for mode in (1,2)}
    args.report.write_text(json.dumps(dict(status='passed',source=reports[0]['source'],
        runtime_source=lock['runtime_source'],protocol_sha256_lf=reports[0]['protocol_sha256_lf'],
        results=results),indent=2)+'\n')
    print('Original Windows Debug/Release terrain observations pass predeclared budgets')

if __name__=='__main__':main()
