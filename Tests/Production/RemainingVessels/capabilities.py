"""Read actual SDK capabilities and prove the passive observer leaves the app unchanged.

Sixty-frame selections are diagnostics. They cannot satisfy complete stock,
persistence, interaction, production admission or final candidate gates.
"""
import argparse
import concurrent.futures
import importlib.util
import math
import os
from pathlib import Path,PureWindowsPath
import subprocess
import sys
import traceback
from types import SimpleNamespace

from lifetimes import (HERE,ROOT,prepare,inspect_world,DIAGNOSTICS,OwnedProcess,Compositor,build_identity,
                       atomic_json,load,require,sha,rows,data_inputs)
sys.path.insert(0,str(HERE.parent/'Client'))
from compare_client import image_ssim

FIELDS=('version','enable_focus','empty_mass','size','pmix','pmiy','pmiz','csx','csy','csz',
        'meshes','thrusters','propellants','docks','parents','children','xpdr')
PORTS={'stock-vessel-docks.csv':('object','index'),
       'stock-vessel-attachments.csv':('object','to_parent','index')}


def observer_source_control(body=None):
    baseline='e0204d51e3809cbf63e59c7b79d1806bf42cc4c2'
    name='Tests/Production/RemainingVessels/NativeProbe.cpp'
    original=subprocess.check_output(['git','-C',str(ROOT),'show',baseline+':'+name])
    wait=b'    std::this_thread::sleep_for(std::chrono::milliseconds(120));\n'
    require(original.count(wait)==1,'Original passive observer delay differs')
    expected=original.replace(wait,b'#ifndef ORBITER_NATIVE_FAST_CAPABILITY_DIAGNOSTIC\n'+wait+b'#endif\n')
    require((HERE/'NativeProbe.cpp').read_bytes() if body is None else body,
            'Passive observer source missing')
    require(((HERE/'NativeProbe.cpp').read_bytes() if body is None else body)==expected,
            'Capability observer changed original getters, forwarding or operations')
    for relative in ('StockVessels/Observation.h','RemainingStock/Details.h'):
        current=HERE.parent/relative
        require(current.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',
            baseline+':Tests/Production/'+relative]),'Original public SDK observation operations changed')
    return dict(status='passed-exact-passive-observer-with-diagnostic-delay-toggle-only',baseline=baseline,
                source_sha256=sha(HERE/'NativeProbe.cpp'))


def initial(records):
    return [r for r in records if r['tick']=='0']


def compare_capabilities(native,windows,expected,budgets):
    left=initial(rows(Path(native)/'stock-vessel-state.csv'))
    right=initial(rows(Path(windows)/'stock-vessel-state.csv'))
    require(len(left)==len(right)==len(expected) and
            {r['object']:r['class'] for r in left}==expected and
            {r['object']:r['class'] for r in right}==expected,
            'Complete original capability roster differs')
    reference={r['object']:r for r in right};result={}
    for row in left:
        other=reference[row['object']]
        for key in FIELDS:
            require(math.isfinite(float(row[key])) and math.isfinite(float(other[key])) and
                    float(row[key])==float(other[key]),
                    'Actual SDK capability differs: '+row['object']+'/'+key)
        result[row['object']]={k:row[k] for k in ('class',*FIELDS)}
    for filename,keys in PORTS.items():
        a=initial(rows(Path(native)/filename));b=initial(rows(Path(windows)/filename))
        key=lambda r:tuple(r[k] for k in keys)
        indexed={key(r):r for r in b}
        require(len(a)==len(b)==len(indexed) and {key(r) for r in a}==set(indexed),
                'Actual capability port inventory differs: '+filename)
        for row in a:
            other=indexed[key(row)]
            require(set(row)==set(other) and None not in row and None not in row.values(),
                    'Incomplete capability port row')
            for field in row:
                if field in keys or field=='tick':continue
                if field in ('x','y','z','dx','dy','dz','rx','ry','rz'):
                    limit=budgets['position_m'] if field in ('x','y','z') else budgets['rotation_rad']
                    require(abs(float(row[field])-float(other[field]))<=limit,
                            'Actual capability port geometry differs: '+filename+'/'+field)
                else:require(row[field]==other[field],'Actual capability port identity differs: '+field)
    return result


