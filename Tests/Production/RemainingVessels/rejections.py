"""Actual negative loader/class controls in the existing remaining-vessel runner."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from lifetimes import (HERE, ROOT, Compositor, OwnedProcess, atomic_json, load,
                       prepare, require, sha, ships)

META = ('Native module SDK build mismatch', 'Native module C++ toolchain/ABI mismatch',
        'Native module architecture mismatch', 'Native module bootstrap version mismatch',
        'Native module descriptor size mismatch', 'Native module kind mismatch',
        'Native module lifecycle entry is missing')
BAD = ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
       'AddressSanitizer:DEADLYSIGNAL', 'Production teardown:',
       'LeakSanitizer has encountered', 'Suppressions used:', 'Lua error:',
       'REJECTION_FIXTURE_INITIALIZE_CALLED')
ENV = dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0', LSAN_OPTIONS='',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1', LD_PRELOAD=None,
           LD_DEBUG='files')


def controls(config, cases):
    selected = {}
    for family in config['required_classes']:
        selected[family] = next(c for c in cases if family in c['declared_vessels'].values())
    result = []
    for family, case in selected.items():
        for variant in ('unknown-class', 'foreign-factory', 'missing-module', 'generic-fallback'):
            if variant in ('missing-module', 'generic-fallback') and not config['classes'][family]['module']:
                continue
            result.append(dict(id=family+'-'+variant, family=family, case=case['id'], variant=variant))
    hst = selected['HST']['id']
    result.extend(dict(id='HST-metadata-'+str(i),family='HST',case=hst,variant='metadata',metadata=i)
                  for i in range(len(META)))
    result.extend(dict(id='HST-'+v,family='HST',case=hst,variant=v)
                  for v in ('missing-query', 'windows-pe'))
    return result


def inspect_case(folder, expected):
    invocation = load(folder/'invocation.json')
    require(invocation['control'] == expected and invocation['environment'] == ENV,
            'Actual negative input/environment differs')
    require(all(sha(p) == v for p, v in invocation['guarded_files_sha256'].items()),
            'Executed negative input/runtime bytes changed')
    receipt = load(folder/'process-receipt.json')
    require(receipt['terminal'] is True and receipt['cancelled'] is False and
            receipt['actual_returncode'] == 1 and receipt['actual_collector_pid'] > 0 and
            receipt['owned_process_identities'][0]['argv'] == invocation['argv'],
            'Actual negative simulator identity/exit differs')
    console = (folder/'console.log').read_text(errors='replace')
    require(invocation['expected_error'].lower() in console.lower() and
            not any(marker in console for marker in BAD),
            'Intended rejection missing, fixture initializer called, or sanitizer failure')
    life = load(folder/'graphics-lifecycle.json')
    require(life == dict(rendered_frames=0,successful_presents=0,context_deleted=True),
            'Negative control presented a frame or failed graphics cleanup')
    require(not (folder/'saved.scn').exists(), 'Rejected input unexpectedly saved a world')
    return dict(actual_pid=receipt['actual_collector_pid'],actual_exitcode=1,lifecycle=life,
                input_roster=invocation['input_roster'],expected_error=invocation['expected_error'],
                files_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()})


def audit(path):
    path=Path(path).resolve();report=load(path)
    require(report['status']=='passed-negative-loader-and-class-controls-only' and
            report['diagnostic_only'] is True and report['native_admission_qualified'] is False and
            report['phase6_complete'] is False and not report['failures'], 'Closed rejection control required')
    require(all(sha(p)==v for p,v in report['guarded_files_sha256'].items()),
            'Rejection owning source/runtime/original resources changed')
    config=load(HERE.parent/'RemainingStock/cases.json')
    cases=[c for c in config['cases'] if c['id'] in report['cases_requested']]
    expected=controls(config,cases)
    require(report['controls_requested']==expected and set(report['controls'])=={v['id'] for v in expected},
            'Incomplete family/loader rejection coverage')
    actual={v['id']:inspect_case(path.parent/v['id'],v) for v in expected}
    require(actual==report['controls'],'Recomputed negative runtime observation differs')
    return dict(status='audited-negative-loader-and-class-controls-only',
                capture_sha256=sha(path),runtime_identity=report['runtime_identity'],
                families=config['required_classes'],actual_processes=len(actual),
                controls=actual,owning_bytes_unchanged=True,sanitizer_suppressions=False,
                diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)


def capture(args):
    config,cases,build,identity,executable,guards,producer,original_data=prepare(args,(Path(__file__),))
    expected=controls(config,cases)
    pe=args.rejection_windows_dll
    require(pe.read_bytes()[:2]==b'MZ','Actual preserved Windows PE input required')
    guards[str(pe)]=sha(pe)
    args.output.mkdir(parents=True)
    fixtures=args.output/'fixtures';fixtures.mkdir()
    report=dict(protocol='remaining-stock-rejections-v1',status='running',producer_commit=producer,
                runtime_identity=identity,runtime_owner=str(args.owner),actual_original_data=original_data,
                guarded_files_sha256=guards,cases_requested=[c['id'] for c in cases],
                controls_requested=expected,controls={},failures={},diagnostic_only=True,
                native_admission_qualified=False,phase6_complete=False)
    manifest=args.output/'rejections.json';atomic_json(manifest,report)
    for i in range(len(META)):
        argv=[identity['compiler'],'-std=c++17','-shared','-fPIC','-Wl,--no-undefined',
              '-fsanitize=address,undefined','-fno-omit-frame-pointer',
              '-DORBITER_NATIVE_BUILD_CONFIGURATION="'+identity['configuration']+'"',
              '-DPHASE6_REJECTED_METADATA='+str(i),'-I'+str(ROOT/'Src/Orbiter'),
              '-I'+str(args.build/'native-sdk'),str(HERE/'RejectedModule.cpp'),
              '-o',str(fixtures/('metadata-'+str(i)+'.so'))]
        atomic_json(fixtures/('command-'+str(i)+'.json'),argv)
        try:
            with (fixtures/('build-'+str(i)+'.log')).open('w') as log:
                subprocess.run(argv,check=True,stdout=log,stderr=subprocess.STDOUT)
        except BaseException as error:
            report['status']='failed';report['failures']['fixture-build-'+str(i)]=str(error)
            atomic_json(manifest,report)
            raise
        guards[str(fixtures/('metadata-'+str(i)+'.so'))]=sha(fixtures/('metadata-'+str(i)+'.so'))
    atomic_json(manifest,report)
    by_id={c['id']:c for c in cases}
    try:
        with Compositor(args.compositor_tools,args.output/'compositor',1,'gl',repeat_rate=0) as display:
            env=dict(display.environment,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',
                     LP_NUM_THREADS='2',LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent),
                     LD_LIBRARY_PATH=':'.join(map(str,[args.build,*args.library])),
                     **{k:v for k,v in ENV.items() if v is not None})
            env.pop('LD_PRELOAD',None)
            for control in expected:
                folder=args.output/control['id'];folder.mkdir()
                assets=folder/'assets';shutil.copytree(args.assets,assets,copy_function=os.link)
                family=control['family'];variant=control['variant'];case=by_id[control['case']]
                target=config['classes'][family]['target'];source=(args.assets/target).read_bytes()
                scenario=(args.assets/case['scenario_entry_point']).read_text()
                modules=args.build/'NativeModules'
                error='Unsupported stock vessel class or capabilities: '+family
                if variant=='unknown-class':
                    clone='Phase6Unqualified'+family
                    new=assets/'Config/Vessels'/(clone+'.cfg');new.write_bytes(source)
                    scenario=re.sub(':'+re.escape(family)+r'(?=\s*$)',':'+clone,scenario,flags=re.M)
                    error='Unsupported stock vessel class or capabilities: '+clone
                else:
                    module={'foreign-factory':'ShuttlePB','missing-module':'Phase6MissingModule',
                            'generic-fallback':None}.get(variant,'Phase6RejectedModule')
                    lines=source.splitlines(keepends=True)
                    lines=[line for line in lines if line.split(b'=',1)[0].strip().lower()!=b'module']
                    changed=b''.join(lines)+(b'\nModule = '+module.encode()+b'\n' if module else b'')
                    path=assets/target;path.unlink();path.write_bytes(changed)
                    if variant=='missing-module':error='Phase6MissingModule'
                    if variant in ('metadata','missing-query','windows-pe'):
                        modules=folder/'modules';shutil.copytree(args.build/'NativeModules',modules,copy_function=os.link)
                        destination=modules/'Vessel/Phase6RejectedModule.so'
                        original=(fixtures/('metadata-'+str(control['metadata'])+'.so') if variant=='metadata'
                                  else args.build/'liborbiter_production_boundary.so' if variant=='missing-query' else pe)
                        os.link(original,destination)
                        error=(META[control['metadata']] if variant=='metadata' else
                               'Missing native module entry: OrbiterNativeQuery' if variant=='missing-query' else
                               'Cannot load native module')
                scenario_path=folder/'input.scn';scenario_path.write_text(scenario)
                roster=ships(scenario)
                require(set(roster)==set(case['declared_vessels']), 'Negative control removed an original vessel')
                cfg=folder/'Orbiter.cfg';cfg.write_bytes((HERE.parent/'NativeScene/Orbiter.cfg').read_bytes())
                argv=list(map(str,[executable,'--assets',assets,'--data',args.data,'--planets',args.planets,
                      '--modules',modules,'--scenario',scenario_path,'--config',cfg,'--evidence',folder,
                      '--save',folder/'saved.scn','--frames','1','--run']))
                inputs={str(p):sha(p) for p in (executable,scenario_path,cfg,assets/target)}
                if variant=='unknown-class':inputs[str(new)]=sha(new)
                if variant in ('metadata','missing-query','windows-pe'):inputs[str(destination)]=sha(destination)
                atomic_json(folder/'invocation.json',dict(argv=argv,control=control,environment=ENV,
                    guarded_files_sha256=inputs,input_roster=roster,expected_error=error))
                with (folder/'console.log').open('w') as log:
                    owned=OwnedProcess(argv,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
                    try:owned.process.wait(timeout=180)
                    finally:atomic_json(folder/'process-receipt.json',owned.cancel())
                report['controls'][control['id']]=inspect_case(folder,control)
                atomic_json(manifest,report)
                print(control['id'],'rejected before presentation with clean sanitizers',flush=True)
        require(all(sha(p)==v for p,v in guards.items()),'Protected negative-control inputs changed')
        report['status']='passed-negative-loader-and-class-controls-only'
    except BaseException as error:
        report['status']='failed';report['failures'][control['id'] if 'control' in locals() else 'setup']=str(error)
        raise
    finally:atomic_json(manifest,report)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();require(not args.output.exists(),'Fresh independent rejection audit required')
    atomic_json(args.output,audit(args.capture))
