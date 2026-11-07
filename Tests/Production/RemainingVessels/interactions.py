"""Original key/GUI/Lua actuator interactions through the existing native runner."""
import argparse
import concurrent.futures
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import threading
import time
import traceback

from lifetimes import (HERE,ROOT,prepare,OwnedProcess,Compositor,DIAGNOSTICS,
                       atomic_json,load,require,sha,rows,ships)

STRINGS={'object','class','dock','focus','attached'}
TRACES={'flight-state.csv','flight-animations.csv','flight-controls.csv','thrust-state.csv','input-events.csv'}
OPS={'eq':lambda a,b:a==b,'ne':lambda a,b:a!=b,'gt':lambda a,b:a>b,'lt':lambda a,b:a<b,
     'ge':lambda a,b:a>=b,'le':lambda a,b:a<=b}
POSE=r'(?:\bset_(?:globalpos|globalvel|rotationmatrix|globalorientation|elements|angvel)|:dock|:create_dock|:create_attachment|:attach_child|\bcreate_vessel)\s*\('
ENV=dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
         UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LD_PRELOAD=None)


def schedule(flow):
    # --save declares a destination. The original Ctrl-S dispatch must write it.
    final=flow['frames']-8
    require(all(int(row['tick'])<final for row in flow['replay']),
            'Control schedule must leave the declared final Ctrl-S interval free')
    result=list(flow['replay'])
    for offset,key in enumerate((29,31,-31,-29)):
        result.append(dict(tick=final+offset,phase='before',action='key',value=str(key)))
    return sorted(result,key=lambda row:(int(row['tick']),{'start':0,'before':1,'pre':2,'after':3}[row['phase']]))


def population(flow,declared):
    reference=flow.get('original_population')
    if reference is None:return declared
    require(set(reference)=={'path','sha256'} and sha(reference['path'])==reference['sha256'],
            'Unchanged original Windows population observation required')
    initial=[r for r in rows(reference['path']) if r['tick']=='0']
    expected={r['object']:r['class'] for r in initial}
    require(expected and len(expected)==len(initial) and
            all(expected.get(name)==kind for name,kind in declared.items()),
            'Generated stock population cannot remove or substitute a declared vessel')
    return expected


def value(folder,spec):
    if not isinstance(spec,dict):return spec
    require(set(spec)=={'trace','where','field'} and spec['trace'] in TRACES,'Explicit interaction trace selector required')
    found=[r for r in rows(folder/spec['trace']) if all(r.get(k)==str(v) for k,v in spec['where'].items())]
    require(len(found)==1 and spec['field'] in found[0],'Missing or ambiguous actual interaction observation')
    text=found[0][spec['field']]
    try:number=float(text)
    except ValueError:return text
    require(math.isfinite(number),'Nonfinite interaction assertion');return number


def inspect(folder,flow,expected):
    invocation=load(folder/'invocation.json');receipt=load(folder/'process-receipt.json')
    require(receipt['terminal'] and not receipt['cancelled'] and receipt['actual_returncode']==0 and
            receipt['actual_collector_pid']>0 and receipt['owned_process_identities'][0]['argv']==invocation['argv'] and
            invocation['flow']==flow and invocation['environment']==ENV and
            all(sha(p)==v for p,v in invocation['guarded_files_sha256'].items()),'Actual interaction process/input binding differs')
    text=(folder/'console.log').read_text(errors='replace')
    require(not any(v in text for v in DIAGNOSTICS),'Interaction runtime/sanitizer diagnostic')
    require(all(tag in text for tag in flow.get('required_log',[])),'Original Lua actuator command did not execute')
    life=load(folder/'graphics-lifecycle.json')
    require(life==dict(rendered_frames=flow['frames'],successful_presents=flow['frames'],context_deleted=True),
            'Complete interaction frames and clean context required')
    mapped=(folder/'actual-loaded-maps.txt').read_text()
    require(all(p in mapped for p in invocation['required_mapped_files']),
            'Actual application/module/provider mapping missing')
    require(load(folder/'numerics.json')['math']==invocation['expected_actual_math'],
            'Actual interaction CPU math profile differs')
    dispatched=schedule(flow)
    require(invocation['dispatched_replay']==dispatched,'Exact original-control and Ctrl-S schedule differs')
    events=rows(folder/'input-events.csv')
    expected_keys=[(int(row['tick']),abs(int(row['value'])),int(int(row['value'])>0))
                   for row in dispatched if row['action']=='key']
    require([(int(row['tick']),int(row['key']),int(row['down'])) for row in events]==expected_keys and
            any(row['tick']==str(flow['frames']-7) and row['key']=='31' and row['down']==row['lctrl']=='1'
                for row in events),'Actual key dispatch did not consume the complete schedule and Ctrl-S')
    groups={}
    for row in rows(folder/'flight-state.csv'):
        require(None not in row and None not in row.values() and
                all(math.isfinite(float(v)) for k,v in row.items() if k not in STRINGS),
                'Nonfinite or incomplete original interaction state')
        groups.setdefault(int(row['tick']),[]).append(row)
    require(set(groups)==set(range(flow['frames']+1)),'Complete finalized interaction tick coverage required')
    require(all({r['object']:r['class'] for r in group}==expected and len(group)==len(expected)
                for group in groups.values()),'Interaction removed or substituted an original vessel')
    require(ships((folder/'saved.scn').read_text())==expected,'Complete saved interaction roster differs')
    require((folder/'scene.rgba').stat().st_size==1280*720*4,'Complete interaction frame required')
    assertions=[]
    for check in flow['checks']:
        require(set(check)=={'left','op','right'} and check['op'] in OPS,'Explicit finite interaction assertion required')
        a=value(folder,check['left']);b=value(folder,check['right'])
        require(OPS[check['op']](a,b),'Actual original-control outcome failed: '+json.dumps(dict(check=check,left=a,right=b)))
        assertions.append(dict(check=check,left=a,right=b))
    return dict(actual_pid=receipt['actual_collector_pid'],actual_exitcode=0,lifecycle=life,
                assertions=assertions,original_vessels=expected,
                files_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()})


