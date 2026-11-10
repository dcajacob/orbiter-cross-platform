#!/usr/bin/env python3
"""Replay every preserved original primitive operand with the old and corrected native bindings."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
from processes import OwnedProcess

OLD='c0d03b1b2122f650c72f372d267b0c9f2aac314a'
FIXED='ccc02c8a34bd1f227624d8778a141e8736ae8111'
MATH='Src/Orbiter/Production/Math'
VENDOR='Extern/ReferenceMath'
CORPUS=ROOT/'Tests/Production/Closeout/NumericalRecovery/ObservedOperands'
OLD_ARCHIVE_SHA='4e71021daa0040d3cbc95cb68e707c134ebccf4e4dbe17c4e8a6bbf481a6fd1b'
SAN='-fsanitize=address,undefined -fno-omit-frame-pointer'
ORDER=('arcsine','touchdown','surface')


def source(commit,name):return subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)


def operands(manifest):
    require(manifest['protocol']=='phase6-exact-original-observed-numerical-operand-renewal-v1' and manifest['automatic_refresh'] is False and manifest['original_saved_input_sha256']=='afc91115951ec44a81cffb6ffa34c00191f9b005aac3f14cf94b21de171b0538' and manifest['source_original_surface_observer']==OLD and set(manifest['corpora'])==set(ORDER),'Complete original exact saved-input primitive cohorts required')
    for group,count in zip(ORDER,(2145,74115,8748),strict=True):
        record=manifest['corpora'][group];path=CORPUS/(group+'-operands.bin.gz');require(sha(path)==record['packed_sha256'] and record['samples']==count,'Complete original sealed primitive packet required')
        raw=gzip.decompress(path.read_bytes());require(hashlib.sha256(raw).hexdigest()==record['operand_bytes_sha256'],'Actual full original operand bytes differ')
        if group=='arcsine':
            require(len(raw)==2145*8,'All2145 original arcsine inputs required')
            for index in range(2145):yield group,(str(index),'asin',raw[index*8:index*8+8].hex(),'')
            continue
        surface=group=='surface';stride=6 if surface else 61;width=5 if surface else 4
        roster=record['roster'];require(record['first_tick']==1 and record['last_tick']==243 and len(roster)==stride and len({tuple(v) for v in roster})==stride and record['rows']==243*stride and len(raw)==243*stride*width*8,'All six original surface centres and61 touchdown vertices per tick required')
        operations=[('longitude','atan2',0,1)]
        if surface:operations.append(('latitude','asin',2,None))
        operations.extend((('sin_latitude','sin',3 if surface else 2,None),('cos_latitude','cos',3 if surface else 2,None),('sin_longitude','sin',4 if surface else 3,None),('cos_longitude','cos',4 if surface else 3,None)))
        require([n for n,*_ in operations]==record['operators'],'Exact original sampled operator roster required')
        for i in range(243*stride):
            tick=i//stride+1;identity=roster[i%stride];base=i*width*8;data=[raw[base+8*v:base+8*(v+1)].hex() for v in range(width)]
            for label,fn,x,y in operations:
                tag='|'.join(map(str,[tick,*identity,label]));require(',' not in tag and '\n' not in tag,'Original object/point identity cannot alter the CSV protocol')
                yield group,(tag,fn,data[x],data[y] if y is not None else '')


def compare_results(output,items,manifest,role):
    digests={g:hashlib.sha256() for g in ORDER};values=[]
    with output.open() as stream:
        meta=json.loads(stream.readline());require(meta==dict(profile='amd-6121d02-fma3',rounding=0,mxcsr_control=8064),'Actual original hardware automatic dispatch/rounding required')
        reader=csv.DictReader(stream);require(reader.fieldnames==['tag','function','x','y','result'],'Exact unchanged original primitive collector output required')
        for (group,wanted),row in zip(items,reader,strict=True):
            value=row['result'];require(tuple(row[k] for k in ('tag','function','x','y'))==wanted and len(value)==16 and all(c in '0123456789abcdef' for c in value),'Every actual original ordered primitive invocation/result required')
            digests[group].update(bytes.fromhex(value));values.append(value)
    key='expected_complete_old_native_result_bits_sha256' if role=='old' else 'complete_original_Windows_result_bits_sha256'
    actual={g:d.hexdigest() for g,d in digests.items()};require(all(actual[g]==manifest['corpora'][g][key] for g in ORDER),'Complete actual '+role+' primitive result-stream digest differs: '+repr(actual))
    return dict(profile=meta,complete_observed_bits_sha256=actual,raw_output_sha256=sha(output)),values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('old-archive','api','output'):p.add_argument('--'+name,type=lambda s:Path(s).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh standard hosted component only; no local build/probe')
    owner=os.environ['GITHUB_SHA'];out=a.output;out.mkdir(parents=True);r=dict(status='running-unqualified',source=owner,old_source=OLD,fixed_source=FIXED,commands=[],new_simulator_processes=0,old_full_native_trajectory_recovered=False,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(out/'verification.json',r)
    def run(name,argv,source_input=None,env=None):
        argv=list(map(str,argv));log=out/(name+'.log');err=out/(name+'.stderr');inp=source_input.open('rb') if source_input else None
        try:
            with log.open('wb') as stream,err.open('wb') as errors:
                child=OwnedProcess(argv,cwd=ROOT,env=env,stdin=inp,stdout=stream,stderr=errors)
                try:child.process.wait(timeout=180)
                finally:receipt=child.cancel();atomic_json(out/(name+'-process.json'),receipt)
        finally:
            if inp:inp.close()
        observed=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']];require(len(observed)==1 and observed[0]['start_ticks']>0 and observed[0]['argv']==argv and receipt['actual_returncode']==0 and receipt['terminal'] is True and receipt['cancelled'] is False,'Actual component command failed: '+name)
        r['commands'].append(dict(name=name,argv=argv,actual_pid=observed[0]['pid'],start_ticks=observed[0]['start_ticks'],log_sha256=sha(log),stderr_sha256=sha(err),receipt_sha256=sha(out/(name+'-process.json'))));save();return log
    try:
        require(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==owner,'Actual current observer owner required')
        api=load(a.api);producer=api['run'];jobs=api['jobs'];artifact=api['artifact'];require(producer['id']==42913344936 and producer['head_sha']=='8a8501f29c3cc3107ded592a5558f03273ba9ae2' and producer['status']=='completed' and producer['conclusion']=='success' and producer['run_attempt']==1 and producer['repository']['private'] is False and producer['repository']['full_name']=='dcajacob/orbiter-cross-platform' and len(jobs)==1 and jobs[0]['id']==130169361885 and jobs[0]['conclusion']=='success' and jobs[0]['labels']==['ubuntu-24.04'] and jobs[0]['head_sha']==producer['head_sha'] and artifact['id']==13807359162 and artifact['expired'] is False and artifact['workflow_run']['id']==producer['id'] and artifact['workflow_run']['head_sha']==producer['head_sha'] and artifact['size_in_bytes']==a.old_archive.stat().st_size==597538 and artifact['digest']=='sha256:'+OLD_ARCHIVE_SHA and sha(a.old_archive)==OLD_ARCHIVE_SHA,'Exact original already-built negative component required; no duplicate old build')
        old=out/'old-reference-math.a'
        with zipfile.ZipFile(a.old_archive) as z:
            evidence=json.loads(z.read('old-atan2-negative/verification.json'));require(evidence['status']=='reproduced-old-automatic-atan2-negative-control-only' and evidence['unchanged_pre_fix_component_source']==OLD and evidence['actual_old_native_bits']=='bff6837bee57350a','Actual old immutable negative component required')
            old.write_bytes(z.read('old-atan2-negative/build/liborbiter_reference_math.a'))
        require(sha(old)==evidence['actual_old_static_math_library_sha256'],'Actual old archived static library bytes differ')
        tree=out/'fixed-source';tree.mkdir();archive=out/'fixed-source.tar';run('archive-original-fixed-component',['git','archive','--format=tar','--output='+str(archive),FIXED,MATH,VENDOR]);run('restore-original-fixed-component',['tar','-xf',archive,'-C',tree]);fixed_sources={}
        for n in subprocess.check_output(['git','ls-tree','-r','--name-only',FIXED,MATH,VENDOR],text=True).splitlines():
            path=tree/n;require(path.is_file() and not path.is_symlink() and path.read_bytes()==source(FIXED,n),'Actual original corrected source differs');fixed_sources[n]=sha(path)
        require(set(fixed_sources)=={p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file()},'Complete exact original corrected component required')
        build=out/'fixed-build';run('configure-original-fixed-math-only',['cmake','-S',tree/MATH,'-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Debug','-DBUILD_TESTING=OFF','-DORBITER_MATH_FORCE_SSE2=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_C_FLAGS='+SAN,'-DCMAKE_CXX_FLAGS='+SAN]);run('build-original-fixed-math-only',['cmake','--build',build,'--target','orbiter_reference_math','--parallel','2'])
        commands=load(build/'compile_commands.json');for_atan={Path(c['file']).name:c['command'] for c in commands if Path(c['file']).name.startswith('atan2_')};require(set(for_atan)=={'atan2_fma.c','atan2_sse2.c'} and all(v in for_atan['atan2_fma.c'] for v in ('-mfma','-ffp-contract=fast',SAN)) and all(v in for_atan['atan2_sse2.c'] for v in ('-mno-fma','-ffp-contract=off',SAN)),'Actual original corrected FMA/SSE2 compile flags required')
        harness=out/'NativeValues.cpp';harness.write_bytes(source(OLD,'Tests/Production/ReloadMath/NativeValues.cpp'));require((tree/MATH/'Runtime.h').read_bytes()==source(OLD,MATH+'/Runtime.h'),'Original read-only primitive collector interface changed')
        manifest=load(CORPUS/'provenance.json');inputs=list(operands(manifest));require(len(inputs)==85008,'Complete original2145/74115/8748 corpus required');input_file=out/'observed-operands.csv'
        with input_file.open('w',newline='') as stream:
            writer=csv.writer(stream,lineterminator='\n');writer.writerow(('tag','function','x','y'));writer.writerows(record for _,record in inputs)
        measurements={};actual={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for role,lib in (('old',old),('fixed',build/'liborbiter_reference_math.a')):
            executable=out/(role+'-native-values');run('link-'+role+'-original-readonly-observer',['/usr/bin/c++','-std=c++17',*SAN.split(),'-I'+str(tree/MATH),harness,lib,'-lm','-o',executable]);observed=run('observe-'+role+'-all-original-inputs',[executable],input_file,env);require((out/('observe-'+role+'-all-original-inputs.stderr')).stat().st_size==0,'Unsuppressed actual sanitizer or primitive observer diagnostics')
            measurements[role],actual[role]=compare_results(observed,inputs,manifest,role);measurements[role].update(actual_observer_executable_sha256=sha(executable),actual_native_math_archive_sha256=sha(lib))
        changes=[dict(group=g,tag=v[0],function=v[1],y=v[2],x=v[3],old=l,fixed=b) for (g,v),l,b in zip(inputs,actual['old'],actual['fixed'],strict=True) if l!=b]
        require(changes==[dict(group='surface',tag='211|Atlantis-SRB1|longitude',function='atan2',y='c1550c2a4f069879',x='412bcfdda20e1e30',old='bff6837bee57350a',fixed='bff6837bee573509')],'Exactly the original first observed surface primitive difference required')
        require(all(sha(tree/n)==d for n,d in fixed_sources.items()) and sha(old)==evidence['actual_old_static_math_library_sha256'] and list(operands(manifest))==inputs,'Every original source, library and complete ordered operand byte must remain exact')
        r.update(status='replayed-exact-complete-original-observed-primitive-sequences-only',actual_samples_per_binding={g:manifest['corpora'][g]['samples'] for g in ORDER},actual_old_and_fixed_observer_processes=2,original_readonly_observer_source_sha256=sha(harness),actual_corrected_source_sha256=fixed_sources,observed_input_sha256=sha(input_file),original_operand_manifest_sha256=sha(CORPUS/'provenance.json'),actual_measured_results=measurements,unique_first_sampled_operation_difference=changes[0],all_actual_fixed_bits_match_original_Windows=True,all_prior_sampled_primitive_bits_identical=True,original_full_historical_physical_trace_relabelled=False,original_primitive_or_runtime_acceptance_tolerances_changed=False)
    except BaseException as error:r.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(r['status'])


if __name__=='__main__':main()