def reference(args,cases,identity,original_data,guards):
    spec=importlib.util.spec_from_file_location('capability_original_runtime',HERE.parent/'RemainingStockRepaired/audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    parent=load(args.windows_reference/'capture.json')
    require(parent['protocol']==audit.protocols.V2 and parent['status'] in
            ('captured-diagnostic-only','captured-awaiting-independent-audit') and not parent['failures'] and
            parent['configuration']==identity['configuration'] and parent['math_profile']==identity['math_profile'] and
            parent['original_application_and_sdk_source']==audit.BASE and
            parent['actual_original_simulation_data']==original_data and
            {c['id'] for c in cases}<=set(parent['cases']), 'Matching complete original Windows reference required')
    build,runtime=audit.runtime_variant(args.windows_build,parent['producer_commit'],identity['configuration'],
                                      args.preserved,audit.protocols.V2)
    config=audit.capture.settings(audit.protocols.V2)
    for directory in (args.windows_build,args.preserved):
        guards.update({str(p):sha(p) for p in directory.rglob('*') if p.is_file()})
    guards[str(args.windows_reference/'capture.json')]=sha(args.windows_reference/'capture.json')
    checked={}
    for case in cases:
        actual=[]
        require(len(parent['cases'][case['id']]['runs'])==2,'Both original Windows repetitions required')
        for repeat in range(1,args.repeats+1):
            folder=args.windows_reference/(case['id']+'-'+str(repeat))
            recorded=parent['cases'][case['id']]['runs'][repeat-1]
            for name,value in recorded['files_sha256'].items():
                require(sha(folder/name)==value,'Original Windows reference file changed: '+name)
                guards[str(folder/name)]=value
            value=audit.capture.inspect_artifacts(folder,case,config)
            require(all(recorded[k]==v for k,v in value.items()),'Original Windows observation differs')
            wanted={'Orbiter.exe':build['runtime_files_sha256']['Orbiter.exe']}
            wanted.update({PureWindowsPath(config['classes'][kind]['original_module']).name:
                build['runtime_files_sha256'][config['classes'][kind]['original_module']]
                for kind in set(case['declared_vessels'].values()) if config['classes'][kind]['module']})
            for name,checksum in wanted.items():
                matches=[m for m in recorded['loaded_modules'] if PureWindowsPath(m['path']).name.casefold()==name.casefold()]
                require(len(matches)==1 and matches[0]['sha256']==checksum,'Actual original mapped application/module differs: '+name)
            actual.append(dict(folder=str(folder),record=recorded))
        checked[case['id']]=actual
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,value in audit.verifier_inputs().items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(__import__('hashlib').sha256(body).hexdigest()==value,'Capability reference reader is not immutable: '+name)
        guards[str(ROOT/name)]=value
    return checked,runtime,config


def inspect_lane(folder,case,identity,observer):
    receipt=load(folder/'process-receipt.json');invocation=load(folder/'invocation.json');argv=invocation['argv']
    require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0,
            'Actual capability simulator did not exit cleanly')
    actual=[r for r in receipt['owned_process_identities'] if r['pid']==receipt['actual_collector_pid']]
    require(len(actual)==1 and actual[0]['argv']==argv and actual[0]['start_ticks']>0,
            'Actual capability PID/start/argv receipt differs')
    require(sha(argv[0])==invocation['executable_sha256'] and
            sha(argv[argv.index('--scenario')+1])==invocation['scenario_sha256'], 'Capability executable/scene changed')
    require(sha(folder/'Orbiter.cfg')==invocation['config_sha256'] and
            sha(folder/'replay.csv')==invocation['replay_sha256'] and
            (folder/'replay.csv').read_bytes()==b'tick,phase,action,value\n',
            'Capability startup configuration or empty input schedule changed')
    env=invocation['environment']
    require(env['ASAN_OPTIONS']=='detect_leaks=1:fast_unwind_on_malloc=0' and env['LSAN_OPTIONS']=='' and
            env['UBSAN_OPTIONS']=='halt_on_error=1:print_stacktrace=1' and
            (env['LD_PRELOAD'] is None if observer is None else env['LD_PRELOAD'].endswith(':'+str(observer))),
            'Actual capability sanitizer/preload controls differ')
    require(not any(v in (folder/'console.log').read_text(errors='replace') for v in DIAGNOSTICS),
            'Capability runtime/sanitizer diagnostic')
    require(load(folder/'numerics.json')['math']=='amd-6121d02-'+
            ('sse2' if identity['math_profile']=='sse2' else 'fma3'),'Actual capability math mode differs')
    world=inspect_world(folder,case['declared_vessels'])
    if observer:
        require((folder/'stock-vessel-complete.txt').read_text().strip()=='60','Capability observer ended early')
        mapped=(folder/'observer-loaded-maps.txt').read_text()
        require(str(observer) in mapped and sha(observer)==invocation['observer_sha256'],
                'Actual capability observer mapping differs')
        observed=rows(folder/'stock-vessel-state.csv')
        require(len(observed)==61*len(case['declared_vessels']) and
                {int(r['tick']) for r in observed}==set(range(61)), 'Capability SDK trace incomplete')
    else:require(not (folder/'stock-vessel-state.csv').exists(),'Observer-off lane unexpectedly observed')
    return world


