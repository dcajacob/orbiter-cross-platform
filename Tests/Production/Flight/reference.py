#!/usr/bin/env python3
"""Observe additional flight/persistence behavior in the pinned pre-flight Windows engine."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from behavior_suite import stage,compare,FILES
from mesa_runtime import require,digest
CASES=[dict(id=name,frames=frames,fixed_step=.25,fixture=fixture,budgets='orbital',epoch=51982.5,target='PB')
       for name,frames,fixture in [('manual_flight',980,'orbit'),('pb_persistence',60,'orbit'),('pb_reload',60,'reload')]]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('orbiter','data','planets','output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--compare',type=Path);p.add_argument('--configuration');a=p.parse_args()
    if a.compare:
        report={c['id']:compare(a.compare/c['id'],a.output/c['id'],c) for c in CASES}
    else:
        require(sys.platform=='win32','Native Windows production reference required')
        a.output.mkdir(parents=True,exist_ok=False);report={}
        for c in CASES:
            checkpoint=a.output/'pb_persistence/Scenarios/BehaviorSnapshot.scn' if c['id']=='pb_reload' else None
            for suffix in ('','-repeat'):
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),a.output/(c['id']+suffix),c,checkpoint)
            first=a.output/c['id'];repeat=a.output/(c['id']+'-repeat')
            report[c['id']]=compare(first,repeat,c)
            for n in FILES:require((first/n).read_bytes()==(repeat/n).read_bytes(),'Nonidentical flight repeat: '+n)
        report['runtime']=json.loads((a.orbiter.parent/'test-runtime.json').read_text())
    (a.output/'flight-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
