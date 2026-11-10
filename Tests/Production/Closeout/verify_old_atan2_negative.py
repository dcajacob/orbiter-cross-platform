#!/usr/bin/env python3
"""Fresh scoped negative observation of the exact pre-fix native math binding, no simulation."""
import argparse
import csv
import gzip
import hashlib
import os
from pathlib import Path
import subprocess
from contracts import ROOT,require,load,sha,atomic_json
from processes import OwnedProcess

OLD='c0d03b1b2122f650c72f372d267b0c9f2aac314a'
MATH='Src/Orbiter/Production/Math'
VENDOR='Extern/ReferenceMath'
FIXTURE=ROOT/'Tests/Production/Math/Reference/ReloadAtan2'
DRIVER=ROOT/'Tests/Production/Closeout/NumericalRecovery/OldAtan2Negative.cpp'
SAN='-fsanitize=address,undefined -fno-omit-frame-pointer'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=lambda s:Path(s).resolve(),required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh standard hosted component only; no local build or simulator')
    source=os.environ['GITHUB_SHA'];require(source==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'Actual diagnostic driver owner required')
    out=a.output;out.mkdir(parents=True);report=dict(status='running-unqualified',source=source,unchanged_pre_fix_component_source=OLD,commands=[],actual_new_simulator_processes=0,original_failed_world_relabelled=False,old_missing_live_trace_recovered=False,complete_numerical_reload_gate_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(out/'verification.json',report)
    def run(name,argv,env=None):
        log=out/(name+'.log')
        with log.open('wb') as stream:
            process=OwnedProcess(list(map(str,argv)),cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            try:process.process.wait(timeout=180)
            finally:receipt=process.cancel();atomic_json(out/(name+'-process.json'),receipt)
        observed=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']]
        report['commands'].append(dict(name=name,argv=list(map(str,argv)),receipt_sha256=sha(out/(name+'-process.json')),log_sha256=sha(log),actual_returncode=receipt['actual_returncode']));save()
        require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and len(observed)==1 and observed[0]['argv']==list(map(str,argv)) and observed[0]['start_ticks']>0,'Actual original component command did not complete: '+name)
    try:
        provenance=load(FIXTURE/'provenance.json');require(provenance['automatic_refresh'] is False and provenance['exact_input']==dict(function='atan2',y='c1550c2a4f069879',x='412bcfdda20e1e30') and sha(FIXTURE/'windows.csv.gz')==provenance['fixture_sha256'],'Original exact captured pair required')
        with gzip.open(FIXTURE/'windows.csv.gz','rt') as stream:seed=next(v for v in csv.DictReader(stream) if v['tag']=='0|0')
        require(seed['y']==provenance['exact_input']['y'] and seed['x']==provenance['exact_input']['x'] and seed['fma3']=='bff6837bee573509' and seed['sse2']=='bff6837bee57350a','Original automatic and SSE2 fixture bits required')
        original=out/'original-source';original.mkdir();archive=out/'original-source.tar'
        run('archive-original-component',['git','archive','--format=tar','--output='+str(archive),OLD,MATH,VENDOR]);run('restore-original-component',['tar','-xf',archive,'-C',original])
        sources={}
        for name in subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,MATH,VENDOR],text=True).splitlines():
            target=original/name;require(target.is_file() and not target.is_symlink() and target.read_bytes()==subprocess.check_output(['git','show',OLD+':'+name]),'Every original pre-fix component/vendor byte required');sources[name]=sha(target)
        require(sources and set(sources)=={p.relative_to(original).as_posix() for p in original.rglob('*') if p.is_file()},'Complete exact original standalone math component required')
        require(DRIVER.read_bytes()==subprocess.check_output(['git','show',source+':'+DRIVER.relative_to(ROOT).as_posix()]),'Exact current observer driver source required')
        build=out/'build';run('configure-original-math-only',['cmake','-S',original/MATH,'-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Debug','-DBUILD_TESTING=OFF','-DORBITER_MATH_FORCE_SSE2=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_C_FLAGS='+SAN,'-DCMAKE_CXX_FLAGS='+SAN])
        run('build-original-math-only',['cmake','--build',build,'--target','orbiter_reference_math','--parallel','2'])
        commands=load(build/'compile_commands.json');atan=[v['command'] for v in commands if Path(v['file']).name=='atan2.c'];require(len(atan)==1 and all(flag in atan[0] for flag in ('-mno-avx','-mno-fma','-ffp-contract=off','-fsanitize=address,undefined')) and '-mfma' not in atan[0],'Actual old automatic atan2 C body must retain its original SSE2-only compilation')
        binary=out/'old-atan2-negative';run('link-observation-driver',['/usr/bin/c++','-std=c++17',*SAN.split(),'-I'+str(original/MATH),DRIVER,build/'liborbiter_reference_math.a','-lm','-Wl,-Map,'+str(out/'actual-link-map.txt'),'-o',binary])
        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run('observe-exact-old-automatic-result',[binary,seed['y'],seed['x']],env);actual=(out/'observe-exact-old-automatic-result.log').read_text().splitlines();require(actual==['amd-6121d02-fma3',seed['sse2']] and actual[1]!=seed['fma3'],'Old actual hardware automatic binding must reproduce the exact historical rejected bit, without any simulator run')
        require(all(sha(original/n)==v for n,v in sources.items()),'Original compiled/vendor source changed')
        report.update(status='reproduced-old-automatic-atan2-negative-control-only',exact_original_input=provenance['exact_input'],actual_CPU_dispatch=actual[0],actual_old_native_bits=actual[1],required_original_Windows_automatic_bits=seed['fma3'],actual_old_binding_rejected_by_original_bit_exact_expectation=True,unchanged_original_source_files_sha256=sources,original_source_archive_sha256=sha(archive),actual_CMake_compile_commands_sha256=sha(build/'compile_commands.json'),actual_old_static_math_library_sha256=sha(build/'liborbiter_reference_math.a'),actual_observation_executable_sha256=sha(binary),actual_link_map_sha256=sha(out/'actual-link-map.txt'),driver_source_sha256=sha(DRIVER),fixture_sha256=provenance['fixture_sha256'],actual_original_sanitizers_unsuppressed=True,original_positive_math_suite_not_replaced=True,original_full_first_difference_report_recovered=False)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
