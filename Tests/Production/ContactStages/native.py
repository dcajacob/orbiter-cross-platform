#!/usr/bin/env python3
"""Prove isolated native contact instrumentation leaves existing traces unchanged.

These native hashes identify already failing diagnostic inputs. They are never
acceptance references and cannot supersede the frozen Windows flight budgets.
"""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRODUCTION=HERE.parent
sys.path.insert(0,str(PRODUCTION));sys.path.insert(0,str(PRODUCTION/'GroundFlight'))
from mesa_runtime import require,digest
BASELINES={
    'impact':'7c1158c302016e955efec3d4359e071c9bee39f8efc969c6253dab84a5f409d5',
    'controlled':'9d95e73bb66d643d53f4d6cca347296f0ac26bf929fcc91ca9b6865daff45636'}

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output','impact-reference','controlled-reference','instrumentation'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();metadata=json.loads(a.instrumentation.read_text())
    require(metadata['diagnostic_only'] and metadata['insertions_reversible'],'Not an isolated contact diagnostic')
    ground=load('stage_ground_verify',PRODUCTION/'GroundFlight/verify.py')
    sys.path.insert(0,str(PRODUCTION/'ControlledLanding'))
    controlled=load('stage_controlled_verify',PRODUCTION/'ControlledLanding/verify.py')
    ground.verify_frozen();controlled.reference.verify();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    results=[]
    for name in ('impact','controlled'):
        baseline=getattr(a,name+'_reference').resolve()
        require(digest(baseline/'flight-state.csv')==BASELINES[name],'Wrong pre-instrumentation native trace: '+name)
        case=next(c for c in ground.CASES if c['id']=='pb_takeoff_landing') if name=='impact' else controlled.CASE
        directory=out/name;directory.mkdir();tape=out/(name+'.csv')
        tape.write_text(ground.commands(case) if name=='impact' else controlled.commands())
        argv=[str(a.executable.resolve())]
        for arg in ('assets','data','modules','planets'):argv+=['--'+arg,str(getattr(a,arg).resolve())]
        argv+=['--config',str(PRODUCTION/'GroundFlight/Orbiter.cfg'),'--scenario',str(PRODUCTION/'GroundFlight/Edwards-ShuttlePB.scn'),
               '--replay',str(tape),'--evidence',str(directory),'--save',str(directory/'Scenarios/BehaviorSnapshot.scn'),
               '--ticks',str(case['frames']),'--fixed-step',str(case['fixed_step']),'--render-every','4','--run']
        with (directory/'console.log').open('w') as log:
            subprocess.run(argv,cwd=directory,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        checksums={}
        for filename in ('flight-state.csv','flight-controls.csv','flight-animations.csv'):
            require((directory/filename).read_bytes()==(baseline/filename).read_bytes(),
                    'Intermediate observer changed native physical trace: '+name+'/'+filename)
            checksums[filename]=digest(directory/filename)
        stages=directory/'contact-stages.jsonl';require(stages.is_file() and stages.stat().st_size>0,'No native stage observations')
        results.append(dict(case=name,unchanged_physical_trace_sha256=checksums,stages_sha256=digest(stages)))
    report=dict(status='passed observation-only proof',diagnostic_only=True,instrumentation=metadata,cases=results)
    (out/'stage-observation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