def compile_command(args,identity,probe):
    return [identity['compiler'],'-std=c++17','-fPIC','-shared','-Wl,--no-undefined',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-DORBITER_NATIVE_FAST_CAPABILITY_DIAGNOSTIC',
        '-I'+str(args.owner/'Orbitersdk/include'),'-I'+str(args.owner/'Src/Orbiter'),
        '-I'+str(args.build/'native-sdk'),str(HERE/'NativeProbe.cpp'),'-L'+str(args.build),
        '-Wl,-rpath,'+str(args.build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)]


def audit(path):
    path=Path(path).resolve();report=load(path)
    require(observer_source_control()==report['observer_source_control'],'Passive capability source control differs')
    require(report['protocol']=='remaining-stock-capability-controls-v1' and
            report['status']=='captured-capability-controls-awaiting-independent-audit' and
            report['diagnostic_only'] is True and not report['failures'] and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False and
            report['repeats'] in (1,2),'Incomplete or incorrectly scoped capability capture')
    args=SimpleNamespace(**{k:Path(v) for k,v in report['runtime'].items()},
                         owner=Path(report['runtime_owner']),repeats=report['repeats'])
    build=load(args.build_record);identity=build_identity(args.build/'orbiter-production',args.build/'NativeModules',
                         args.build_record,build['source_base'],args.owner)
    require(identity==report['runtime_identity'] and identity['sanitizer_linked'],'Capability runtime identity differs')
    require(all(sha(p)==v for p,v in report['guarded_files_sha256'].items()),'Guarded capability inputs changed')
    config=load(HERE.parent/'RemainingStock/cases.json')
    cases=[c for c in config['cases'] if c['id'] in report['cases_requested']]
    require([c['id'] for c in cases]==report['cases_requested'] and
            len(cases)==len(set(report['cases_requested']))==len(report['cases']),'Capability selection incomplete')
    references,runtime,windows_config=reference(args,cases,identity,report['actual_original_data'],{})
    require(runtime==report['original_runtime'] and data_inputs.inspect(args.data,args.planets)==
            report['actual_original_data'],'Original capability runtime or data changed')
    probe=path.parent/'capability-probe.so'
    require(sha(probe)==report['observer_sha256'] and load(path.parent/'observer-build-command.json')==
            compile_command(args,identity,probe),'Capability observer binary/build differs')
    results={}
    for case in cases:
        runs=report['cases'][case['id']]['runs'];require(len(runs)==report['repeats'],'Capability repeat missing')
        verified=[]
        for repeat,record in enumerate(runs,1):
            on=path.parent/(case['id']+'-'+str(repeat)+'-on');off=path.parent/(case['id']+'-'+str(repeat)+'-off')
            for enabled,folder in [(False,off),(True,on)]:
                require(inspect_lane(folder,case,identity,probe if enabled else None)==record['lanes']['on' if enabled else 'off'],
                        'Closed capability lane changed')
            for name in ('flight-state.csv','production-state.csv','camera.csv','flight-animations.csv','flight-controls.csv','thrust-state.csv'):
                require((off/name).read_bytes()==(on/name).read_bytes(),'Capability observation changed '+name)
            score=image_ssim((off/'scene.rgba').read_bytes(),(on/'scene.rgba').read_bytes(),1280,720)
            require(score>=windows_config['image_ssim_minimum'] and score==record['observer_equivalence_ssim'],
                    'Capability observer frame equivalence differs')
            caps=compare_capabilities(on,references[case['id']][repeat-1]['folder'],case['declared_vessels'],windows_config['budgets'])
            require(caps==record['actual_capabilities'],'Re-read actual capabilities differ')
            verified.append(dict(actual_capabilities=caps,observer_equivalence_ssim=score))
        results[case['id']]=verified
    return dict(status='audited-original-Windows-native-capabilities-and-observer-controls-diagnostic-only',
        capture_sha256=sha(path),runtime_identity=identity,cases=results,repeats=report['repeats'],
        actual_processes=len(cases)*report['repeats']*2,owning_bytes_unchanged=True,
        auditor_sources_sha256={str(p):sha(p) for p in (Path(__file__),HERE/'lifetimes.py')},
        historical_original_launch_receipts_reconstructed=False,diagnostic_only=True,
        native_admission_qualified=False,phase6_complete=False)


