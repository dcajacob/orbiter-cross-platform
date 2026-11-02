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
from comparison import compare_states
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--disable-fma3',action='store_true',help='Separate Windows runtime sensitivity experiment; never an accepted reference');a=p.parse_args()
    require(sys.platform=='win32','Windows SDK/math observation requires Windows')
    proof=verify();case=next(c for c in CASES if c['id']=='pb_takeoff_landing')
    def setup(directory):
        (directory/'Scenarios/Behavior.scn').write_bytes((HERE/'Edwards-ShuttlePB.scn').read_bytes())
        dispatch='  ProductionGroundMathDispatch\n' if a.disable_fma3 else ''
        (directory/'Orbiter.cfg').write_text((HERE/'Orbiter.cfg').read_text()+'\nACTIVE_MODULES\n'+dispatch+'  ProductionBehaviorDriver\n  ProductionGroundMathDriver\nEND_MODULES\n',encoding='ascii')
    a.output.mkdir(parents=True,exist_ok=False);directory=a.output/'pb_takeoff_landing'
    stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,case,None,setup);validate(directory,case)
    result=dict(status='passed observation-only',reference_run=proof['run_id'],configuration=a.configuration)
    with zipfile.ZipFile(HERE.parent/'GroundReference'/proof['artifacts'][a.configuration]['path']) as original:
        for name in ('behavior-state.csv','behavior-propellant.csv','behavior-animations.csv'):
            expected=original.read('production-behavior/pb_takeoff_landing/'+name)
            if not a.disable_fma3:require((directory/name).read_bytes()==expected,'Math observer changed the original physical trace: '+name)
            elif name=='behavior-state.csv':
                baseline=a.output/'frozen-state.csv';baseline.write_bytes(expected)
        if a.disable_fma3:
            dispatch=json.loads((directory/'math-dispatch.json').read_text())
            require(dispatch['diagnostic_only'] and dispatch['selected_fma3']==0,'Requested Windows runtime math path was not selected')
            result.update(status='completed sensitivity diagnostic',dispatch=dispatch)
            try:result['frozen_comparison']=compare_states(baseline,directory/'behavior-state.csv')
            except Exception as error:result['frozen_comparison']=dict(status='outside frozen acceptance',error=str(error))
    (a.output/'math-observation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
