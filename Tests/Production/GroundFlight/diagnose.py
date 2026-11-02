#!/usr/bin/env python3
"""Observe Windows math without changing any frozen input or reference byte."""
import argparse,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.dont_write_bytecode=True;sys.path.insert(0,str(HERE.parent))
from reference import CASES,validate
from frozen import verify
from behavior_suite import stage
from mesa_runtime import require
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);a=p.parse_args()
    require(sys.platform=='win32','Windows SDK/math observation requires Windows')
    proof=verify();case=next(c for c in CASES if c['id']=='pb_takeoff_landing')
    def setup(directory):
        (directory/'Scenarios/Behavior.scn').write_bytes((HERE/'Edwards-ShuttlePB.scn').read_bytes())
        (directory/'Orbiter.cfg').write_text((HERE/'Orbiter.cfg').read_text()+'\nACTIVE_MODULES\n  ProductionBehaviorDriver\n  ProductionGroundMathDriver\nEND_MODULES\n',encoding='ascii')
    a.output.mkdir(parents=True,exist_ok=False);directory=a.output/'pb_takeoff_landing'
    stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,case,None,setup);validate(directory,case)
    with zipfile.ZipFile(HERE.parent/'GroundReference'/proof['artifacts'][a.configuration]['path']) as original:
        for name in ('behavior-state.csv','behavior-propellant.csv','behavior-animations.csv'):
            require((directory/name).read_bytes()==original.read('production-behavior/pb_takeoff_landing/'+name),
                    'Math observer changed the original physical trace: '+name)
    (a.output/'math-observation.json').write_text(json.dumps(dict(status='passed observation-only',reference_run=proof['run_id'],configuration=a.configuration),indent=2)+'\n')
if __name__=='__main__':main()