def audit(path):
    path=Path(path).resolve();report=load(path);plan=load(report['plan'])
    require(report['status']=='captured-original-input-interactions-awaiting-independent-audit' and
            not report['failures'] and report['diagnostic_only'] is True and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False and
            all(sha(p)==v for p,v in report['guarded_files_sha256'].items()),'Closed unchanged interaction capture required')
    expected=[f for f in plan['flows'] if f['case'] in report['cases_requested']]
    require(set(report['flows'])=={f['id'] for f in expected},'Complete requested interaction scope required')
    result={}
    cases={c['id']:c for c in load(HERE.parent/'RemainingStock/cases.json')['cases']}
    for flow in expected:
        runs=[]
        for repeat in (1,2):
            recorded=report['flows'][flow['id']][repeat-1]
            require(recorded['original_vessels']==population(flow,cases[flow['case']]['declared_vessels']),
                    'Independent complete original/generated population differs')
            actual=inspect(path.parent/(flow['id']+'-'+str(repeat)),flow,recorded['original_vessels'])
            require(actual==recorded,'Recomputed actual interaction differs');runs.append(actual)
        for name in ('flight-state.csv','flight-animations.csv','input-events.csv','saved.scn','scene.rgba'):
            a=path.parent/(flow['id']+'-1')/name;b=path.parent/(flow['id']+'-2')/name
            require(a.read_bytes()==b.read_bytes(),'Repeated original-input interaction differs: '+name)
        result[flow['id']]=runs
    return dict(status='audited-selected-original-input-interactions-only',capture_sha256=sha(path),
                runtime_identity=report['runtime_identity'],flows=result,actual_processes=len(result)*2,
                qualified_families=sorted({family for f in expected for family in f['families']}),
                owning_bytes_unchanged=True,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)


