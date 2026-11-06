#!/usr/bin/env python3
"""Build a diagnostic observation toggle without changing a retained package or physics."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ANCHOR='math_observation::Row(mathTrace,completedTicks,time.SimT0,*v,MakeVECTOR3(earth->GPos()),er,ob,earth->Rotation());'
PREFIX='#include <cstdlib>\n'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def instrument(body):
    text=body.decode()
    if text.count(ANCHOR)!=1:raise ValueError('Unique original read-only observation call required')
    replacement='if (!std::getenv("ORBITER_TEST_DISABLE_MATH_OBSERVER")) '+ANCHOR
    generated=PREFIX+text.replace(ANCHOR,replacement)
    if generated.removeprefix(PREFIX).replace(replacement,ANCHOR)!=text:
        raise ValueError('Observation toggle does not recover the original translation unit')
    return generated.encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',type=Path,required=True);parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh isolated diagnostic build required')
    args.output=args.output.resolve();args.owner=args.owner.resolve();args.package=args.package.resolve()
    engine=args.package/'engine';source=args.owner/'Src/Orbiter/Production/NativeApplication.cpp'
    build=json.loads((args.package/'build.json').read_text());original=source.read_bytes()
    if hashlib.sha256(original.replace(b'\r\n',b'\n')).hexdigest()!=build['source_sha256_lf']['Src/Orbiter/Production/NativeApplication.cpp']:
        raise ValueError('Retained owning source differs from package')
    commands=json.loads((engine/'compile_commands.json').read_text())
    chosen=[c for c in commands if c['file']==str(source) and 'production_remaining_stock_diagnostic.dir/' in c['output']]
    if len(chosen)!=1:raise ValueError('Exact diagnostic translation unit command required')
    args.output.mkdir(parents=True);generated=args.output/'NativeApplication.cpp';generated.write_bytes(instrument(original))
    obj=args.output/'NativeApplication.cpp.o';exe=args.output/'production_remaining_stock_diagnostic'
    compile_args=shlex.split(chosen[0]['command'])
    compile_args[compile_args.index('-o')+1]=str(obj);compile_args[compile_args.index('-c')+1]=str(generated)
    compile_args[1:1]=['-iquote',str(source.parent)]
    link_line=subprocess.check_output(['ninja','-C',str(engine),'-t','commands','production_remaining_stock_diagnostic'],text=True).splitlines()[-1]
    parts=link_line.split(' && ')
    if len(parts)!=3 or parts[0]!=':' or parts[-1]!=':':raise ValueError('Unexpected retained link command structure')
    link_args=shlex.split(parts[1]);link_args[link_args.index('-o')+1]=str(exe)
    old_object=str(Path(chosen[0]['output']).relative_to(engine))
    if link_args.count(old_object)!=1:raise ValueError('Exact retained application object required')
    link_args[link_args.index(old_object)]=str(obj)
    link_args=[('-Wl,--dependency-file='+str(args.output/'link.d')) if a.startswith('-Wl,--dependency-file=') else a for a in link_args]
    guarded={str(p):sha(p) for p in (source,args.package/'build.json',engine/'build.ninja',engine/'compile_commands.json',
        engine/'production_remaining_stock_diagnostic',engine/'liborbiter_production_vessels.so',engine/'liborbiter_production_boundary.so',engine/'Math/liborbiter_reference_math.a')}
    report=dict(status='building',diagnostic_only=True,original_source_sha256=sha(source),generated_source_sha256=sha(generated),
        insertion_reversible=True,physics_formulas_and_order_unchanged=True,compile_command=compile_args,link_command=link_args,
        retained_package=str(args.package),retained_source=build['source_base'],guarded_sha256=guarded,phase6_complete=False)
    try:
        for label,argv in [('compile',compile_args),('link',link_args)]:
            with (args.output/(label+'.log')).open('w') as log:
                process=subprocess.Popen(argv,cwd=engine,stdout=log,stderr=subprocess.STDOUT)
                report[label+'_pid']=process.pid;report[label+'_returncode']=process.wait()
            if report[label+'_returncode']!=0:raise ValueError('Diagnostic '+label+' failed')
        if any(sha(Path(p))!=value for p,value in guarded.items()):raise ValueError('Retained source/package changed')
        report.update(status='built-observation-toggle-diagnostic-only',executable_sha256=sha(exe))
    except BaseException as error:
        report.update(status='failed',error=str(error))
        raise
    finally:
        (args.output/'build.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
