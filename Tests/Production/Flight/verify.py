#!/usr/bin/env python3
"""Run the actual native production flight host against immutable Windows cases."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from behavior_suite import scenario,rows,compare_states
from frozen_behavior import load_reference
from mesa_runtime import require,digest

def commands(name):
    lines=[]
    def add(tick,action,value,phase='pre'):lines.append((tick,phase,action,value))
    if name=='manual_flight':
        add(0,'main',.2);add(40,'main',0);add(40,'hover',.1);add(60,'hover',0)
        for slot,group in enumerate((3,4,5,6,7,8,11,12,10,9,13,14)):
            add(80+slot*40,'attitude',1 if slot<6 else 2)
            for tick in range(80+slot*40,88+slot*40):add(tick,'rcs'+str(group),.2)
        for i,mode in enumerate((1,3,4,5,6)):add(560+i*80,'navreset',0);add(560+i*80,'nav',mode)
    if name in ('attachments','lifetime'):
        add(1 if name=='attachments' else 10,'create','Child ShuttlePB')
        if name=='attachments':
            add(1,'attachment','Child');add(10,'attach','Child');add(30,'detach','Child')
        else:
            add(11,'focus','Child');add(20,'focus','PB');add(30,'delete','Child PB')
    if name=='pb_persistence':add(0,'main',.2);add(39,'save',1,'after')
    if name=='docked':add(10,'undock',0)
    if name=='clock':
        add(20,'warp',10);add(40,'warp',1);add(59,'pause',1,'after');add(62,'pause',0,'after')
    return 'tick,phase,action,value\n'+''.join(f'{t},{p},{a},{v}\n' for t,p,a,v in sorted(lines,key=lambda x:x[0]))

def extract(archive,out):
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.startswith('production-behavior/') and not name.endswith('/'):
                target=out/Path(name).relative_to('production-behavior');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--case',action='append')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    old=load_reference(ROOT/'Tests/Production/BehaviorReference')
    extract((ROOT/'Tests/Production/BehaviorReference'/old['artifacts'][a.configuration]['path']).resolve(),out/'reference')
    newroot=ROOT/'Tests/Production/FlightReference';new=json.loads((newroot/'provenance.json').read_text())
    require(new['run_id']==41350187262 and new['automatic_refresh'] is False,'Wrong pre-flight Windows reference')
    for record in new['artifacts'].values():require(digest(newroot/record['path'])==record['sha256'],'Frozen flight archive changed')
    extract(newroot/new['artifacts'][a.configuration]['path'],out/'reference')
    cases={c['id']:c for c in json.loads((ROOT/'Tests/Production/behavior-cases.json').read_text())['cases']}
    cases.update({name:dict(id=name,frames=count,fixed_step=.25,fixture=fixture,budgets='orbital') for name,count,fixture in [('manual_flight',980,'orbit'),('pb_persistence',60,'orbit'),('pb_reload',60,'reload')]})
    names=a.case or ['manual_flight','docked','dock_approach','clock','pb_persistence','pb_reload','attachments','lifetime']
    report={}
    for name in names:
        case=cases[name];fixture=out/(name+'.scn')
        if name=='pb_reload':fixture=(out/'pb_persistence-render-4/checkpoint.scn')
        else:fixture.write_text(scenario(case['fixture']))
        tape=out/(name+'.csv');tape.write_text(commands(name))
        histories=[];roundtrips=[]
        for render in (4,17):
            directory=out/(name+'-render-'+str(render));directory.mkdir(exist_ok=True)
            argv=[str(a.executable.resolve())]
            for n in ('assets','data','modules','planets'):argv += ['--'+n,str(getattr(a,n).resolve())]
            argv+=['--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),'--scenario',str(fixture.resolve()),'--save',str(directory/'checkpoint.scn'),'--evidence',str(directory),'--ticks',str(case['frames']),'--fixed-step',str(case['fixed_step']),'--render-every',str(render),'--replay',str(tape),'--run']
            with (directory/'console.log').open('w') as log:process=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            require(process.returncode==0,'Native production flight failed: '+str(directory))
            histories.append((directory/'flight-state.csv').read_bytes())
            roundtrips.append(compare_states(out/'reference'/name/'behavior-state.csv',directory/'flight-state.csv',case))
            if name in ('attachments','lifetime'):
                from lifecycle import verify_lifetime
                roundtrips[-1]['lifetime']=verify_lifetime(out/'reference'/name,directory,case)
            lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text());require(lifecycle['context_deleted'] and lifecycle['successful_presents']>0,'Flight graphics lifecycle incomplete')
        require(histories[0]==histories[1],'Physics changes with render frequency: '+name)
        report[name]=dict(render_frequency_independent=True,windows_differences=roundtrips)
        if name=='pb_persistence':
            require((out/'pb_persistence-render-4/checkpoint.scn').read_bytes()==(out/'pb_persistence-render-17/checkpoint.scn').read_bytes(),'Stock serializer depends on frame rate')
    # Each actual graphics session owns its real window/context and world.
    cycle=out/'cycles';argv=[str(a.executable.resolve())]
    for n in ('assets','data','modules','planets'):argv += ['--'+n,str(getattr(a,n).resolve())]
    argv+=['--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),'--scenario',str(ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn'),'--save',str(out/'cycle-checkpoint.scn'),'--evidence',str(cycle),'--frames','60','--sessions','20','--run']
    with (out/'cycles.log').open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    sessions=sorted(cycle.glob('session-*'));require(len(sessions)==20,'Incomplete session replacement test')
    states=[]
    for session in sessions:
        life=json.loads((session/'graphics-lifecycle.json').read_text())
        require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Session did not release its real graphics context')
        events=rows(session/'visual-events.csv')
        for event in ('register','unregister'):require({'PB','ISS','Earth'}<={r['object'] for r in events if r['event']==event},'Session visual lifetime incomplete')
        states.append((session/'flight-state.csv').read_bytes())
    require(len(set(states))==1,'Session replacement changed initialized/stepped state')
    report['twenty_sessions']=dict(status='passed',identical_states=True)
    (out/'flight-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
