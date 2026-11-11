#!/usr/bin/env python3
"""Test explicit contact-retry and initialization physics prototypes; preserve the frozen application and every guard."""
import hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time,zipfile
from contracts import ROOT,atomic_json,load,require,sha
from frozen_admission_api import candidate,hosted
from hosted_normal_admission import prepare_package,prepare_snapshot
import capture_hosted_native_writer_runtime as original_setup
from inspect_rejection_cpp_abi import abi_tokens,host_macros
import restore_rejection_sdk_header as original_sdk
from rejection_input_bundle import pack
from processes import OwnedProcess

PROFILE='Debug-automatic'
SOURCE='ccc02c8a34bd1f227624d8778a141e8736ae8111'
HERE=Path(__file__).resolve().parent
FOLDER=ROOT/'out/contact-component-trial'/PROFILE
BEFORE='\tAddSurfaceForces (&F, &M, &state, tfrac, dt); // add ground contact forces and moments'
AFTER='\tcollision_during_update |=\n\t'+BEFORE
CALL='vlist[comp].vessel->AddSurfaceForces (&Fcomp, &Mcomp, &scomp, tfrac, dt)'
FIXED_CALL=CALL[:-1]+', update_with_collision)'
INIT_BEFORE='\tsp.is_in_atm        = false;'
INIT_AFTER=INIT_BEFORE+'\n\tUpdateProxies();\n\tUpdateSurfParams();'


def method(body,signature):
    start=body.index(signature);opening=body.index('{',start);level=1;end=opening+1
    while level:
        require(end<len(body),'Complete original method required')
        if body[end]=='{':level+=1
        elif body[end]=='}':level-=1
        end+=1
    return body[start:end]+'\n'


def source_variant(mode):
    require(mode in ('original-methods','collision-retry-prototype','contact-initialization-prototype'),'Exact component trial mode required')
    path=ROOT/'Src/Orbiter/SuperVessel.cpp';body=path.read_text()
    require(path.read_bytes()==subprocess.check_output(['git','show',SOURCE+':Src/Orbiter/SuperVessel.cpp'],cwd=ROOT),
            'Frozen production source must remain byte-identical; do not update its original conservation guard')
    first=method(body,'void SuperVessel::GetIntermediateMoments (');second=method(body,'bool SuperVessel::AddSurfaceForces (')
    require(first.count(BEFORE)==second.count(CALL)==1,'Exact original dispatch/contact anchors required')
    third=method(body,'void SuperVessel::SetDefaultState ()')
    require(third.count(INIT_BEFORE)==1,'Exact original assembly default-state anchor required')
    if mode in ('collision-retry-prototype','contact-initialization-prototype'):
        first=first.replace(BEFORE,AFTER,1);second=second.replace(CALL,FIXED_CALL,1)
    if mode=='contact-initialization-prototype':third=third.replace(INIT_BEFORE,INIT_AFTER,1)
    original=first+second+third
    functions=[]
    for i,code in enumerate((first,second,third)):
        opening=code.index('{')+1;functions.append(code[:opening]+'\n    contact_trial_call('+str(i)+');'+code[opening:])
    prefix=r'''#include "SuperVessel.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
namespace {
std::atomic<bool> seen[3]{};
void contact_trial_call(unsigned index) {
    if(!seen[index].exchange(true))if(const char* path=std::getenv("ORBITER_CONTACT_TRIAL_RECEIPT")) {
        if(auto* out=std::fopen(path,"a")) {
            std::fputs(index==0?"moments\n":index==1?"surface\n":"defaults\n",out);std::fclose(out);
        }
    }
}
}
'''
    return prefix+'\n'.join(functions),dict(mode=mode,production_source=SOURCE,production_file_sha256=sha(path),
        complete_method_bodies_sha256=hashlib.sha256(original.encode()).hexdigest(),production_source_modified=False,
        changes=[] if mode=='original-methods' else ['Retain assembly collision detection for existing integration retry','Apply component ground forces only when existing contact-retry policy enables them']+(['Initialize assembly proxy and actual surface state after original defaults clear them'] if mode=='contact-initialization-prototype' else []),
        first_call_observation_only=True,qualification_granted=False)


