#!/usr/bin/env python3
"""Run every original native unit and the already-corrected complete Catch discovery protocol."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import atomic_json,require,sha
from hosted_native_package import test_result
from recheck_native_discovery import expected_cases,inspect_discovery,inspect_execution,clean_sanitizers


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=lambda v:Path(v).resolve(),required=True);a=p.parse_args();folder=a.package;report=dict(status='running',commands=[],physics_version='assembly-contact-v2',qualification_granted=False);failures=[]
    environment=dict(os.environ,LD_PRELOAD=subprocess.check_output(['c++','-print-file-name=libasan.so'],text=True).strip(),PYTHONMALLOC='malloc',ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    def save():atomic_json(folder/'complete-unit-verification.json',report)
    def run(label,argv,cwd=ROOT):
        log=folder/(label+'.log');item=dict(label=label,argv=list(map(str,argv)));report['commands'].append(item);save()
        with log.open('w') as stream:
            child=subprocess.Popen(item['argv'],cwd=cwd,env=environment,stdout=stream,stderr=subprocess.STDOUT);item['actual_pid']=child.pid;save()
            try:item['actual_returncode']=child.wait(timeout=900)
            except subprocess.TimeoutExpired:child.kill();child.wait();item['actual_returncode']=child.returncode;item['timed_out']=True
        item['log_sha256']=sha(log);save()
        if item['actual_returncode']!=0:raise ValueError('Original unit/discovery command failed: '+label)
        clean_sanitizers(log.read_text(errors='replace'))
    try:
        for kind,build in [('engine',folder/'engine'),('upstream',folder/'upstream-units')]:
            try:
                run(kind+'-tests',['ctest','--test-dir',build,'--output-on-failure','--output-junit',folder/(kind+'-tests.xml')])
                report[kind]=test_result(folder/('registered-unit-tests.json' if kind=='engine' else 'upstream-registered-unit-tests.json'),folder/(kind+'-tests.xml'))
            except Exception as error:failures.append(dict(component=kind,error=str(error)));report['failures']=failures;save()
        results={}
        for short,binary,file,family in [('lua','existing_lua_unit','Tests/Lua.Interpreter.cpp','Lua.Interpreter'),('collision','existing_collision_unit','Tests/Collision.CollisionCore.cpp','Collision.CollisionCore')]:
            try:
                exe=folder/'upstream-units'/binary;command=[exe,*([folder/'upstream-units/assets'] if short=='lua' else [])]
                run('upstream-'+short+'-case-inventory',command+['--list-tests'],folder/'upstream-units')
                (folder/('upstream-'+short+'-case-inventory.txt')).write_bytes((folder/('upstream-'+short+'-case-inventory.log')).read_bytes())
                source=ROOT/file;cases=expected_cases(source.read_text());catalog=folder/(binary+'-discovery.xml');execution=folder/(binary+'-execution.xml')
                run(binary+'-discovery',command+['--list-tests','--reporter','xml','--out',catalog],folder/'upstream-units');discovery=inspect_discovery(catalog,cases,source)
                run(binary+'-execution',command+['--reporter','xml','--out',execution],folder/'upstream-units');results[family]=dict(discovery=discovery,execution=inspect_execution(execution,cases,source),binary_sha256=sha(exe))
            except Exception as error:failures.append(dict(component=family,error=str(error)));report['failures']=failures;save()
        report['fresh_upstream_results']=results
        require(not failures,'At least one original unit or complete-case discovery failed; every partial result preserved')
        require(report['engine']['executed_processes']==32 and report['upstream']['executed_processes']==2 and set(results)=={'Lua.Interpreter','Collision.CollisionCore'},'All original32engine and2upstream processes plus actual Catch cases required')
        report['status']='passed-all-original-native-units-and-complete-catch-cases'
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
