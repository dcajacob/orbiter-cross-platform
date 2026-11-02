#!/usr/bin/env python3
"""Verify actual native controlled landing against the additional frozen Windows reference."""
import argparse,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
from capture import CASE,validate,verify_frozen as verify_ground
from comparison import compare_states
from behavior_suite import rows
from mesa_runtime import require
spec=importlib.util.spec_from_file_location('controlled_reference',HERE/'frozen.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)

def commands():
    lines=['tick,phase,action,value\n','0,pre,nav,2\n','0,pre,holdalt_ground,12\n','1200,pre,holdalt_ground,0\n']
    for tick in range(4800,CASE['frames']):
        lines.extend(f'{tick},pre,{action},{value}\n' for action,value in (('navoff',7),('navoff',2),('hover',0)))
    lines.append(f'{CASE["frames"]-1},after,save,1\n');return ''.join(lines)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args()
    verify_ground();proof=reference.verify();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=out/'reference'
    with zipfile.ZipFile(HERE.parent/'ControlledReference'/proof['artifacts'][a.configuration]['path']) as archive:
        for name in archive.namelist():
            prefix='production-behavior/controlled-landing/'
            if name.startswith(prefix) and not name.endswith('/'):
                relative=Path(name[len(prefix):]);require('..' not in relative.parts,'Invalid frozen member')
                target=frozen/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    tape=out/'controlled-landing.csv';tape.write_text(commands());histories=[];saves=[];runs=[];failures=[]
    for render in (4,17):
        directory=out/('render-'+str(render));directory.mkdir(exist_ok=True);argv=[str(a.executable.resolve())]
        for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
        argv+=['--config',str(HERE.parent/'GroundFlight/Orbiter.cfg'),'--scenario',str(HERE.parent/'GroundFlight/Edwards-ShuttlePB.scn'),
               '--replay',str(tape),'--save',str(directory/'Scenarios/BehaviorSnapshot.scn'),'--evidence',str(directory),
               '--ticks',str(CASE['frames']),'--fixed-step',str(CASE['fixed_step']),'--render-every',str(render),'--run']
        result=dict(render_every=render)
        try:
            with (directory/'console.log').open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
            history=(directory/'flight-state.csv').read_bytes();histories.append(history)
            saves.append((directory/'Scenarios/BehaviorSnapshot.scn').read_bytes())
            (directory/'behavior-state.csv').write_bytes(history)
            result['safety']=validate(directory)
            controls=[r for r in rows(directory/'flight-controls.csv') if r['object']=='PB']
            require(controls[-1]['flight_status']=='1','Native SDK never reached a true landed state')
            phases={'world.update.before','world.update.after','world.finalise.before','world.finalise.after','time.end.before','time.end.after','app.frame.end'}
            original=[(r['phase'],r['detail']) for r in rows(frozen/'behavior-events.csv') if r['phase'] in phases]
            native=[(r['event'],r['running']) for r in rows(directory/'application-lifecycle.csv') if r['event'] in phases]
            require(original==native,'Original session/finalization ordering changed')
            life=json.loads((directory/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']>0,'Graphics session did not complete')
            result['lifecycle_order']=True
            old=[r for r in rows(frozen/'behavior-state.csv') if r['object']=='PB']
            new=[r for r in rows(directory/'flight-state.csv') if r['object']=='PB']
            result['maximum_propellant_difference_kg']=max(abs(float(x['fuel'])-float(y['fuel'])) for x,y in zip(old,new))
            result['windows']=compare_states(frozen/'behavior-state.csv',directory/'flight-state.csv')
            result['status']='passed'
        except Exception as error:
            result.update(status='failed',error=str(error));failures.append(f'render-{render}: {error}')
        runs.append(result)
    independent=len(histories)==len(saves)==2 and histories[0]==histories[1] and saves[0]==saves[1]
    if not independent:failures.append('Controlled landing physics or persistence depends on rendering frequency, or a run is incomplete')
    report=dict(status='failed' if failures else 'passed controlled upright landing',reference_run=proof['run_id'],render_frequency_independent=independent,runs=runs,failures=failures)
    (out/'controlled-landing-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
