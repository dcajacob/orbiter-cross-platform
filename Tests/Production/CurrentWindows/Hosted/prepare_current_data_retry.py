"""Retry only the observed HTTP504 while running the exact original data helper.

Every invocation, stdout, failed partial download and final status is retained.
Original URLs, locks, byte counts, digests and all input checks remain untouched.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha
from restore_sdk import PRODUCER


def run_preparation(argv,output,protected,partial=None,run=subprocess.run,sleep=time.sleep):
    output=Path(output);require(not output.exists(),'Fresh immutable transport attempt directory required');output.mkdir(parents=True)
    result=dict(protocol='phase6-original-data-helper-HTTP504-retry-v1',argv=list(map(str,argv)),status='running',attempts=[],
        original_helper_and_locks_unchanged=True,pinned_URLs_versions_and_checks_unchanged=True,qualification_granted=False)
    def save():(output/'transport.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for number in range(1,4):
            require(all(sha(p)==v for p,v in protected.items()),'Original data helper or input lock changed')
            started=datetime.datetime.now(datetime.timezone.utc).isoformat()
            completed=run(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            text=completed.stdout;log=output/('attempt-'+str(number)+'.log');log.write_text(text)
            retryable=completed.returncode!=0 and 'urllib.error.HTTPError: HTTP Error 504: Gateway Time-out' in text and 'prepare_hosted_data.py' in text
            item=dict(attempt=number,started_utc=started,returncode=completed.returncode,stdout=str(log),stdout_sha256=sha(log),observed_original_HTTP504=retryable)
            if completed.returncode and partial is not None and Path(partial).is_file():
                source=Path(partial);destination=output/('attempt-'+str(number)+'.partial');shutil.copy2(source,destination)
                require(sha(source)==sha(destination),'Failed partial transport bytes changed while preserving')
                item['failed_partial']=dict(original_path=str(source),preserved_path=str(destination),bytes=source.stat().st_size,sha256=sha(destination))
            result['attempts'].append(item);save()
            require(all(sha(p)==v for p,v in protected.items()),'Original data helper or lock changed while preparing inputs')
            if completed.returncode==0:
                result['status']='passed-original-immutable-data-helper-only';save();print(text,flush=True);return result
            print(text[-8000:],flush=True)
            require(retryable and number<3,'Original data preparation failed; every attempt retained, no input or acceptance substitution')
            sleep(10)
        raise ValueError('Unreachable transport retry state')
    except BaseException as error:
        try:result['original_helper_and_locks_unchanged']=all(sha(p)==v for p,v in protected.items())
        except OSError:result['original_helper_and_locks_unchanged']=False
        result.update(status='failed-original-data-preparation-unqualified',error=str(error));save();raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cell',required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('ImageOS') in {'win25','win25-vs2026'},
            'Actual standard GitHub Windows input preparation required')
    require(a.cell in {c+'-'+m+'-'+phase for c in ('Debug','Release') for m in ('automatic','sse2') for phase in ('stock','reload')},
            'Exact full current input preparation cell required')
    owner=ROOT/'application-source';require(subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],text=True).strip()==PRODUCER,
            'Exact unchanged original input helper source required')
    protected={}
    for name in ('prepare_hosted_data.py','mesa_runtime.py','stock-data.lock.json','stock-data-container-v2.lock.json','standard-planets.lock.json'):
        relative='Tests/Production/'+name;path=owner/relative
        raw=path.read_bytes();expected=subprocess.check_output(['git','-C',str(owner),'show',PRODUCER+':'+relative])
        require(raw.replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n'),'Original helper/input lock differs from the frozen source')
        protected[str(path)]=sha(path)
    helper=owner/'Tests/Production/prepare_hosted_data.py';py=[sys.executable,'-B',str(helper)]
    tasks=[('stock',py+['--archive','out/current-data-cache/Orbiter-x64.zip','--destination','out/current-stock-data'],ROOT/'out/current-data-cache/Orbiter-x64.partial'),
           ('planets',py+['--lock','application-source/Tests/Production/standard-planets.lock.json','--archive','out/current-planet-cache/Orbiter2016.zip','--destination','out/current-stock-planets'],ROOT/'out/current-planet-cache/Orbiter2016.partial')]
    for label,argv,partial in tasks:run_preparation(argv,ROOT/'out/current-data-transport'/a.cell/label,protected,partial)


if __name__=='__main__':main()
