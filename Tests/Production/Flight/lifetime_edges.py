#!/usr/bin/env python3
"""Exercise production lifecycle edge cases, repeated ownership and SDK contracts.

Supplementary invariants only. The unchanged Windows attachments/lifetime cases
remain the numerical and callback-order oracle in verify.py.
"""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from behavior_suite import scenario,rows
from mesa_runtime import require

def schedules():
    cases={}
    for name,alternate in [('focused_delete',''),('alternative_camera',' Earth')]:
        cases[name]=[(0,'create','Child ShuttlePB'),(1,'focus','Child'),(4,'delete','Child'+alternate)]
    cases['delete_parent']=[(0,'create','Child ShuttlePB'),(1,'focus','Child'),(4,'delete','PB')]
    for name,deleted in [('attached_child_delete','Child'),('attached_parent_delete','PB')]:
        cases[name]=[(0,'create','Child ShuttlePB'),(0,'attachment','Child'),(1,'attach','Child')]
        if deleted=='PB':cases[name].append((2,'focus','Child'))
        cases[name].append((4,'delete',deleted))
    cases['simultaneous_delete']=[(0,'create','A ShuttlePB'),(0,'focus','A'),(0,'create','B ShuttlePB'),(0,'focus','PB'),(4,'delete','A'),(4,'delete','B')]
    cases['twenty_cycles']=[]
    for cycle in range(20):
        tick=cycle*10
        cases['twenty_cycles'] += [(tick,'create_legacy' if cycle%2 else 'create','Child ShuttlePB'),(tick+1,'focus','Child'),(tick+2,'focus','PB'),(tick+3,'delete','Child PB')]
    cases['persist_dynamic']=[(0,'create','Child ShuttlePB'),(1,'focus','Child'),(4,'delete','PB'),(10,'save','1')]
    cases['close_last_focus']=[(1,'delete','ISS'),(1,'delete','PB')]
    return cases

def check(directory,name):
    state=rows(directory/'flight-state.csv');events=rows(directory/'lifetime-events.csv');visual=rows(directory/'visual-events.csv')
    final=[r for r in state if r['tick']==state[-1]['tick']];objects={r['object'] for r in final}
    if name=='close_last_focus':
        require(int(state[-1]['tick'])<12,'Original no-focus policy failed to close the session')
    else:
        parent_deleted=name in ('delete_parent','attached_parent_delete','persist_dynamic')
        require(objects==({'Child','ISS'} if parent_deleted else {'PB','ISS'}),'Deleted objects remain or survivors disappeared')
        require({r['focus'] for r in final}==({'Child'} if parent_deleted else {'PB'}),'Focus did not reach the surviving real vessel')
        require(all(not r['attached'] for r in final),'Surviving vessel retains a deleted attachment partner')
    if name in ('focused_delete','alternative_camera'):
        targets=[r['object'] for r in events if r['phase']=='camera.target' and int(r['frame'])>=4]
        require(targets==(['Earth'] if name=='alternative_camera' else ['PB']),'Camera retains a deleted vessel or ignores its alternative')
    if name=='simultaneous_delete':
        require([r['object'] for r in events if r['phase']=='module.delete']==['B','A'],'Original reverse deletion order changed')
    for child in (['A','B'] if name=='simultaneous_delete' else ['Child'] if name!='close_last_focus' else []):
        count=20 if name=='twenty_cycles' else 1
        require([r['event'] for r in visual if r['object']==child]==['register','unregister']*count,'Repeated child visuals leaked or outlived their bodies')
        for phase in ('module.library.open','module.interface.release.before','module.interface.release.after','module.library.close.before','module.library.close.after'):
            require(sum(r['phase']==phase and r['object']==child for r in events)==count,'Native module ownership count differs: '+phase)
    life=json.loads((directory/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']>0,'Lifecycle session did not release its real window/context')
    return dict(final_objects=sorted(objects),final_tick=int(state[-1]['tick']),graphics_released=True,ownership='passed')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);fixture=out/'orbit.scn';fixture.write_text(scenario('orbit'));report={}
    for name,commands in schedules().items():
        tape=out/(name+'.csv');tape.write_text('tick,phase,action,value\n'+''.join(f'{tick},pre,{action},{value}\n' for tick,action,value in commands));traces=[]
        for render in (4,17):
            directory=out/(name+'-render-'+str(render));directory.mkdir(exist_ok=True);argv=[str(a.executable.resolve())]
            for arg in ('assets','data','modules','planets'):argv+=['--'+arg,str(getattr(a,arg).resolve())]
            argv += ['--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),'--scenario',str(fixture),'--save',str(directory/'checkpoint.scn'),'--evidence',str(directory),'--replay',str(tape),'--ticks',str(210 if name=='twenty_cycles' else 12),'--fixed-step','.25','--render-every',str(render),'--run']
            with (directory/'console.log').open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
            traces.append((directory/'flight-state.csv').read_bytes());report[name]=check(directory,name)
        require(traces[0]==traces[1],'Lifecycle state depends on rendering frequency: '+name)
        if name=='persist_dynamic':
            saved=out/'persist_dynamic-render-4/checkpoint.scn'
            text=saved.read_text();require('Child:ShuttlePB' in text and 'PB:ShuttlePB' not in text,'Saved object graph lost the child or retained its deleted parent')
            require(saved.read_bytes()==(out/'persist_dynamic-render-17/checkpoint.scn').read_bytes(),'Dynamic persistence depends on rendering')
            target=out/'reloaded';target.mkdir(exist_ok=True);command=[str(a.executable.resolve())]
            for arg in ('assets','data','modules','planets'):command+=['--'+arg,str(getattr(a,arg).resolve())]
            command+=['--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),'--scenario',str(saved),'--evidence',str(target),'--ticks','12','--run']
            with (target/'console.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
            initial=[r for r in rows(target/'flight-state.csv') if r['tick']=='0']
            require({r['object'] for r in initial}=={'Child','ISS'} and {r['focus'] for r in initial}=={'Child'},'Stock reload did not restore the actual created/deleted/focus graph')
            report[name]['stock_reload']=True
        report[name]['render_frequency_independent']=True
    (out/'lifetime-edges.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
