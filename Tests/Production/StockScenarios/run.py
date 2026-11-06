#!/usr/bin/env python3
"""Attempt every unchanged locked stock scenario; retain every failure explicitly."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from inventory import ROOT,corpus,digest,require
import intentional_exit
import sys
sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection'))
import admission as api_admission
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from processes import OwnedProcess


def rows(path):
    if not path.exists():return []
    with path.open() as stream:return list(csv.DictReader(stream))


def inspect(out,case,returncode,scenario=None,exit_reference=None,profile=None,api_reference=None):
    log=(out/'console.log').read_text(errors='replace')
    markers=('Lua error:','LuaCall (','Orbiter native production:','runtime error:',
             'ERROR: AddressSanitizer:','ERROR: LeakSanitizer:','WARNING: ThreadSanitizer:')
    problems=[line for line in log.splitlines() if any(marker in line for marker in markers)]
    if returncode:problems.append('process exit '+str(returncode))
    selected=None;exit_observation=None;api_selected=None;api_observation=None
    try:
        selected=intentional_exit.policy(scenario,case)
        if selected:
            exit_observation=intentional_exit.inspect(out,selected,returncode,exit_reference,profile)
        api_selected=api_admission.policy(scenario,case,api_reference)
        if api_selected:
            api_observation=api_admission.inspect(out,case,api_reference,profile,returncode)
    except (ValueError,OSError,KeyError,TypeError) as error:
        problems.append('Pinned stock exit rejected: '+str(error))
    frames=selected['pins']['termination']['completed_frames'] if selected else 0 if api_selected else 60
    receipt_path=out/'process-receipt.json'
    if api_selected or receipt_path.exists():
        try:
            receipt=json.loads(receipt_path.read_text())
            require(receipt['terminal'] is True and receipt['cancelled'] is False and
                    type(receipt['actual_collector_pid']) is int and receipt['actual_collector_pid']>0 and
                    receipt['actual_returncode']==returncode, 'Completed actual simulator PID/exit receipt required')
        except (ValueError,OSError,KeyError,TypeError) as error:
            problems.append('Process receipt rejected: '+str(error))
    life_path=out/'graphics-lifecycle.json'
    life=json.loads(life_path.read_text()) if life_path.exists() else {}
    if life!=dict(rendered_frames=frames,successful_presents=frames,context_deleted=True):
        problems.append('Incomplete '+str(frames)+'-frame presentation or context deletion')
    states=rows(out/'flight-state.csv');groups={}
    for row in states:groups.setdefault(int(row['tick']),[]).append(row)
    expected={(name,kind.lower()) for name,kind in case['ships'].items()}
    if set(groups)!=set(range(frames+1)):problems.append('Incomplete finalized all-vessel ticks')
    for tick,group in groups.items():
        actual={(r['object'],r['class'].lower()) for r in group}
        if len(group)!=len(expected) or actual!=expected:
            problems.append('Incomplete or substituted vessel manifest at tick '+str(tick));break
    if case['dependency_problems']:problems.append('Declared vessel dependencies are incomplete')
    meshes=rows(out/'visual-meshes.csv')
    result=dict(status='passed' if not problems else 'failed',problems=problems,returncode=returncode,
        lifecycle=life,finalized_ticks=len(groups),declared_vessels=len(expected),
        observed_vessels=sorted({(r['object'],r['class']) for r in states}),
        initial_mjd=float(states[0]['mjd']) if states else None,
        visual_mesh_records=len(meshes),
        files_sha256={name:digest(out/name) for name in ('console.log','flight-state.csv','visual-meshes.csv',
            'graphics-lifecycle.json','native-window.json','invocation.json','process-receipt.json') if (out/name).exists()})
    if selected:
        result['intentional_exit']=exit_observation
        for path in sorted(out.iterdir()):
            if path.is_file() and path.suffix in ('.csv','.txt','.log','.json','.scn'):
                result['files_sha256'][path.name]=digest(path)
    if api_selected:
        result['general_api_startup_exit']=api_observation
        for name in ('api-asset-variant.json','saved.scn','numerics.json'):
            if (out/name).exists():result['files_sha256'][name]=digest(out/name)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--inventory-only',action='store_true')
    p.add_argument('--case',action='append')
    p.add_argument('--backend',choices=('x11','wayland'),required=True)
    p.add_argument('--build-record',type=Path,required=True)
    p.add_argument('--runtime-source-commit',required=True)
    p.add_argument('--runtime-owner',type=Path,default=ROOT,help='Retained immutable source/package owner, when different from this runner')
    p.add_argument('--stock-exit-reference',type=Path)
    p.add_argument('--general-api-qualification',type=Path,help='Explicit audited v2 test variant and startup-exit qualification')
    a=p.parse_args()
    for name in ('executable','assets','data','modules','planets','output','build_record','stock_exit_reference'):
        if getattr(a,name) is not None:setattr(a,name,getattr(a,name).resolve())
    report=corpus(a.assets,a.modules)
    require(not a.case or set(a.case)<=set(report['cases']),'Unknown stock scenario selection')
    a.runtime_owner=a.runtime_owner.resolve()
    identity=intentional_exit.build_identity(a.executable,a.modules,a.build_record,a.runtime_source_commit,a.runtime_owner)
    api_reference=api_admission.reference(a.general_api_qualification)
    runtime_environment={key:os.environ.get(key) for key in ('LD_LIBRARY_PATH','LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER',
        'LP_NUM_THREADS','ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS')}
    if identity['sanitizer_linked']:
        require(all(runtime_environment[key]==value for key,value in dict(
            ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1').items()),
            'Instrumented stock sweep requires explicit leak detection and no suppressions')
    a.output.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),Path(__file__).with_name('inventory.py'),Path(intentional_exit.__file__),
             ROOT/'Src/Orbiter/Production/NativeApplication.cpp',
             ROOT/'Tests/Production/StockVessels/Observation.h',ROOT/'Tests/Production/StockVessels/verify_original.py',
             ROOT/'Tests/Production/StockVessels/original.py',ROOT/'Tests/Production/behavior_suite.py',
             ROOT/'Tests/Production/Cockpit/cases.json',ROOT/'Tests/Production/phase3-extraction.lock.json',
             *sorted(intentional_exit.FIXTURE.glob('*.py')),intentional_exit.FIXTURE/'case.json',
             intentional_exit.FIXTURE/'observations.lock.json',intentional_exit.FIXTURE/'NativeProbe.cpp']
    sources.extend(ROOT/'Tests/Production/GeneralApiCorrection'/name for name in
                   ('admission.py','qualification.py','startup_contract.py','startup-policy-v1.json','prepare.py','inputs-v2.json'))
    sources.append(ROOT/'Tests/Production/Closeout/processes.py')
    report.update(status='inventory-only' if a.inventory_only else 'running',phase6_complete=False,
        scope='Unchanged complete 157-scenario corpus; initialization/smoke, not physical interaction or new Windows state/image parity',
        backend=a.backend,engine_default_mjd_without_numeric_date=51982.5,execution_protocol='normal-stock-capture-v2',
        runtime_owner=str(a.runtime_owner),diagnostic_only=a.case is not None,
        cases_requested=[name for name in report['cases'] if a.case is None or name in a.case],
        source_sha256={str(path.relative_to(ROOT)):digest(path) for path in sources},
        runtime_identity=identity,runtime_environment=runtime_environment,build_record_path=str(a.build_record),
        runtime_sha256=dict(executable=digest(a.executable),renderer=digest(a.modules/'Graphics/OGLClient.so'),
                            vessels=digest(a.executable.parent/'liborbiter_production_vessels.so')))
    observer_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,checksum in report['source_sha256'].items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',observer_commit+':'+name])
        require(hashlib.sha256(body).hexdigest()==checksum,'Stock observer must match its immutable producer: '+name)
    report['observer_commit']=observer_commit
    if api_reference:
        report['general_api_qualification']=dict(path=api_reference['path'],sha256=api_reference['sha256'],
            protocol=api_reference['body']['protocol'],variant='general-api-spice-test-correction-v2')
    manifest=a.output/'stock-scenarios.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    if a.inventory_only:
        print(json.dumps(dict(scenarios=157,inventory_ready=sum(c['inventory_ready'] for c in report['cases'].values()))));return
    exit_selected=any(intentional_exit.policy(name,case,a.assets) for name,case in report['cases'].items()
                      if not a.case or name in a.case)
    probe=None
    if exit_selected:
        report['stock_exit_reference']=intentional_exit.audit_reference(a.stock_exit_reference,a.output/'stock-exit-original-audit.json')
        probe=intentional_exit.compile_probe(a.output,a.executable,identity)
        report['stock_exit_probe_sha256']=digest(probe)
    build=json.loads(a.build_record.read_text())
    protected={str(a.runtime_owner/name):checksum for name,checksum in build['runtime_files_sha256'].items()}
    owning=build.get('source_sha256_lf',build.get('source_sha256'))
    protected.update({str(a.runtime_owner/name):digest(a.runtime_owner/name) for name in owning})
    protected.update({str(path):digest(path) for path in [*sources,a.build_record]})
    if exit_selected:
        script=intentional_exit.settings()['script']
        protected[str(a.assets/script)]=digest(a.assets/script)
        protected[str(probe)]=digest(probe)
    if api_reference:
        protected[api_reference['path']]=api_reference['sha256']
        protected.update(api_reference['body']['evidence_sha256'])
        protected[str(a.assets/'Script/Tests/GeneralApiTest.lua')]=digest(a.assets/'Script/Tests/GeneralApiTest.lua')
    report['protected_files_sha256']=protected
    save()
    try:
        for number,(name,case) in enumerate(report['cases'].items()):
            if a.case and name not in a.case:continue
            out=a.output/f'{number:03d}';out.mkdir()
            selected=intentional_exit.policy(name,case,a.assets)
            api_selected=api_admission.policy(name,case,api_reference)
            selected_assets=a.assets
            if api_selected:
                selected_assets=out/'api-assets'
                variant=api_admission.stage_assets(a.assets,selected_assets)
                (out/'api-asset-variant.json').write_text(json.dumps(variant,indent=2)+'\n')
                (out/'saved.scn').write_bytes(api_admission.startup_contract.SAVE_SENTINEL)
            (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\n')
            scenario=selected_assets/'Scenarios'/name
            env=None
            if selected:
                scenario=out/'flight.scn';scenario.write_bytes((a.assets/'Scenarios'/name).read_bytes())
                (out/'saved.scn').write_bytes(b'Existing save preserved across stock oapi.exit.\n')
                (out/'replay.csv').write_text('tick,phase,action,value\n')
                with (out/'Orbiter.cfg').open('a') as config:config.write('InstrumentUpdateInterval = 0.25\n')
                env=intentional_exit.environment(probe,identity)
            argv=[str(a.executable)]
            for key in ('assets','data','modules','planets'):argv+=['--'+key,str(selected_assets if key=='assets' else getattr(a,key))]
            argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(scenario),
                   '--evidence',str(out),'--save',str(out/'saved.scn'),'--frames','60','--fixed-step',
                   '0.015625' if api_selected else '.25','--run']
            if selected:argv+=['--replay',str(out/'replay.csv')]
            (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
            started=time.monotonic()
            try:
                with (out/'console.log').open('w') as console:
                    process=OwnedProcess(argv,cwd=out,env=env,stdout=console,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+180
                    try:
                        while process.process.poll() is None:
                            process.discover()
                            if time.monotonic()>deadline:raise subprocess.TimeoutExpired(argv,180)
                            time.sleep(.1)
                    finally:
                        if process.process.poll() is None:process.cancel()
                        (out/'process-receipt.json').write_text(json.dumps(process.receipt(),indent=2)+'\n')
                case['returncode']=process.process.returncode
                if selected:
                    (out/'console.txt').write_bytes((out/'console.log').read_bytes())
                    (out/'process-result.json').write_text(json.dumps(dict(returncode=case['returncode']))+'\n')
                case.update(inspect(out,case,case['returncode'],name,a.stock_exit_reference,identity['profile'],api_reference))
                window=out/'native-window.json'
                if window.exists() and json.loads(window.read_text())['backend']!=a.backend:
                    case['status']='failed';case['problems'].append('Actual window backend differs')
            except (OSError,ValueError,subprocess.TimeoutExpired) as error:
                case.update(status='failed',problems=[str(error)])
            case.update(output=out.name,elapsed_seconds=time.monotonic()-started)
            print(json.dumps(dict(scenario=name,status=case['status'],ready=case['inventory_ready'],
                                  frames=case.get('lifecycle',{}).get('successful_presents',0),problems=case.get('problems',[]))),flush=True)
            save()
        attempted=[c for c in report['cases'].values() if c['status']!='not-run']
        report['summary']=dict(attempted=len(attempted),passed=sum(c['status']=='passed' for c in attempted),
            failed=sum(c['status']=='failed' for c in attempted),inventory_ready=sum(c['inventory_ready'] for c in report['cases'].values()),
            source_metadata_mismatches=sum(c['locked_inventory_metadata_differs'] for c in report['cases'].values()))
        require(all(digest(Path(name))==checksum for name,checksum in protected.items()),
                'Sources, reference pins, probe or retained application binaries changed during stock sweep')
        report['sources_and_binaries_unchanged']=True
        report['status']='passed' if len(attempted)==157 and all(c['status']=='passed' for c in attempted) else 'incomplete'
    finally:save()
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
