#!/usr/bin/env python3
"""Diagnose the first invalid HST contact operation; no production or acceptance edits."""
import hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'Tests/Production/Closeout')]
from contracts import require,sha,load,atomic_json
from transforms import replace_once
import native_capture
from hosted_contact_component_trial import method
from inspect_rejection_cpp_abi import abi_tokens,host_macros
from restore_rejection_sdk_header import binary_sdk_base,header_bytes
from processes import OwnedProcess
from rejection_input_bundle import pack
PROFILE='Debug-automatic';RUNTIME=native_capture.RUNTIME
SCENE='Satellites and Probes/Hubble Space Telescope/HST Launch.scn'
OUTPUT=ROOT/'out/physics-v2-HST-first-invalid'/PROFILE



def component(mode):
    require(mode in ('current-methods-control','first-invalid-trap'),'Exact diagnostic component mode required')
    source=ROOT/'Src/Orbiter/SuperVessel.cpp';body=source.read_text();immutable=subprocess.check_output(['git','show',RUNTIME+':Src/Orbiter/SuperVessel.cpp'],cwd=ROOT).decode()
    require(body==immutable,'Approved physics v2 source must remain exactly unchanged')
    methods=[method(body,s) for s in ('void SuperVessel::GetIntermediateMoments (','bool SuperVessel::AddSurfaceForces (','void SuperVessel::SetDefaultState ()')]
    complete=''.join(methods);instrumented=[]
    for i,code in enumerate(methods):
        pos=code.index('{')+1;code=code[:pos]+'\n    actual_call('+str(i)+');'+code[pos:]
        if i==0 and mode=='first-invalid-trap':
            code=replace_once(code,'\n\t// TODO: Move this up to VesselBase','\n    TrapScope first_invalid;\n\t// TODO: Move this up to VesselBase')
        instrumented.append(code)
    prefix=r'''#define _GNU_SOURCE 1
#include "SuperVessel.h"
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <csignal>
#include <cfenv>
#include <execinfo.h>
#include <dlfcn.h>
#include <ucontext.h>
#include <unistd.h>
namespace {
std::atomic<bool> seen[3]{};
void actual_call(unsigned index) {
    if(!seen[index].exchange(true)) if(const char* path=std::getenv("ORBITER_HST_CALLS"))
        if(auto* out=std::fopen(path,"a")) { std::fputs(index==0?"moments\n":index==1?"surface\n":"defaults\n",out); std::fclose(out); }
}
void first_invalid_handler(int, siginfo_t* info, void* context) {
    const auto pc=reinterpret_cast<void*>(static_cast<ucontext_t*>(context)->uc_mcontext.gregs[REG_RIP]);
    Dl_info identity{};dladdr(pc,&identity);
    std::fprintf(stderr,"HST_FIRST_INVALID code=%d pc=%p binary=%s offset=0x%lx\n",info->si_code,pc,identity.dli_fname?identity.dli_fname:"?",static_cast<unsigned long>(reinterpret_cast<uintptr_t>(pc)-reinterpret_cast<uintptr_t>(identity.dli_fbase)));
    void* frames[64];const int count=backtrace(frames,64);backtrace_symbols_fd(frames,count,STDERR_FILENO);
    std::fflush(stderr);_Exit(136);
}
struct TrapScope {
    fenv_t saved;
    TrapScope() { fegetenv(&saved);struct sigaction action{};action.sa_sigaction=first_invalid_handler;action.sa_flags=SA_SIGINFO;sigemptyset(&action.sa_mask);sigaction(SIGFPE,&action,nullptr);feclearexcept(FE_ALL_EXCEPT);feenableexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW); }
    ~TrapScope() { fesetenv(&saved); }
};
}
'''
    return prefix+'\n'.join(instrumented),dict(mode=mode,compiled_application=RUNTIME,complete_unchanged_method_bodies_sha256=hashlib.sha256(complete.encode()).hexdigest(),production_sources_modified=False,diagnostic_only=True,qualification_granted=False)