def component_abi(engine,output):
    # The retained package omitted this generated SDK input. Use the existing
    # complete source/cache/binary topology proof before invoking the compiler.
    restoration=original_sdk.restore(PROFILE,engine.parent/'build.json',output/'original-SDK-header-restoration.json')
    header=engine/'native-sdk/OrbiterNativeBuild.h'
    require(sha(header)==restoration['header_sha256'],'Actual restored original SDK input differs')
    (output/'OrbiterNativeBuild.h').write_bytes(header.read_bytes())
    tokens=abi_tokens((engine/'liborbiter_production_boundary.so').read_bytes());macros=host_macros(header,output)
    require(len(tokens)==1 and macros['actual_cpp_abi']==tokens[0],'Actual host compiler and untouched native SDK/engine ABI must match')
    return restoration,tokens[0],macros


def prepare():
    hosted();lock=candidate();prepare_package(PROFILE,lock);prepare_snapshot(PROFILE)
    base=ROOT/'out/admission-package-source'/PROFILE
    for source,old,new,target in [
        (base/'network.sh','Tests/Production/Closeout/prepare_hosted_normal_admission.sh',
         'out/admission-package-source/'+PROFILE+'/contact-bootstrap.sh',base/'contact-network.sh'),
        (HERE/'prepare_hosted_normal_admission.sh','Tests/Production/Closeout/hosted_normal_admission.py --profile',
         'Tests/Production/Closeout/hosted_contact_component_trial.py --profile',base/'contact-bootstrap.sh')]:
        body=source.read_text();require(body.count(old)==1,'Exact original hosted setup anchor required');target.write_text(body.replace(old,new,1))
    output=ROOT/'out/contact-component-compiler';output.mkdir()
    engine=ROOT/'out/phase6-hosted-native'/PROFILE/'engine';header=engine/'native-sdk/OrbiterNativeBuild.h'
    restoration,engine_abi,macros=component_abi(engine,output)
    report=dict(source=os.environ['GITHUB_SHA'],candidate_id=lock['id'],actual_engine_cpp_abi=engine_abi,host_macros=macros,original_omitted_SDK_header=restoration,variants={},frozen_application_rebuilt=False,original_source_guard_modified=False,qualification_granted=False)
    for mode in ('original-methods','contact-initialization-prototype'):
        body,record=source_variant(mode);cpp=output/(mode+'.cpp');cpp.write_text(body);library=output/(mode+'.so')
        argv=['/usr/bin/c++','-std=c++17','-O0','-fPIC','-shared','-Wl,--no-undefined','-fsanitize=address,undefined','-fno-omit-frame-pointer',
              '-DORBITER_PRODUCTION_SHARED','-DORBITER_NATIVE_BUILD_CONFIGURATION="Debug"','-I'+str(ROOT/'Src/Orbiter'),
              '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(engine/'native-sdk'),str(cpp),'-L'+str(engine),'-Wl,-rpath,'+str(engine),
              '-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(library)]
        log=output/(mode+'-compiler.log')
        with log.open('wb') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);code=child.wait(timeout=300)
        record.update(argv=argv,actual_pid=child.pid,actual_returncode=code,cpp_sha256=sha(cpp),compiler_log_sha256=sha(log));report['variants'][mode]=record
        atomic_json(output/'compiler.json',report)
        if code:print(log.read_text(errors='replace')[-10000:],flush=True)
        require(code==0,'Actual isolated component compilation failed; all original files remain untouched')
        record['library_sha256']=sha(library);atomic_json(output/'compiler.json',report)
    files=(header,base/'contact-network.sh',base/'contact-bootstrap.sh',HERE/'prepare_hosted_normal_admission.sh',
           *[p for p in output.iterdir() if p.is_file()])
    (base/'contact-before.sha256').write_text((base/'before.sha256').read_text()+''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files))


def original_case_control(operation,name,out,code=0):
    program=r'''
import sys,pathlib,json
sys.path.insert(0,str(pathlib.Path('Tests/Production/StockScenarios').resolve()))
import run as original
operation,name,directory,returncode=sys.argv[1:];out=pathlib.Path(directory)
if operation=='stage':
 body=original.configuration(False);(out/'Orbiter.cfg').write_text(body);(out/'staged-Orbiter.cfg').write_text(body)
else:
 report=original.corpus(pathlib.Path('out/native-stock-assets'),pathlib.Path('out/phase6-hosted-native/Debug-automatic/engine/NativeModules'))
 case=report['cases'][name];case['startup_configuration_policy']='original-propagators-v1'
 result=original.inspect(out,case,int(returncode),scenario=name,profile='Debug-automatic')
 (out/'original-inspection.json').write_text(json.dumps(result,indent=2)+'\n')
'''
    subprocess.run([sys.executable,'-B','-c',program,operation,name,str(out),str(code)],cwd=ROOT,check=True)


