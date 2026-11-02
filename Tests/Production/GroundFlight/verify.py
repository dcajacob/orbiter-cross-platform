#!/usr/bin/env python3
"""Compare the actual native flight host with frozen Windows ground flights."""
import argparse,json,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tests/Production'))
from mesa_runtime import require,digest
from behavior_suite import rows
from reference import CASES,MANIFEST,validate,roundtrip
from comparison import compare_states
from frozen import verify as verify_frozen

def commands(case):
    identifier=case['id'];lines=['tick,phase,action,value\n']
    def add(tick,phase,action,value):lines.append(f'{tick},{phase},{action},{value}\n')
    if identifier in ('pb_atmosphere','pb_aerodynamic_controls'):add(0,'start','airborne','1500 200 0')
    elif identifier=='pb_contact':add(0,'start','airborne','8 0 0.5')
    if identifier=='pb_aerodynamic_controls':
        add(0,'start','aerodynamic',7);add(0,'start','attitude',0)
    for tick in range(case['frames']):
        if identifier=='pb_atmosphere':
            if tick==0:add(tick,'pre','nav',2)
            add(tick,'pre','main',.15)
        elif identifier=='pb_aerodynamic_controls':
            add(tick,'pre','elevator',.2 if 60<=tick<120 else -.2 if 180<=tick<240 else 0.)
            add(tick,'pre','aileron',.2 if 300<=tick<360 else -.2 if 420<=tick<480 else 0.)
        elif identifier=='pb_takeoff_landing':
            if tick==0:add(tick,'pre','nav',2)
            if tick==1200:add(tick,'pre','navoff',2)
            add(tick,'pre','hover',1. if tick<240 else .65 if tick<540 else .78 if tick<2100 else 0.)
        if (identifier=='pb_ground_persistence' and tick+1==MANIFEST['checkpoint_tick']) or (identifier=='pb_takeoff_landing' and tick+1==case['frames']):add(tick,'after','save',1)
    return ''.join(lines)

def frozen(output,configuration):
    directory=ROOT/'Tests/Production/GroundReference'
    provenance=verify_frozen(directory)
    with zipfile.ZipFile(directory/provenance['artifacts'][configuration]['path']) as archive:
        for name in archive.namelist():
            if not name.startswith('production-behavior/') or name.endswith('/'):continue
            relative=Path(name).relative_to('production-behavior');require('..' not in relative.parts,'Invalid frozen archive member')
            target=output/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    return provenance

def compare(reference,candidate):
    state=compare_states(reference/'behavior-state.csv',candidate/'flight-state.csv')
    phases={'world.update.before','world.update.after','world.finalise.before','world.finalise.after',
            'time.end.before','time.end.after','app.frame.end'}
    original=[(r['phase'],r['detail']) for r in rows(reference/'behavior-events.csv') if r['phase'] in phases]
    native=[(r['event'],r['running']) for r in rows(candidate/'application-lifecycle.csv') if r['event'] in phases]
    require(original==native,'Ground-flight world/finalization/time lifecycle ordering differs')
    original=rows(reference/'behavior-animations.csv');native=rows(candidate/'flight-animations.csv')
    require(len(original)==len(native),'Actual animation observation count differs')
    for a,b in zip(original,native):
        require(all(a[k]==b[k] for k in ('tick','object','index')) and abs(float(a['state'])-float(b['state']))<=1e-12,
                'Stock control-surface mesh animation differs')
    return dict(state,lifecycle_order=True,animations=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--case',action='append',choices=[c['id'] for c in CASES]);a=p.parse_args()
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
    provenance=frozen(output/'reference',a.configuration);results={};failures=[]
    selected=[c for c in CASES if not a.case or c['id'] in a.case]
    for case in selected:
        name=case['id'];tape=output/(name+'.csv');tape.write_text(commands(case))
        histories=[];saves=[];case_results=[]
        for render in (4,17):
            directory=output/(name+'-render-'+str(render));directory.mkdir(exist_ok=True)
            scenario=(output/('pb_ground_persistence-render-'+str(render))/'Scenarios/BehaviorSnapshot.scn') if case['fixture']=='reload' else HERE/'Edwards-ShuttlePB.scn'
            argv=[str(a.executable.resolve())]
            for arg in ('assets','data','modules','planets'):argv+=['--'+arg,str(getattr(a,arg).resolve())]
            argv+=['--config',str(HERE/'Orbiter.cfg'),'--scenario',str(scenario),'--replay',str(tape),
                   '--evidence',str(directory),'--save',str(directory/'Scenarios/BehaviorSnapshot.scn'),
                   '--ticks',str(case['frames']),'--fixed-step',str(case['fixed_step']),'--render-every',str(render),'--run']
            try:
                with (directory/'console.log').open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
                history=(directory/'flight-state.csv').read_bytes();histories.append(history)
                # Reuse independent Windows semantic checks on the actual native observations.
                (directory/'behavior-state.csv').write_bytes(history)
                (directory/'behavior-animations.csv').write_bytes((directory/'flight-animations.csv').read_bytes())
                behavior=validate(directory,case)
                state=compare(output/'reference'/name,directory)
                life=json.loads((directory/'graphics-lifecycle.json').read_text())
                require(life['context_deleted'] and life['successful_presents']>0,'Ground graphics lifecycle incomplete')
                if name=='pb_ground_persistence':saves.append((directory/'Scenarios/BehaviorSnapshot.scn').read_bytes())
                case_results.append(dict(behavior=behavior,windows=state))
            except Exception as error:
                failures.append(f'{name}/render-{render}: {error}')
                case_results.append(dict(status='failed',error=str(error)))
                if (directory/'flight-state.csv').is_file() and len(histories)<len(case_results):
                    histories.append((directory/'flight-state.csv').read_bytes())
        independent=len(histories)==2 and histories[0]==histories[1]
        if not independent:failures.append('Ground physics depends on rendering frequency: '+name)
        if saves and (len(saves)!=2 or saves[0]!=saves[1]):failures.append('Landed serializer depends on rendering frequency: '+name)
        results[name]=dict(render_frequency_independent=independent,runs=case_results)
        (output/'ground-flight-progress.json').write_text(json.dumps(dict(cases=results,failures=failures),indent=2)+'\n')
    if any(c['id']=='pb_ground_reload' for c in selected):
        try:results['landed_roundtrip']=roundtrip(output/'pb_ground_persistence-render-4',output/'pb_ground_reload-render-4')
        except Exception as error:failures.append('Landed round trip: '+str(error))
    results['reference_run']=provenance['run_id'];results['failures']=failures
    results['complete_suite']=len(selected)==len(CASES)
    results['status']='failed' if failures else 'passed' if results['complete_suite'] else 'passed focused checks'
    (output/'ground-flight-verification.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
