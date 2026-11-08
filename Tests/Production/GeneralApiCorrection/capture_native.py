#!/usr/bin/env python3
"""Capture the original failure and versioned API correction with a retained package."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from prepare import ROOT,ORIGINAL,prepare,require,digest
from startup_contract import SAVE_SENTINEL, inspect_native


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('owner','package','assets','data','planets','compositor-tools','gtk-plugin','output'):
        p.add_argument('--'+name,type=lambda s:Path(s).resolve(),required=True)
    p.add_argument('--library',type=lambda s:Path(s).resolve(),action='append',required=True)
    a=p.parse_args();sys.path[:0]=[str(ROOT/'Tests/Production/Closeout'),str(a.owner/'Tests/Production/StockScenarios'),
                                 str(a.owner/'Tests/Production/RemainingStockPersistence')]
    from contracts import atomic_json,sha
    from processes import OwnedProcess
    import intentional_exit
    from capture_native import stage_asset_tree
    # Bind the compositor by its original owning source, independently of the
    # correction producer. Do not relabel the retained simulator package.
    import importlib.util
    file=a.owner/'Tests/Production/RemainingVessels/native.py'
    spec=importlib.util.spec_from_file_location('api_native_owner',file);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    build=json.loads((a.package/'build.json').read_text());engine=a.package/'engine'
    identity=intentional_exit.build_identity(engine/'orbiter-production',engine/'NativeModules',a.package/'build.json',build['source_base'])
    require(identity['sanitizer_linked'],'Actual ASan/UBSan package required')
    require(not a.output.exists(),'Fresh API diagnostic output required');a.output.mkdir()
    variant=a.output/'variant';proof=prepare(variant,'v2')
    libraries=[directory/name for directory in a.library for name in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0')
               if (directory/name).exists()]
    require({p.name for p in libraries}=={'libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0'},'Pinned native providers required')
    guards={str(path):sha(path) for path in [a.gtk_plugin,*libraries,a.package/'build.json',a.assets/'remaining-vessels-resources.json']}
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    sources=[Path(__file__),Path(__file__).with_name('prepare.py'),Path(__file__).with_name('startup_contract.py'),
             Path(__file__).with_name('startup-policy-v1.json')]
    for source in sources:
        require(digest(subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+source.relative_to(ROOT).as_posix()]))==sha(source),
                'API capture source must match its immutable producer')
    guards.update({str(source):sha(source) for source in sources})
    report=dict(status='running',runtime_identity=identity,build_sha256=sha(a.package/'build.json'),variant=proof,
                producer_commit=producer,cases={},guarded_files_sha256=guards,normal_admission_qualified=False,phase6_complete=False)
    atomic_json(a.output/'diagnostic.json',report)
    try:
        with native.Compositor(a.compositor_tools,a.output/'compositor') as display:
            for mode in ('original','corrected'):
                out=a.output/mode;stage_asset_tree(a.assets,out)
                target=out/ORIGINAL;require(sha(target)==proof['original_script_sha256'],'Copied original script differs')
                if mode=='corrected':target.unlink();target.write_bytes((variant/ORIGINAL).read_bytes())
                cfg=out/'Orbiter.cfg';cfg.unlink(missing_ok=True);cfg.write_bytes((a.owner/'Tests/Production/NativeScene/Orbiter.cfg').read_bytes())
                saved=out/'saved.scn';saved.write_bytes(SAVE_SENTINEL)
                argv=[str(engine/'orbiter-production'),'--assets',str(out),'--data',str(a.data),'--planets',str(a.planets),
                    '--modules',str(engine/'NativeModules'),'--scenario',str(out/'Scenarios/Tests/GeneralApiTest.scn'),
                    '--config',str(cfg),'--evidence',str(out),'--save',str(saved),'--frames','60','--fixed-step','0.015625','--run']
                env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                    LD_LIBRARY_PATH=':'.join(map(str,[engine,*a.library])),LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),
                    ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                env.pop('LD_PRELOAD',None)
                atomic_json(out/'diagnostic-invocation.json',dict(argv=argv,script_sha256=sha(target),
                    sanitizer_environment={k:env[k] for k in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS')}))
                with (out/'console.log').open('w') as log:
                    process=OwnedProcess(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT);deadline=time.monotonic()+240
                    try:
                        while process.process.poll() is None:
                            process.discover()
                            if time.monotonic()>deadline:raise TimeoutError('API diagnostic timeout')
                            time.sleep(.1)
                    finally:
                        if process.process.poll() is None:process.cancel()
                receipt=process.receipt();require(receipt['actual_returncode']==0 and not receipt['cancelled'],'API simulator failed')
                text=(out/'console.log').read_text(errors='replace')
                require(not any(s in text for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:')),
                        'Unsuppressed native sanitizer finding')
                if mode=='corrected':require(text.count('=== All tests passed ===')==1 and ' - FAILED!' not in text and 'LuaCall (' not in text,
                                             'Corrected actual API script failed')
                else:require('Assertion failed' in text and 'Test: planet status' in text and '=== All tests passed ===' not in text,
                             'Original failure was lost')
                life=json.loads((out/'graphics-lifecycle.json').read_text());require(life['context_deleted'],'API context was not closed')
                math=json.loads((out/'numerics.json').read_text())['math']
                require(math=='amd-6121d02-'+('sse2' if identity['math_profile']=='sse2' else 'fma3'),
                        'Actual API CPU math path differs')
                startup=inspect_native(out,identity['profile'],receipt['actual_returncode'],target,
                                       out/'Scenarios/Tests/GeneralApiTest.scn',saved) if mode=='corrected' else None
                report['cases'][mode]=dict(process=receipt,graphics=life,script_sha256=sha(target),console_sha256=sha(out/'console.log'),
                    actual_math=math,startup_exit=startup,script_result='failed-inherited-assertion' if mode=='original' else 'passed-corrected-test')
                atomic_json(a.output/'diagnostic.json',report)
        require(all(sha(Path(path))==value for path,value in guards.items()),'Pinned API runtime/provider inputs changed')
        require(intentional_exit.build_identity(engine/'orbiter-production',engine/'NativeModules',a.package/'build.json',build['source_base'])==identity,
                'Retained native source/package changed')
        report['status']='captured-original-and-corrected-native-diagnostic-only'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:atomic_json(a.output/'diagnostic.json',report)


if __name__=='__main__':main()