def run_cases(output,providers,mesa,report,save):
    sys.path.insert(0,str(ROOT/'Tests/Production/WaylandInput'));from compositor import Compositor
    build=ROOT/'out/phase6-hosted-native'/PROFILE;engine=build/'engine';before=load(build/'build.json')
    compiler=load(ROOT/'out/contact-component-compiler/compiler.json');lock=candidate()
    require(before['source_base']==SOURCE and compiler['candidate_id']==lock['id'],'Exact unchanged frozen source/binary base required')
    require(sha(engine/'native-sdk/OrbiterNativeBuild.h')==compiler['original_omitted_SDK_header']['header_sha256'],'Original reconstructed SDK input changed after compilation')
    # Existing independent diagnostic ZIP preserves the original partial bytes; no bulk transfer leaves GitHub.
    archive=ROOT/'out/contact-trial-prior/producer.zip';api=load(ROOT/'out/contact-trial-prior/api.json');a=api['artifact']
    require(a['id']==13827115523 and a['size_in_bytes']==archive.stat().st_size==324434 and
            a['digest']=='sha256:18da8a441c1ed94248650f858a89b6836613240c4edc8516f2e24142b945cc0d' and 'sha256:'+sha(archive)==a['digest'],
            'Exact original independently verified failure diagnostic ZIP required')
    expected={};cases=load(HERE/'failed-normal-admission-v4.lock.json')['failed_cases']
    with zipfile.ZipFile(archive) as z:
        inspection=z.read(next(n for n in z.namelist() if n.endswith('/inspection.json')));inspection=json.loads(inspection)
        require(inspection['original_source']=='2cf4163dd55cab88337bcdf5890a4a34c1b3334b' and inspection['source_run_id']==42926670117 and inspection['profile']==PROFILE,'Original failed normal source/profile required')
        for name,number in cases.items():
            body=z.read(next(n for n in z.namelist() if n.endswith('/original-partials/'+number+'/flight-state.csv')))
            require(hashlib.sha256(body).hexdigest()==inspection['selected_unchanged_files'][number+'/flight-state.csv']['sha256'],'Original exact partial trace changed')
            expected[name]=hashlib.sha256(body).hexdigest()
    report.update(candidate_id=lock['id'],physics_component_trial=True,frozen_application_source=SOURCE,actual_application_rebuilt=False,original_source_guards_unchanged=True,trials={});save()
    with Compositor(providers/'compositor',output/'trial-compositor') as display:
        libraries=[engine,*(providers/f/'install/lib/x86_64-linux-gnu' for f in ('fontconfig-candidate','gdk-candidate')),mesa/'install/lib/x86_64-linux-gnu']
        common=dict(display.environment,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'),LIBGL_ALWAYS_SOFTWARE='1',
            GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LD_LIBRARY_PATH=':'.join(map(str,libraries)),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
            LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        asan=Path('/usr/lib/x86_64-linux-gnu/libasan.so.8');require(asan.is_file(),'Original declared ASan runtime required')
        for mode in ('unchanged-application','original-methods','contact-initialization-prototype'):
            results={};report['trials'][mode]=results
            for name,number in cases.items():
                folder=output/(mode+'-'+number);folder.mkdir();original_case_control('stage',name,folder)
                argv=[str(engine/'orbiter-production'),'--assets',str(ROOT/'out/native-stock-assets'),'--data',str(ROOT/'out/native-stock-data'),
                      '--planets',str(ROOT/'out/native-stock-planets'),'--modules',str(engine/'NativeModules'),'--config',str(folder/'Orbiter.cfg'),
                      '--scenario',str(ROOT/'out/native-stock-assets/Scenarios'/name),'--evidence',str(folder),'--save',str(folder/'saved.scn'),
                      '--frames','60','--fixed-step','.25','--run']
                env=dict(common);library=None
                if mode!='unchanged-application':
                    library=ROOT/'out/contact-component-compiler'/(mode+'.so');require(sha(library)==compiler['variants'][mode]['library_sha256'],'Exact declared component trial bytes required')
                    env.update(LD_PRELOAD=str(asan)+':'+str(library),ORBITER_CONTACT_TRIAL_RECEIPT=str(folder/'actual-component-calls.txt'))
                atomic_json(folder/'invocation.json',argv)
                with (folder/'console.log').open('w') as console:
                    process=OwnedProcess(argv,cwd=folder,env=env,stdout=console,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+180
                    try:
                        while process.process.poll() is None:
                            process.discover()
                            if time.monotonic()>deadline:raise subprocess.TimeoutExpired(argv,180)
                            time.sleep(.1)
                    finally:
                        if process.process.poll() is None:process.cancel()
                        atomic_json(folder/'process-receipt.json',process.receipt())
                    code=process.process.returncode
                original_case_control('audit',name,folder,code);actual=load(folder/'original-inspection.json')
                calls=(folder/'actual-component-calls.txt').read_text().splitlines() if (folder/'actual-component-calls.txt').is_file() else []
                trace=folder/'flight-state.csv';digest=sha(trace) if trace.is_file() else None
                results[name]=dict(actual_pid=process.process.pid,actual_exitcode=code,original_inspection=actual,flight_trace_sha256=digest,
                    original_partial_trace_sha256=expected[name],byte_identical_to_original_failure=(digest==expected[name]),actual_component_dispatches=calls,
                    component_library_sha256=sha(library) if library else None,physics_component_trial=True,normal_admission_qualified=False)
                save()
    require(display.process.returncode==0,'Owned compositor must exit normally')
    for mode,results in report['trials'].items():
        require(len(results)==4,'All four unchanged original scenes required in every trial mode')
        for item in results.values():
            if mode=='contact-initialization-prototype':require(item['original_inspection']['status']=='passed' and item['actual_exitcode']==0,'Proposed physics component did not pass the unchanged original scenario reader')
            else:require(item['original_inspection']['status']=='failed' and item['byte_identical_to_original_failure'],'Unchanged before component did not reproduce every exact original failed trace')
            if mode!='unchanged-application':require(set(item['actual_component_dispatches'])=={'moments','surface','defaults'},'All three actual method dispatches must be observed; no assumed interposition')
    require(candidate()==lock and all(sha(ROOT/n)==v for n,v in before['runtime_files_sha256'].items()),'Original frozen application/source bytes changed during trial')


def frozen_postflight(output):
    build=ROOT/'out/phase6-hosted-native'/PROFILE;record=load(build/'build.json')
    compiler=load(ROOT/'out/contact-component-compiler/compiler.json');changed=[]
    for name,digest in record['runtime_files_sha256'].items():
        if not (ROOT/name).is_file() or sha(ROOT/name)!=digest:changed.append(name)
    header=build/'engine/native-sdk/OrbiterNativeBuild.h'
    if sha(header)!=compiler['original_omitted_SDK_header']['header_sha256']:changed.append(str(header))
    for name,item in compiler['variants'].items():
        library=ROOT/'out/contact-component-compiler'/(name+'.so')
        if sha(library)!=item['library_sha256']:changed.append(str(library))
    source=ROOT/'Src/Orbiter/SuperVessel.cpp'
    if source.read_bytes()!=subprocess.check_output(['git','show',SOURCE+':Src/Orbiter/SuperVessel.cpp'],cwd=ROOT):changed.append(str(source))
    atomic_json(output/'frozen-postflight.json',dict(status='passed' if not changed else 'failed',changed=changed,candidate_id=candidate()['id'],original_runtime_files_checked=len(record['runtime_files_sha256']),original_production_source_unchanged=not changed,qualification_granted=False))
    require(not changed,'Original frozen bytes or explicitly declared prototype changed during diagnostic trial')


def prepared_body():
    body=original_setup.prepared_body()
    for old,new,count in [("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-explicit-assembly-contact-component-trial-v1'",1),
        ("ROOT/'out/hosted-native-writer'","ROOT/'out/contact-component-trial'",1),
        ("ROOT/'out/native-writer-container.json'","ROOT/'out/contact-component-container.json'",2)]:
        require(body.count(old)==count,'Every original provider setup anchor must remain exact');body=body.replace(old,new)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=");end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    body=body[:start]+"        from hosted_contact_component_trial import run_cases\n        run_cases(output,providers,mesa,report,save)\n"+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    require(body.count(old)==1,'Original completion source anchor required')
    return body.replace(old,"        report.update(status='validated-contact-initialization-physics-prototype-only',actual_processes=12,normal_admission_qualified=False,phase6_complete=False,original_source_guards_unchanged=True)",1)


if __name__=='__main__':
    hosted();require(sys.argv[1:] in (['--prepare',PROFILE],['--profile',PROFILE]),'Only one affected original Debug automatic component trial required')
    if sys.argv[1]=='--prepare':prepare()
    else:
        try:exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
        finally:
            if FOLDER.is_dir():
                try:frozen_postflight(FOLDER)
                finally:pack(ROOT,{p for p in FOLDER.rglob('*') if p.is_file() or p.is_symlink()},FOLDER/'trial-raw.tar.gz',FOLDER/'trial-raw-index.json')
