#!/usr/bin/env python3
"""Re-use a pinned existing CRT probe for a new explicit primitive-only corpus."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from capture import input_values,parse


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executable',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if sys.platform!='win32' or a.output.exists():raise ValueError('Windows and fresh primitive output required')
    inputs=input_values(a.inputs);body='\n'.join(inputs)+'\n';a.output.mkdir()
    report=dict(status='running',probe_sha256=sha(a.executable),inputs_sha256=sha(a.inputs),captures={},
                scope='Explicit elementary-math diagnostic only; no simulator acceptance',phase6_complete=False)
    def save():(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for profile in ('default','sse2'):
            repeats=[]
            for repeat in (1,2):
                argv=[str(a.executable),profile]
                process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                stdout,stderr=process.communicate(body,timeout=60)
                (a.output/(profile+'-'+str(repeat)+'.txt')).write_text(stdout)
                if process.returncode!=0 or stderr:raise ValueError('Actual CRT probe failed: '+stderr)
                metadata,rows=parse(stdout,inputs,profile,a.configuration,False);repeats.append((metadata,rows))
                report['captures'][profile+'-'+str(repeat)]=dict(actual_pid=process.pid,returncode=process.returncode,metadata=metadata,samples=len(rows),output_sha256=sha(a.output/(profile+'-'+str(repeat)+'.txt')))
            if repeats[0]!=repeats[1]:raise ValueError('Repeated primitive result differs')
            save()
        if sha(a.executable)!=report['probe_sha256'] or sha(a.inputs)!=report['inputs_sha256']:raise ValueError('Probe/corpus changed')
        report['status']='observed-pinned-existing-probe'
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
