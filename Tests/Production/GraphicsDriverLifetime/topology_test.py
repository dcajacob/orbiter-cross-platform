#!/usr/bin/env python3
"""Check the actual Mesa CPU cache owner across repeated dlclose, without suppressions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from topology_cleanup import ORIGINAL_SHA256,APPEND,candidate

HERE=Path(__file__).resolve().parent


def require(value,message):
    if not value:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesa-build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true','Hosted Linux ownership controls only')
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    database=json.loads((a.mesa_build/'compile_commands.json').read_text());entries=[d for d in database if Path(d['file']).name=='u_cpu_detect.c']
    require(len(entries)==1,'One actual configured Mesa CPU source command required');entry=entries[0]
    source=(Path(entry['directory'])/entry['file']).resolve();compiled=source.read_bytes()
    require(compiled.endswith(APPEND),'Explicit separate topology lifetime variant required')
    original=compiled[:-len(APPEND)];require(candidate(original)==compiled,'All original CPU detection/affinity bytes must remain unchanged')
    baseline=output/'baseline-u_cpu_detect.c';baseline.write_bytes(original)
    report=dict(status='running',original_source_sha256=ORIGINAL_SHA256,compiled_source_sha256=hashlib.sha256(compiled).hexdigest(),
        commands=[],runs={},sanitizers=dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),
        simulation_executed=False,qualification_granted=False,phase6_complete=False)
    def command(argv,cwd,label,environment=None):
        with (output/(label+'.log')).open('w') as stream:
            child=subprocess.Popen(argv,cwd=cwd,env=environment,stdout=stream,stderr=subprocess.STDOUT)
            code=child.wait(timeout=120)
        report['commands'].append(dict(argv=argv,cwd=str(cwd),actual_pid=child.pid,actual_returncode=code,label=label,
            log_sha256=hashlib.sha256((output/(label+'.log')).read_bytes()).hexdigest()))
        return code
    try:
        configured=shlex.split(entry['command']);flags=[];i=1
        while i<len(configured):
            value=configured[i]
            if value in ('-o','-MF','-MQ'):i+=2;continue
            if value in ('-MD','-c') or value==entry['file']:i+=1;continue
            flags.append(value);i+=1
        for name,path in (('baseline',baseline),('candidate',source)):
            fixture=output/(name+'.c')
            fixture.write_text('#include '+json.dumps(str(path))+'''\n
__attribute__((visibility("default"))) int prepare_topology_fixture(int genuine);
__attribute__((visibility("default"))) int prepare_topology_fixture(int genuine) {
    if(util_cpu_caps.L3_affinity_mask || _util_cpu_caps_state.caps.L3_affinity_mask)return 1;
    util_affinity_mask *owned=realloc(NULL,sizeof(util_affinity_mask));
    if(!owned)return 2;
    memset(owned,0x5a,sizeof(util_affinity_mask));
    util_cpu_caps.L3_affinity_mask=owned;
    _util_cpu_caps_state.caps.L3_affinity_mask=owned;
    for(unsigned n=0;n<sizeof(util_affinity_mask);++n)
        if(((unsigned char*)util_cpu_caps.L3_affinity_mask)[n]!=0x5a ||
           ((unsigned char*)_util_cpu_caps_state.caps.L3_affinity_mask)[n]!=0x5a)return 3;
    if(genuine) {
        void *lost=malloc(4096);
        if(!lost)return 4;
        memset(lost,0x42,4096);
        __asm__ volatile("" : : "r"(lost) : "memory");
    }
    return 0;
}
''')
            argv=[configured[0],*flags,'-ffunction-sections','-fdata-sections','-fvisibility=hidden','-fPIC',
                '-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-shared','-Wl,--gc-sections',str(fixture),'-o',str(output/(name+'.so'))]
            require(command(argv,entry['directory'],'build-'+name)==0,'Actual original/candidate Mesa cache fixture compilation failed')
        loader=output/'loader'
        require(command(['c++','-std=c++17','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-gnu-unique',
            str(HERE/'TopologyOwner.Test.cpp'),'-ldl','-o',str(loader)],HERE,'build-loader')==0,'Actual ownership loader compilation failed')
        environment=dict(os.environ,**report['sanitizers'])
        for name,kind,genuine in (('baseline','baseline',0),('candidate','candidate',0),('genuine-leak','candidate',1)):
            code=command([str(loader),str(output/(kind+'.so')),str(genuine)],HERE,'run-'+name,environment)
            text=(output/('run-'+name+'.log')).read_text();report['runs'][name]=dict(actual_returncode=code,output=text)
            require('completed_ownership_cycles=20' in text,'All twenty actual DSO ownership lifetimes required')
            if name=='candidate':require(code==0 and not any(v in text for v in ('ERROR:','runtime error:','SUMMARY:')),'Candidate cache lifetime is not sanitizer-clean')
            else:
                expected=2560 if name=='baseline' else 81920
                require(code!=0 and 'ERROR: LeakSanitizer:' in text and f'{expected} byte(s) leaked in 20 allocation(s)' in text,
                    'Actual unsuppressed original-owner and independent genuine-leak failures required')
        require(source.read_bytes()==compiled and baseline.read_bytes()==original,'Owning baseline/candidate CPU source changed')
        report['status']='passed'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:(output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['runs'],indent=2))


if __name__=='__main__':main()