def capture(args):
    source_control=observer_source_control()
    extra=[Path(__file__),HERE/'NativeProbe.cpp',HERE.parent/'StockVessels/Observation.h',
           HERE.parent/'RemainingStock/Details.h',HERE.parent/'Client/compare_client.py']
    config,cases,build,identity,executable,guards,producer,original_data=prepare(args,extra)
    references,original_runtime,windows_config=reference(args,cases,identity,original_data,guards)
    args.output.mkdir(parents=True)
    probe=args.output/'capability-probe.so'
    command=compile_command(args,identity,probe)
    atomic_json(args.output/'observer-build-command.json',command)
    with (args.output/'observer-build.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    guards[str(probe)]=sha(probe)
    report=dict(protocol='remaining-stock-capability-controls-v1',status='running',runtime_identity=identity,
        runtime_owner=str(args.owner),producer_commit=producer,observer_sha256=sha(probe),
        observer_source_control=source_control,
        runtime={name:str(getattr(args,name)) for name in ('build','build_record','assets','data','planets',
                                                         'windows_reference','windows_build','preserved')},
        guarded_files_sha256=guards,actual_original_data=original_data,original_runtime=original_runtime,
        cases_requested=[c['id'] for c in cases],repeats=args.repeats,cases={},failures={},diagnostic_only=True,
        native_admission_qualified=False,phase6_complete=False)
    manifest=args.output/'capabilities.json';atomic_json(manifest,report)
    asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()

    def run_case(case):
        results=[]
        with Compositor(args.compositor_tools,args.output/(case['id']+'-compositor'),1,'gl',repeat_rate=0) as display:
            for repeat in range(1,args.repeats+1):
                lanes={}
                for enabled in (False,True):
                    folder=args.output/(case['id']+'-'+str(repeat)+'-'+('on' if enabled else 'off'));folder.mkdir()
                    cfg=(HERE.parent/'NativeScene/Orbiter.cfg').read_text()
                    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                        require(cfg.count(line)==1,'Unexpected original propagator fixture');cfg=cfg.replace(line,'')
                    (folder/'Orbiter.cfg').write_text(cfg+'\nMenubarMode = 1\nInfobarMode = 1\n')
                    (folder/'replay.csv').write_text('tick,phase,action,value\n')
                    argv=list(map(str,[executable,'--assets',args.assets,'--data',args.data,'--planets',args.planets,
                        '--modules',args.build/'NativeModules','--scenario',args.assets/case['scenario_entry_point'],
                        '--config',folder/'Orbiter.cfg','--evidence',folder,'--save',folder/'saved.scn',
                        '--frames','60','--fixed-step','0.015625','--fixed-ui-clock','--capture-time','0.78125',
                        '--replay',folder/'replay.csv','--run']))
                    env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                        LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[args.build,*args.library])),
                        ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                        UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    env.pop('LD_PRELOAD',None)
                    if enabled:env['LD_PRELOAD']=asan+':'+str(probe)
                    atomic_json(folder/'invocation.json',dict(argv=argv,executable_sha256=sha(executable),
                        scenario_sha256=sha(args.assets/case['scenario_entry_point']),observer_sha256=sha(probe) if enabled else None,
                        config_sha256=sha(folder/'Orbiter.cfg'),replay_sha256=sha(folder/'replay.csv'),
                        environment={k:env.get(k) for k in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS','LD_PRELOAD',
                                                          'LD_LIBRARY_PATH','LIBDECOR_PLUGIN_DIR')}))
                    with (folder/'console.log').open('w') as log:
                        owned=OwnedProcess(argv,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
                        try:owned.process.wait(timeout=300)
                        finally:atomic_json(folder/'process-receipt.json',owned.cancel())
                    lanes['on' if enabled else 'off']=inspect_lane(folder,case,identity,probe if enabled else None)
                off=args.output/(case['id']+'-'+str(repeat)+'-off');on=args.output/(case['id']+'-'+str(repeat)+'-on')
                for name in ('flight-state.csv','production-state.csv','camera.csv','flight-animations.csv','flight-controls.csv','thrust-state.csv'):
                    require((off/name).read_bytes()==(on/name).read_bytes(),'Passive capability observation changed '+name)
                score=image_ssim((off/'scene.rgba').read_bytes(),(on/'scene.rgba').read_bytes(),1280,720)
                require(score>=windows_config['image_ssim_minimum'],'Passive observation changed the full frame beyond existing budget')
                caps=compare_capabilities(on,references[case['id']][repeat-1]['folder'],case['declared_vessels'],windows_config['budgets'])
                results.append(dict(lanes=lanes,observer_equivalence_ssim=score,actual_capabilities=caps,
                                    windows_reference=str(references[case['id']][repeat-1]['folder'])))
        return dict(runs=results)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending={pool.submit(run_case,case):case['id'] for case in cases}
        for future in concurrent.futures.as_completed(pending):
            name=pending[future]
            try:report['cases'][name]=future.result()
            except BaseException as error:report['failures'][name]=dict(error=str(error),traceback=traceback.format_exc())
            atomic_json(manifest,report);print(name,'failed' if name in report['failures'] else 'capabilities and observer controls captured',flush=True)
    require(all(sha(p)==value for p,value in guards.items()),'Capability source/runtime/reference/provider inputs changed')
    require(data_inputs.inspect(args.data,args.planets)==original_data,'Original capability simulation data changed')
    report['status']='failed' if report['failures'] else 'captured-capability-controls-awaiting-independent-audit'
    atomic_json(manifest,report);require(not report['failures'],'Capability failures retained; no class admission')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'Fresh independent capability audit required')
    atomic_json(args.output,audit(args.capture))
