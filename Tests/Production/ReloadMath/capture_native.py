#!/usr/bin/env python3
"""Verify a reversible native math-observer toggle against a retained failing run."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('owner','baseline','assets','compositor-tools','gtk-plugin','output'):
        p.add_argument('--'+name,type=lambda s:Path(s).resolve(),required=True)
    package=p.add_mutually_exclusive_group(required=True)
    package.add_argument('--build',type=lambda s:Path(s).resolve(),help='Historical reversible math-call-toggle diagnostic build')
    package.add_argument('--retained-package',type=lambda s:Path(s).resolve(),help='Unmodified package; toggle only the additional passive observer')
    p.add_argument('--extra-observer',type=lambda s:Path(s).resolve())
    p.add_argument('--mode',choices=('off','on'),action='append')
    p.add_argument('--library',type=lambda s:Path(s).resolve(),action='append',required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(root/'Tests/Production/Closeout'))
    from contracts import require,sha,atomic_json,load
    from processes import OwnedProcess
    sys.path.insert(0,str(a.owner/'Tests/Production/RemainingStockPersistence'))
    import observations
    invocation=load(a.baseline/'invocation.json');producer=invocation['collector_producer_commit']
    reader=observations.bind_owner(a.owner,producer)
    native=reader.native
    if a.retained_package:
        require(a.extra_observer is not None,'Retained executable requires an additional passive observer')
        engine=a.retained_package/'engine';record=load(a.retained_package/'build.json')
        identity=native.build_identity(engine/'orbiter-production',engine/'NativeModules',a.retained_package/'build.json',record['source_base'])
        require(identity['sanitizer_linked'],'Actual unsuppressed sanitizer package required')
        executable=engine/'production_remaining_stock_diagnostic'
        guarded={str(a.owner/name):value for group in ('runtime_files_sha256','candidate_runtime_files_sha256','generated_source_files_sha256') for name,value in record[group].items()}
        require(guarded.get(str(executable))==sha(executable) and invocation['argv'][0]==str(executable),'Retained actual executable differs')
        build=dict(guarded_sha256=guarded);build_record=a.retained_package/'build.json'
    else:
        build=load(a.build/'build.json');executable=a.build/'production_remaining_stock_diagnostic';build_record=a.build/'build.json'
        require(build['status']=='built-observation-toggle-diagnostic-only' and build['insertion_reversible'] and
                build['executable_sha256']==sha(executable), 'Actual reversible diagnostic binary required')
    require(not a.output.exists(),'Fresh native observer equivalence output required');a.output.mkdir()
    original=invocation['argv'];engine=Path(original[0]).parent;asan=subprocess.check_output(['/usr/bin/c++','-print-file-name=libasan.so'],text=True).strip()
    probe=a.baseline.parent/'remaining-vessels-probe.so';require(probe.is_file(),'Retained real SDK observer required')
    names=[*native.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv','scene.rgba','saved.scn','flight-state.csv']
    expected={name:sha(a.baseline/name) for name in names}
    modes=a.mode or ['off','on'];require(len(set(modes))==len(modes),'Unique requested modes required')
    report=dict(status='running',diagnostic_only=True,requested_modes=modes,cases={},baseline_sha256=expected,
                diagnostic_build_sha256=sha(build_record),observer_kind='additional-passive-module' if a.retained_package else 'math-call-toggle',phase6_complete=False)
    extra=dict(path=str(a.extra_observer),sha256=sha(a.extra_observer)) if a.extra_observer else None
    report['extra_observer']=extra
    atomic_json(a.output/'capture.json',report)
    try:
        with native.Compositor(a.compositor_tools,a.output/'compositor') as display:
            def run(mode):
                out=a.output/('observer-'+mode);reader.stage_asset_tree(a.assets,out)
                scenario=invocation['scenario_entry_point'];target=out/scenario;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((a.baseline/scenario).read_bytes())
                for name in ('persistence-replay.csv','remaining-stock-finalized-frame-v2.txt'):
                    (out/name).write_bytes((a.baseline/name).read_bytes())
                cfg=out/'Orbiter.cfg';cfg.unlink(missing_ok=True);cfg.write_bytes((a.baseline/'staged-Orbiter.cfg').read_bytes())
                argv=[str(executable)]+[v.replace(str(a.baseline),str(out)) for v in original[1:]]
                env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                    LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[engine,*a.library])),
                    LD_PRELOAD=asan+':'+str(probe),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                    UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                if a.extra_observer and (not a.retained_package or mode=='on'):
                    env['LD_PRELOAD']=asan+':'+str(a.extra_observer)+':'+str(probe)
                env.pop('ORBITER_TEST_DISABLE_MATH_OBSERVER',None)
                if mode=='off' and not a.retained_package:env['ORBITER_TEST_DISABLE_MATH_OBSERVER']='1'
                atomic_json(out/'diagnostic-invocation.json',dict(argv=argv,mode=mode,saved_input_sha256=sha(target),
                    sanitizer_environment={k:env[k] for k in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS')},
                    sdk_observer_sha256=sha(probe),gtk_plugin_sha256=sha(a.gtk_plugin),extra_observer=extra))
                with (out/'console.log').open('w') as log:
                    process=OwnedProcess(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT);deadline=time.monotonic()+1200
                    try:
                        while process.process.poll() is None:
                            process.discover()
                            if time.monotonic()>deadline:raise TimeoutError('Native diagnostic timeout')
                            time.sleep(.25)
                    finally:
                        if process.process.poll() is None:process.cancel()
                receipt=process.receipt();atomic_json(out/'process-result.json',receipt)
                require(receipt['actual_returncode']==0 and not receipt['cancelled'],'Native diagnostic process failed')
                text=(out/'console.log').read_text(errors='replace')
                require(not any(s in text for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','LuaCall (')),'Unsuppressed native diagnostic finding')
                require(load(out/'graphics-lifecycle.json')==dict(rendered_frames=960,successful_presents=960,context_deleted=True),'Native graphics lifetime incomplete')
                require(all(sha(out/n)==v for n,v in expected.items()),'Observer toggle or relink changed original native simulation/frame/save bytes')
                rows=(out/'ground-math.csv').read_text().splitlines()
                require(len(rows)==(len((a.baseline/'ground-math.csv').read_text().splitlines()) if mode=='on' or a.retained_package else 1),'Actual enabled/disabled observation coverage differs')
                if mode=='on' or a.retained_package:require(sha(out/'ground-math.csv')==sha(a.baseline/'ground-math.csv'),'Enabled math observation differs from retained baseline')
                return mode,dict(process=receipt,baseline_bytes_identical=True,math_rows=len(rows)-1,files_sha256={n:sha(out/n) for n in names})
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                for future in concurrent.futures.as_completed([pool.submit(run,mode) for mode in modes]):
                    mode,result=future.result();report['cases'][mode]=result;atomic_json(a.output/'capture.json',report)
        require(all(sha(Path(p))==value for p,value in build['guarded_sha256'].items()),'Retained native package changed')
        require(extra is None or sha(a.extra_observer)==extra['sha256'],'Extra observer changed during capture')
        report.update(status='passed-native-observer-equivalence-diagnostic-only',passive_observer_baseline_equivalence=True,on_off_equivalence=set(modes)=={'off','on'})
        atomic_json(a.output/'capture.json',report);print(report['status'])
    except BaseException as error:
        report.update(status='failed',error=str(error))
        atomic_json(a.output/'capture.json',report)
        raise



if __name__=='__main__':main()
