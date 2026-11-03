#!/usr/bin/env python3
"""Check the actual HUD heading-tape method with unsuppressed ASan/UBSan/LSan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

HERE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=HERE.parents[2]/'Src/Orbiter/hud.cpp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=args.source.read_text();start=source.index('void HUD::AddMesh_HeadingTape (')
    method=source[start:source.index('void HUD::AddMesh_AzimuthTape (',start)]
    harness=(HERE/'HeadingTape.Test.cpp').read_text()
    generated=out/'heading.cpp';generated.write_text(harness.replace('// HUD_METHOD',method))
    report=dict(status='building',production_method_sha256=hashlib.sha256(method.encode()).hexdigest(),
                fixture_sha256=hashlib.sha256(harness.encode()).hexdigest())
    try:
        executable=out/'heading-test'
        command=[*shlex.split(os.environ.get('CXX','c++')),'-std=c++17','-g','-O0',
                 '-fsanitize=address,undefined','-fsanitize-address-use-after-scope','-fno-omit-frame-pointer',
                 str(generated),'-o',str(executable)]
        report['command']=command
        with (out/'build.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                 UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        result=subprocess.run([str(executable)],env=env,capture_output=True,text=True,timeout=30)
        (out/'run.log').write_text(result.stdout+result.stderr)
        report.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode)
        print(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('HUD heading-tape test failed')
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