def run_cases(output,providers,mesa,report,save):
    from compositor import Compositor
    build=ROOT/'out/phase6-physics-v2-native'/PROFILE;engine=build/'engine';record=load(build/'build.json');native_capture.verify_units(PROFILE)
    require(record['source_base']==RUNTIME and record['instrumentation']=='address,undefined','Actual approved sanitized runtime required')
    prior=load(HERE/'HST-first-invalid-origin.json');prior_base=ROOT/'out/physics-v2-HST-first-invalid-source';prior_api=load(prior_base/'api.json');prior_zip=prior_base/'producer.zip'
    require(prior_api['artifact']['digest']=='sha256:'+sha(prior_zip) and prior_zip.stat().st_size==prior['receipt_bytes'],'Actual retained earlier full-sweep receipt bytes required')
    with zipfile.ZipFile(prior_zip) as z: old=json.loads(z.read('hosted-normal-admission/'+PROFILE+'/capture/stock-scenarios.json'))
    case=old['cases'][SCENE];require(old['observer_commit']==prior['source'] and old['runtime_identity']['runtime_source_commit']==RUNTIME and old['summary']['passed']==156 and old['summary']['failed']==1 and case['status']=='failed' and case['files_sha256']['flight-state.csv']==prior['HST_trace_sha256'],'Actual original completed new-version failed HST identity required')
    unchanged={str(ROOT/n):h for n,h in record['runtime_files_sha256'].items()};unchanged[str(ROOT/'Src/Orbiter/SuperVessel.cpp')]=sha(ROOT/'Src/Orbiter/SuperVessel.cpp')
    require(all(sha(n)==h for n,h in unchanged.items()),'Every actual runtime byte required before diagnostic')
    compiler=output/'isolated-compiler';compiler.mkdir();sdk=compiler/'sdk';sdk.mkdir();template=ROOT/'Src/Orbiter/Production/NativeBuild.h.in'
    require(template.read_bytes()==subprocess.check_output(['git','show',RUNTIME+':'+template.relative_to(ROOT).as_posix()],cwd=ROOT),'Exact actual compiled SDK template required')
    header=sdk/'OrbiterNativeBuild.h';header.write_bytes(header_bytes(template.read_bytes(),binary_sdk_base(engine/'liborbiter_production_boundary.so','Debug'),'ON'))
    macros=host_macros(header,compiler);tokens=abi_tokens((engine/'liborbiter_production_boundary.so').read_bytes());require(tokens==[macros['actual_cpp_abi']],'Actual component compiler ABI must match actual retained v2 engine')
    compiled={}
    for mode in ('current-methods-control','first-invalid-trap'):
        body,item=component(mode);cpp=compiler/(mode+'.cpp');cpp.write_text(body);library=compiler/(mode+'.so')
        argv=['/usr/bin/c++','-std=c++17','-O0','-g','-fPIC','-shared','-Wl,--no-undefined','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DORBITER_PRODUCTION_SHARED','-DORBITER_NATIVE_BUILD_CONFIGURATION="Debug"','-I'+str(ROOT/'Src/Orbiter'),'-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(sdk),str(cpp),'-L'+str(engine),'-Wl,-rpath,'+str(engine),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(library)]
        log=compiler/(mode+'.log')
        with log.open('wb') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);code=child.wait(timeout=300)
        item.update(actual_pid=child.pid,actual_returncode=code,argv=argv,source_sha256=sha(cpp),log_sha256=sha(log));compiled[mode]=item;atomic_json(compiler/'compiler.json',dict(actual_abi=macros,variants=compiled))
        if code:print(log.read_text(errors='replace')[-10000:],flush=True)
        require(code==0,'Actual isolated diagnostic component compilation failed')
        item['library_sha256']=sha(library);atomic_json(compiler/'compiler.json',dict(actual_abi=macros,variants=compiled))
    program="import sys,pathlib;sys.path.insert(0,str(pathlib.Path('Tests/Production/StockScenarios').resolve()));import run;sys.stdout.write(run.configuration(False))"
    config=subprocess.check_output([sys.executable,'-B','-c',program],cwd=ROOT,text=True)
    gtk=providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so';libraries=[engine,*(providers/f/'install/lib/x86_64-linux-gnu' for f in ('fontconfig-candidate','gdk-candidate')),mesa/'install/lib/x86_64-linux-gnu']
    report.update(actual_application_rebuilt=False,original_sanitizers_unchanged=True,original_clock_seconds=.25,original_frames=60,diagnostic_processes={});save()
    with Compositor(providers/'compositor',output/'trial-compositor') as display:
        common=dict(display.environment,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'),LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LD_LIBRARY_PATH=':'.join(map(str,libraries)),LIBDECOR_PLUGIN_DIR=str(gtk.parent),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for mode in ('unchanged-application','current-methods-control','first-invalid-trap'):
            folder=output/mode;folder.mkdir();(folder/'Orbiter.cfg').write_text(config);(folder/'staged-Orbiter.cfg').write_text(config)
            argv=[str(engine/'orbiter-production'),'--assets',str(ROOT/'out/native-stock-assets'),'--data',str(ROOT/'out/native-stock-data'),'--planets',str(ROOT/'out/native-stock-planets'),'--modules',str(engine/'NativeModules'),'--config',str(folder/'Orbiter.cfg'),'--scenario',str(ROOT/'out/native-stock-assets/Scenarios'/SCENE),'--evidence',str(folder),'--save',str(folder/'saved.scn'),'--frames','60','--fixed-step','.25','--run']
            env=dict(common)
            if mode!='unchanged-application':env.update(LD_PRELOAD='/usr/lib/x86_64-linux-gnu/libasan.so.8:'+str(compiler/(mode+'.so')),ORBITER_HST_CALLS=str(folder/'actual-component-calls.txt'))
            atomic_json(folder/'invocation.json',argv)
            with (folder/'console.log').open('w') as console:
                proc=OwnedProcess(argv,cwd=folder,env=env,stdout=console,stderr=subprocess.STDOUT);deadline=time.monotonic()+180
                try:
                    while proc.process.poll() is None:
                        proc.discover()
                        if time.monotonic()>deadline:raise subprocess.TimeoutExpired(argv,180)
                        time.sleep(.1)
                finally:
                    if proc.process.poll() is None:proc.cancel()
                    atomic_json(folder/'process-receipt.json',proc.receipt())
            receipt=proc.receipt();trace=folder/'flight-state.csv';console=(folder/'console.log').read_text(errors='replace');calls=(folder/'actual-component-calls.txt').read_text().splitlines() if (folder/'actual-component-calls.txt').exists() else []
            item=dict(actual_pid=proc.process.pid,actual_returncode=proc.process.returncode,terminal=receipt['terminal'],cancelled=receipt['cancelled'],trace_sha256=sha(trace) if trace.exists() else None,actual_component_dispatches=calls,first_invalid_recorded='HST_FIRST_INVALID code=' in console,original_nonfinite_failure='Orbiter native production: Nonfinite flight state' in console,qualification_granted=False)
            report['diagnostic_processes'][mode]=item;save();print(json.dumps(dict(mode=mode,**item)),flush=True)
            if mode=='first-invalid-trap':
                print(console[-14000:],flush=True)
                import re
                locations=re.findall(r'(/[^\s()]+\.so)\(\+?(0x[0-9a-f]+)\)',console)
                locations+=re.findall(r'binary=([^\s]+) offset=(0x[0-9a-f]+)',console)
                for binary,address in locations:
                    result=subprocess.run(['addr2line','-e',binary,'-f','-C',address],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
                    with (folder/'resolved-stack.txt').open('a') as stream:stream.write(binary+' '+address+'\n'+result.stdout)
                require(item['first_invalid_recorded'] and item['actual_returncode']==136,'A real first invalid exception and actual terminal diagnostic process required')
            else:require(item['original_nonfinite_failure'] and item['actual_returncode']==1,'Both actual controls must preserve the actual HST failure')
            if mode!='unchanged-application':require(set(calls)=={'moments','surface','defaults'},'All exact method dispatches must be actually observed')
    require(display.process.returncode==0,'Owned compositor must terminate normally')
    require(report['diagnostic_processes']['unchanged-application']['trace_sha256']==report['diagnostic_processes']['current-methods-control']['trace_sha256']==prior['HST_trace_sha256'],'Unchanged method interposition must reproduce byte-identical HST failure')
    require(all(sha(n)==h for n,h in unchanged.items()),'Every approved production/runtime byte must remain unchanged after diagnostics')
    atomic_json(output/'unchanged-runtime-postflight.json',dict(status='passed',files_sha256=unchanged,qualification_granted=False));report['complete_control_trace_identical']=True;save()


def prepared_body():
    body=native_capture.prepared_body();body=replace_once(body,"protocol='phase6-versioned-physics-v2-normal-admission'","protocol='phase6-physics-v2-HST-first-invalid-diagnostic'")
    body=replace_once(body,"ROOT/'out/hosted-normal-admission'","ROOT/'out/physics-v2-HST-first-invalid'")
    start=body.index('        from native_capture import version_lock,verify_scope,REFERENCE,EXIT,RUNTIME');end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    body=body[:start]+"        from hst_fpe import run_cases\n        run_cases(output,providers,mesa,report,save)\n"+body[end:]
    body=replace_once(body,"status='captured-and-audited-fresh-v2-full-normal-profile-only',actual_processes=157","status='diagnosed-HST-first-invalid-only',actual_processes=3")
    return body


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and sys.argv[1:] in (['--prepare',PROFILE],['--profile',PROFILE]),'One standard-hosted small HST diagnostic only; no local simulation')
    if sys.argv[1]=='--prepare':
        native_capture.prepare(PROFILE);folder=ROOT/'out/admission-package-source'/PROFILE
        bootstrap=folder/'hst-bootstrap.sh';bootstrap.write_text(replace_once((folder/'physics-v2-bootstrap.sh').read_text(),'Tests/Production/PhysicsV2/native_capture.py','Tests/Production/PhysicsV2/hst_fpe.py'))
        network=folder/'hst-network.sh';network.write_text(replace_once((folder/'physics-v2-network.sh').read_text(),'physics-v2-bootstrap.sh','hst-bootstrap.sh'))
        generated=folder/'hst-generated.py';generated.write_text(prepared_body())
        files=[Path(__file__).resolve(),bootstrap,network,generated]
        (folder/'hst-before.sha256').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files));return
    try:exec(compile(prepared_body(),str(HERE/'hst_fpe.py'),'exec'),{'__name__':'__main__','__file__':str(HERE/'hst_fpe.py')})
    finally:
        if OUTPUT.exists():pack(ROOT,{p for p in OUTPUT.rglob('*') if p.is_file() or p.is_symlink()},OUTPUT/'diagnostic-raw.tar.gz',OUTPUT/'diagnostic-raw-index.json')


if __name__=='__main__':main()
