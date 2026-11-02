#!/usr/bin/env python3
"""Qualify a controlled upright landing in the unchanged original Windows application."""
import argparse,hashlib,json,math,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.dont_write_bytecode=True;sys.path.insert(0,str(HERE.parent));sys.path.insert(0,str(HERE.parent/'GroundFlight'))
from frozen import verify as verify_frozen
from reference import validate as validate_ground
from comparison import compare_windows
from behavior_suite import stage,rows,FILES
from mesa_runtime import require,digest
MANIFEST=json.loads((HERE/'case.json').read_text())
CASE=dict(id=MANIFEST['driver_case_id'],frames=MANIFEST['frames'],fixed_step=MANIFEST['fixed_step'],epoch=MANIFEST['epoch'],fixture='ground',budgets='contact',target='PB')

def validate(directory):
    result=validate_ground(directory,CASE);states=[r for r in rows(directory/'behavior-state.csv') if r['object']=='PB']
    requirements=MANIFEST['physical_requirements'];tilts=[]
    for row in states:
        position=[float(row[k]) for k in ('rx','ry','rz')];radius=math.sqrt(sum(x*x for x in position))
        cosine=sum(float(row[f'm{i}2'])*position[i-1] for i in range(1,4))/radius
        tilts.append(math.acos(max(-1.,min(1.,cosine))))
    require(max(tilts)<=requirements['maximum_body_up_tilt_rad'],'The vessel tipped: landed status alone is insufficient')
    require(result['maximum_altitude_agl_m']>=requirements['minimum_peak_altitude_agl_m'],'Controlled takeoff did not reach required height')
    peak=max(range(len(states)),key=lambda i:float(states[i]['altitude_agl']))
    touchdowns=[i for i in range(peak+1,len(states)) if states[i-1]['ground']=='0' and states[i]['ground']=='1']
    require(touchdowns,'No return touchdown after the peak altitude')
    speed=max(float(states[j]['airspeed']) for i in touchdowns for j in (i-1,i))
    require(speed<=requirements['maximum_touchdown_airspeed_m_s'],'Controlled touchdown was too fast')
    return dict(result,maximum_body_up_tilt_rad=max(tilts),final_body_up_tilt_rad=tilts[-1],maximum_touchdown_airspeed_m_s=speed)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','output','compare'):p.add_argument('--'+name,type=Path)
    p.add_argument('--configuration',choices=('Debug','Release'));a=p.parse_args();require(a.output is not None,'Explicit output required')
    verify_frozen()
    if a.compare:
        left=a.compare/'controlled-landing';right=a.output/'controlled-landing';validate(left);validate(right)
        report=dict(status='passed original Windows cross-configuration qualification',comparison=compare_windows(left,right))
    else:
        require(sys.platform=='win32' and all((a.orbiter,a.data,a.planets,a.configuration)),'Original Windows application and locked data required')
        a.output.mkdir(parents=True,exist_ok=False)
        def setup(directory):
            fixture=HERE.parent/'GroundFlight'
            (directory/'Scenarios/Behavior.scn').write_bytes((fixture/'Edwards-ShuttlePB.scn').read_bytes())
            (directory/'Orbiter.cfg').write_text((fixture/'Orbiter.cfg').read_text()+'\nACTIVE_MODULES\n  ProductionLandingDriver\nEND_MODULES\n',encoding='ascii')
        for suffix in ('','-repeat'):
            stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),a.output/('controlled-landing'+suffix),CASE,None,setup)
            validate(a.output/('controlled-landing'+suffix))
        first=a.output/'controlled-landing';repeat=a.output/'controlled-landing-repeat'
        comparison=compare_windows(first,repeat)
        for name in FILES:require((first/name).read_bytes()==(repeat/name).read_bytes(),'Original controlled landing repeat differs: '+name)
        report=dict(status='repeatable original Windows candidate; cross-configuration qualification required',configuration=a.configuration,
            behavior=validate(first),repeat=comparison,application=json.loads((a.orbiter.parent/'test-runtime.json').read_text()),
            driver_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            input_sha256_lf={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for path in (HERE/'Controls.h',HERE/'Driver.cpp',HERE/'case.json',HERE/'capture.py')},
            driver_binary_sha256=digest(a.orbiter.parent/'Modules/Plugin/ProductionLandingDriver.dll'))
        require(report['application']['source_commit']==MANIFEST['application_source'],'Wrong pre-flight Windows application')
    (a.output/'controlled-landing-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
