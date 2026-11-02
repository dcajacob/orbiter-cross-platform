#!/usr/bin/env python3
"""Locate intermediate differences after both observers prove unchanged physics.

This is diagnostic evidence, never a numerical acceptance comparison.
"""
import argparse,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True;HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from mesa_runtime import require,digest

def read(path):
    with path.open() as stream:return [json.loads(line) for line in stream]

def difference(left,right):
    first=None;structure=None;stages={};matched=0
    for a,b in zip(left,right):
        identity=('call','seconds','fraction','dt','stage','point')+(('object',) if 'object' in a or 'object' in b else ())
        if any(a[k]!=b[k] for k in identity) or a['values'].keys()!=b['values'].keys():
            structure=dict(windows={k:a[k] for k in identity},native={k:b[k] for k in identity});break
        matched+=1
        changed=[]
        for key,x in a['values'].items():
            y=b['values'][key];require(math.isfinite(x) and math.isfinite(y),'Nonfinite intermediate observation')
            if x!=y:
                changed.append(dict(field=key,windows=x,native=y,absolute=abs(x-y),
                                    windows_hex=float(x).hex(),native_hex=float(y).hex()))
        if changed:
            item=dict(call=a['call'],seconds=a['seconds'],fraction=a['fraction'],stage=a['stage'],point=a['point'],differences=changed)
            if first is None:first=item
            stages.setdefault(a['stage'],item)
    return dict(windows_rows=len(left),native_rows=len(right),matched_structure_rows=matched,
                first_difference=first,first_by_stage=stages,first_structure_difference=structure)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('windows','native','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for directory in (a.windows,a.native):
        proof=json.loads((directory/'stage-observation.json').read_text())
        require(proof['status']=='passed observation-only proof' and proof['diagnostic_only'],
                'Rejecting observations without byte-identical physical-trace proof')
        for case in proof['cases']:
            require(digest(directory/case['case']/'contact-stages.jsonl')==case['stages_sha256'],'Intermediate observations changed')
    cases={}
    for name in ('impact','controlled'):
        left=a.windows/name/'contact-stages.jsonl';right=a.native/name/'contact-stages.jsonl'
        cases[name]=dict(windows_sha256=digest(left),native_sha256=digest(right),**difference(read(left),read(right)))
    report=dict(diagnostic_only=True,acceptance_override=False,cases=cases)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:case['first_difference'] for name,case in cases.items()},indent=2))
if __name__=='__main__':main()
