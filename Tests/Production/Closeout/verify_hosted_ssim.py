#!/usr/bin/env python3
"""Verify the existing scalar SSIM tool against unchanged Python on real full frames."""
import argparse
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import subprocess
import time
import zipfile
from contracts import ROOT,require,sha,load
from ssim_kernel import compare

SOURCE='f9bf6c7814965cd897f349f97890d9e005cbb66d'
DIGEST='097116cce0bcda507c0546c98933155cb95e423c24f1ca58a387e235ac6a408d'


def validate_api(record):
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==42515116858 and
            run['head_sha']==SOURCE and run['head_branch']=='codex/github-qualification' and
            run['path']=='.github/workflows/phase6-qualification.yml' and run['status'] in ('in_progress','completed'),
            'Exact source campaign required for arithmetic controls; no cohort qualification inferred')
    require(artifact['id']==13638968833 and artifact['name']=='matched-clock-remaining-stock-v2-Debug-sse2' and
            artifact['size_in_bytes']==458096852 and artifact['digest']=='sha256:'+DIGEST and artifact['expired'] is False and
            artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==SOURCE,
            'Exact completed original frame source artifact required')
    require(len(jobs)==1 and jobs[0]['id']==128839665625 and jobs[0]['run_id']==run['id'] and jobs[0]['head_sha']==SOURCE and
            jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and 'windows-2025' in jobs[0]['labels'],
            'Actual complete standard Windows frame producer required')


def small_pairs():
    pairs=[]
    for index,(width,height) in enumerate(((11,11),(17,13),(31,29),(32,21),(29,23))):
        left=bytes((i*(17+index)+3)%256 for i in range(width*height*4));right=bytearray(left)
        if index==1:right[:]=bytes([19])*(width*height*4)
        elif index==2:
            for p in range(0,len(right),16):right[p]^=0xff
        elif index==3:
            for p in range(3,len(right),4):right[p]^=0xff
        elif index==4:right[:]=left[4:]+left[:4]
        pairs.append((f'small-{index}',left,bytes(right),width,height))
    return pairs


def equality(label,actual,reference):
    require(math.isfinite(actual) and math.isfinite(reference) and actual.hex()==reference.hex(),
            'Scalar SSIM differs from unchanged Python binary64 result: '+label)
    return dict(name=label,actual_hex=actual.hex(),reference_hex=reference.hex())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();api=load(a.api);validate_api(api)
    require(a.archive.stat().st_size==458096852 and sha(a.archive)==DIGEST,'Actual original API archive byte identity differs')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh hosted scalar verification output required');a.output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('hosted_retained_ssim',ROOT/'Tests/Production/Client/compare_client.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    reference=reader.image_ssim;cpp=Path(__file__).with_name('ssim_kernel.cpp');wrapper=Path(__file__).with_name('ssim_kernel.py');executable=a.output/'ssim'
    guarded={str(path):sha(path) for path in (cpp,wrapper,Path(inspect.getsourcefile(reference)))}
    source_api=a.output/'original-source-api.json';source_api.write_bytes(a.api.read_bytes());guarded[str(source_api)]=sha(source_api)
    frames=[]
    with zipfile.ZipFile(a.archive) as archive:
        for n in range(1,5):
            name=f'remaining-stock-repaired/remaining_stock_{n:03d}-1/scene.rgba'
            require(archive.namelist().count(name)==1,'Unique original full-frame member required')
            body=archive.read(name);require(len(body)==1280*720*4,'Complete original 1280x720 RGBA required')
            target=a.output/f'original-{n:03d}.rgba';target.write_bytes(body);guarded[str(target)]=sha(target);frames.append(body)
    command=['c++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off',str(cpp),'-o',str(executable)]
    with (a.output/'compile.log').open('w') as stream:
        child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);pid=child.pid;code=child.wait()
    require(code==0,'Actual scalar comparator build failed');guarded[str(executable)]=sha(executable);guarded[str(a.output/'compile.log')]=sha(a.output/'compile.log')
    full=[('full-1',frames[0],frames[1],1280,720),('full-2',frames[2],frames[3],1280,720)]
    require(all(left!=right for _,left,right,_,_ in full),'Real full-frame controls must exercise nonidentical image arithmetic')
    comparisons=[]
    for label,left,right,width,height in [*small_pairs(),*full]:
        start=time.monotonic_ns();expected=reference(left,right,width,height);reference_ns=time.monotonic_ns()-start
        start=time.monotonic_ns();actual=compare(executable,left,right,width,height);actual_ns=time.monotonic_ns()-start
        row=equality(label,actual,expected);row.update(width=width,height=height,left_sha256=hashlib.sha256(left).hexdigest(),right_sha256=hashlib.sha256(right).hexdigest(),reference_elapsed_ns=reference_ns,actual_elapsed_ns=actual_ns)
        comparisons.append(row);print(label,row['actual_hex'],'equals unchanged Python',flush=True)
    require(all(sha(name)==value for name,value in guarded.items()) and sha(a.archive)==DIGEST,'Original SSIM inputs/source bytes changed')
    record=dict(status='verified-bit-identical-to-retained-python-ssim',full_frame_pairs=2,small_control_pairs=5,comparisons=comparisons,
        executable=str(executable),reference_reader_sha256=sha(inspect.getsourcefile(reference)),guarded_files_sha256=guarded,
        producer_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),verifier_sha256=sha(__file__),
        compiler_command=command,actual_compiler_pid=pid,actual_compiler_returncode=code,
        original_run_id=42515116858,original_job_id=128839665625,original_artifact_id=13638968833,original_api_archive_sha256=DIGEST,
        actual_capture_sources_and_budgets_unchanged=True,masks=False,rescaling=False,budgets_changed=False,
        scope='Arithmetic-equivalence controls only. Cross-scene full-frame pairs do not measure acceptance or hardware performance.',
        original_reference_cohort_audit_pending=True,native_admission_qualified=False,phase6_complete=False)
    (a.output/'verification.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'])


if __name__=='__main__':main()