def capture(args):
    plan=load(args.interaction_plan)
    require(plan['schema']==1 and plan['protocol']=='remaining-stock-original-input-interactions-v1',
            'Versioned original-input plan required')
    flows=[f for f in plan['flows'] if f['case'] in args.case]
    require(flows and {f['case'] for f in flows}==set(args.case),'Exact selected original interaction cases required')
    scripts=[ROOT/f['script'] for f in flows if f.get('script')]
    config,cases,build,identity,executable,guards,producer,original_data=prepare(args,(Path(__file__),args.interaction_plan,*scripts))
    by_id={c['id']:c for c in cases}
    for flow in flows:
        require(1<=flow['frames']<=100000 and flow['fixed_step'] in (.015625,.25) and flow['checks'],
                'Bounded declared interaction duration and outcomes required')
        expected=population(flow,by_id[flow['case']]['declared_vessels'])
        require(set(expected.values())<=set(config['classes']) and set(flow['families'])<=set(expected.values()),
                'Flow does not contain its original families')
        if flow.get('original_population'):
            guards[flow['original_population']['path']]=flow['original_population']['sha256']
        if flow.get('script'):require(not re.search(POSE,(ROOT/flow['script']).read_text()),'State-placement setters cannot manufacture an interaction')
        require(all(r['action'] in ('key','ui','mouse','focus','save') for r in flow['replay']),
                'Original input/GUI/focus/save dispatch only')
    args.output.mkdir(parents=True)
    report=dict(protocol=plan['protocol'],status='running',plan=str(args.interaction_plan),producer_commit=producer,
                runtime_identity=identity,runtime_owner=str(args.owner),actual_original_data=original_data,
                guarded_files_sha256=guards,cases_requested=[c['id'] for c in cases],repeats=2,
                flows={},failures={},diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)
    manifest=args.output/'interactions.json';atomic_json(manifest,report)
    stopping=threading.Event()
    def run(flow):
        result=[];case=by_id[flow['case']]
        for repeat in (1,2):
            require(not stopping.is_set(),'Interaction cancelled after another focused failure')
            folder=args.output/(flow['id']+'-'+str(repeat));folder.mkdir();assets=folder/'assets'
            shutil.copytree(args.assets,assets,copy_function=os.link)
            for p in (assets,*(p for p in assets.rglob('*') if p.is_dir())):p.chmod(p.stat().st_mode|stat.S_IWUSR)
            scenario=assets/case['scenario_entry_point'];original=scenario.read_text()
            require(original==(ROOT/case['scenario_entry_point']).read_text(),'Original complete interaction scene differs')
            expected=population(flow,ships(original))
            if flow.get('script'):
                require(not re.search(r'^\s*Script\s',original,re.M),'Original scenario script cannot be replaced')
                line='  Script '+Path(flow['script']).stem+'\n'
                derived=original.replace('END_ENVIRONMENT',line+'END_ENVIRONMENT',1)
                require(derived.replace(line,'',1)==original,'Interaction changed original vessel/environment input')
                scenario.unlink();scenario.write_text(derived)
                target=assets/'Script'/(Path(flow['script']).stem+'.lua')
                require(not target.exists(),'Interaction script would replace an original installed file')
                target.write_bytes((ROOT/flow['script']).read_bytes())
            cfg=(HERE.parent/'NativeScene/Orbiter.cfg').read_text()
            for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                require(cfg.count(line)==1,'Original propagator fixture differs');cfg=cfg.replace(line,'')
            (folder/'Orbiter.cfg').write_text(cfg+'\nMenubarMode = 1\nInfobarMode = 1\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n'+flow.get('configuration',''))
            if flow.get('gui_evidence',False):
                (folder/'menu-evidence.enabled').touch();(folder/'ui-evidence.enabled').touch()
            with (folder/'replay.csv').open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=('tick','phase','action','value'));writer.writeheader();writer.writerows(schedule(flow))
            argv=list(map(str,[executable,'--assets',assets,'--data',args.data,'--planets',args.planets,'--modules',args.build/'NativeModules',
                '--scenario',scenario,'--config',folder/'Orbiter.cfg','--evidence',folder,'--save',folder/'saved.scn',
                '--replay',folder/'replay.csv','--frames',flow['frames'],'--fixed-step',flow['fixed_step'],
                '--fixed-system-step','.1','--capture-time',(flow['frames']-16)*flow['fixed_step'],'--fixed-ui-clock','--run']))
            inputs={str(p):sha(p) for p in (executable,scenario,folder/'Orbiter.cfg',folder/'replay.csv')}
            if flow.get('script'):inputs[str(target)]=sha(target)
            required=[executable,args.build/'liborbiter_production_boundary.so',args.build/'liborbiter_production_vessels.so',
                      args.build/'NativeModules/Graphics/OGLClient.so',args.gtk_plugin]
            required.extend(args.build/'NativeModules/Vessel'/(config['classes'][kind]['module']+'.so')
                for kind in set(expected.values()) if config['classes'][kind]['module'])
            for name in ('libfontconfig.so.1','libEGL_mesa.so.0','libgdk-3.so.0'):
                found=[p/name for p in args.library if (p/name).is_file()]
                require(len(found)==1,'Explicit unique interaction provider required: '+name);required+=found
            required=[str(p.resolve()) for p in required]
            atomic_json(folder/'invocation.json',dict(argv=argv,flow=flow,environment=ENV,guarded_files_sha256=inputs,
                required_mapped_files=required,dispatched_replay=schedule(flow),
                expected_actual_math='amd-6121d02-'+('sse2' if identity['math_profile']=='sse2' else 'fma3')))
            with Compositor(args.compositor_tools,folder/'compositor',1,'gl',repeat_rate=0) as display:
                env=dict(display.environment,**{k:v for k,v in ENV.items() if v is not None},
                    LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                    LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[args.build,*args.library])))
                env.pop('LD_PRELOAD',None)
                with (folder/'console.log').open('w') as log:
                    owned=OwnedProcess(argv,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
                    try:
                        deadline=time.monotonic()+900
                        while owned.process.poll() is None:
                            try:mapped=(Path('/proc')/str(owned.process.pid)/'maps').read_text()
                            except OSError:mapped=''
                            if all(p in mapped for p in required):
                                (folder/'actual-loaded-maps.txt').write_text(mapped);break
                            require(time.monotonic()<deadline,'Interaction mapping/exit timeout');time.sleep(.01)
                        owned.process.wait(timeout=max(1,deadline-time.monotonic()))
                    finally:atomic_json(folder/'process-receipt.json',owned.cancel())
            try:result.append(inspect(folder,flow,expected))
            except BaseException:
                stopping.set();raise
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending={pool.submit(run,f):f['id'] for f in flows}
        for task in concurrent.futures.as_completed(pending):
            name=pending[task]
            try:report['flows'][name]=task.result()
            except BaseException as error:report['failures'][name]=dict(error=str(error),traceback=traceback.format_exc())
            atomic_json(manifest,report)
    require(all(sha(p)==v for p,v in guards.items()),'Owning interaction bytes changed')
    report['status']='failed' if report['failures'] else 'captured-original-input-interactions-awaiting-independent-audit'
    atomic_json(manifest,report);require(not report['failures'],'Original input interaction failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'Fresh independent interaction audit required');atomic_json(args.output,audit(args.capture))
