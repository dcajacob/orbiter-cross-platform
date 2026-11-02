#!/usr/bin/env python3
"""Capture controlled ShuttlePB ground flights in the pinned Windows application."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
from behavior_suite import stage,compare,rows,FILES
from mesa_runtime import require,digest
HERE=Path(__file__).resolve().parent
MANIFEST=json.loads((HERE/'cases.json').read_text())
CASES=[dict(c,fixed_step=MANIFEST['fixed_step'],epoch=MANIFEST['epoch'],budgets='contact',target='PB') for c in MANIFEST['cases']]

def validate(directory,case):
    own=[r for r in rows(directory/'behavior-state.csv') if r['object']=='PB']
    require(len(own)==case['frames']+1,'Missing finalized ShuttlePB samples')
    require(all(r['class']=='ShuttlePB' for r in own),'Stock ShuttlePB was replaced')
    require(any(abs(float(r['altitude_mean'])-float(r['altitude_agl']))>100 for r in own),
            'Real nonzero Edwards elevation is required')
    require(max(float(r['density']) for r in own)>.1,'Actual Earth atmosphere is missing')
    identifier=case['id']
    transitions=[int(b['tick']) for a,b in zip(own,own[1:]) if a['ground']!=b['ground']]
    if identifier=='pb_atmosphere':
        require(max(float(r['drag']) for r in own)>1 and max(float(r['dynamic_pressure']) for r in own)>100,
                'Stock aerodynamic forces were not exercised')
        require(max(float(r['altitude_agl']) for r in own)>1000,'Airborne atmosphere setup failed')
    elif identifier=='pb_contact':
        require(own[0]['ground']=='0' and any(r['ground']=='1' for r in own),'Descending ShuttlePB did not contact terrain')
    elif identifier=='pb_takeoff_landing':
        require(max(float(r['altitude_agl']) for r in own)>5,'ShuttlePB did not lift off')
        airborne=[i for i,r in enumerate(own) if r['ground']=='0' and float(r['altitude_agl'])>5]
        require(airborne and any(r['ground']=='1' for r in own[airborne[-1]+1:]),'ShuttlePB did not return to ground contact')
        require(own[-1]['ground']=='1' and float(own[-1]['altitude_agl'])<3,'ShuttlePB did not finish on the real ground')
        require(float(own[-1]['fuel'])<float(own[0]['fuel']),'Powered takeoff consumed no propellant')
    else:
        require(all(r['ground']=='1' for r in own),'Landed ShuttlePB lost terrain contact')
    if identifier=='pb_ground_persistence':
        require((directory/'Scenarios/BehaviorSnapshot.scn').is_file(),'Original landed save missing')
    return dict(samples=len(own),ground_transition_ticks=transitions,
                maximum_altitude_agl_m=max(float(r['altitude_agl']) for r in own),
                maximum_drag_n=max(float(r['drag']) for r in own),final_fuel_kg=float(own[-1]['fuel']))

def roundtrip(saved,reloaded):
    before=next(r for r in rows(saved/'behavior-state.csv') if r['object']=='PB' and int(r['tick'])==MANIFEST['checkpoint_tick'])
    after=next(r for r in rows(reloaded/'behavior-state.csv') if r['object']=='PB' and r['tick']=='0')
    require(before['ground']==after['ground']=='1' and before['class']==after['class']=='ShuttlePB',
            'Original serializer lost landed/module state')
    require(abs(float(before['mjd'])-float(after['mjd']))<=1e-10,'Landed round trip changed finalized epoch')
    from behavior_suite import distance,quaternion,quaternion_angle
    p=distance([float(before[k]) for k in ('rx','ry','rz')],[float(after[k]) for k in ('rx','ry','rz')])
    v=distance([float(before[k]) for k in ('vx','vy','vz')],[float(after[k]) for k in ('vx','vy','vz')])
    angle=quaternion_angle(quaternion(before),quaternion(after))
    # Landed saves use POS/HEADING/ALT, not the free-flight RPOS/RVEL serializer.
    # Preserve and compare this measured Windows round trip when checking Linux.
    require(p<=1 and v<=.1 and angle<=1e-3,'Original landed round trip exceeds declared contact budgets')
    return dict(position_m=p,velocity_m_s=v,rotation_rad=angle)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('orbiter','data','planets','output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--compare',type=Path);p.add_argument('--configuration',choices=('Debug','Release'));a=p.parse_args()
    require(a.output is not None,'Explicit output directory required')
    if a.compare:
        report={c['id']:compare(a.compare/c['id'],a.output/c['id'],c) for c in CASES}
    else:
        require(sys.platform=='win32','Original ground-flight capture requires native Windows')
        require(all((a.orbiter,a.data,a.planets,a.configuration)),'Missing reference capture input')
        a.output.mkdir(parents=True,exist_ok=False);report={}
        for c in CASES:
            checkpoint=a.output/'pb_ground_persistence/Scenarios/BehaviorSnapshot.scn' if c['fixture']=='reload' else None
            def setup(directory):
                if c['fixture']!='reload':(directory/'Scenarios/Behavior.scn').write_bytes((HERE/'Edwards-ShuttlePB.scn').read_bytes())
            for suffix in ('','-repeat'):
                # before_launch supplies the pinned ground fixture before invocation hashes are recorded.
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),a.output/(c['id']+suffix),c,checkpoint,setup)
            first=a.output/c['id'];repeat=a.output/(c['id']+'-repeat')
            report[c['id']]=dict(comparison=compare(first,repeat,c),behavior=validate(first,c))
            report[c['id']]['run_inputs_sha256']={name:digest(first/name) for name in
                ('Orbiter.cfg','Scenarios/Behavior.scn','behavior-case.txt','invocation.json')}
            for name in FILES:require((first/name).read_bytes()==(repeat/name).read_bytes(),'Ground-flight repeat differs: '+name)
        report['landed_roundtrip']=roundtrip(a.output/'pb_ground_persistence',a.output/'pb_ground_reload')
        runtime=json.loads((a.orbiter.parent/'test-runtime.json').read_text())
        require(runtime['source_commit']==MANIFEST['application_source'],'Wrong pre-ground-flight Windows application')
        report['runtime']=runtime
        report['driver_source']=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        report['input_sha256']={str(path.relative_to(ROOT)):digest(path) for path in
            (HERE/'cases.json',HERE/'Schedules.h',HERE/'Edwards-ShuttlePB.scn',ROOT/'Tests/Production/BehaviorDriver.cpp',ROOT/'Tests/Production/Fixtures/Orbiter.cfg')}
    (a.output/'ground-flight-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
