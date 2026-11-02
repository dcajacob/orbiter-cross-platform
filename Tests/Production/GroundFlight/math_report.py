#!/usr/bin/env python3
"""Report read-only math differences; this tool never accepts a flight or changes a reference."""
import argparse,csv,hashlib,json,math,struct
from decimal import Decimal,localcontext
from pathlib import Path

def bits(value):
    raw=struct.unpack('>Q',struct.pack('>d',value))[0]
    return (~raw)&((1<<64)-1) if raw>>63 else raw|(1<<63)

def nearest_trig(value,cosine):
    # Independent high precision Taylor series, only for the small observed
    # angles. This diagnostic is never linked to Orbiter's propagation code.
    if abs(value)>7:raise ValueError('Diagnostic series requires an angle within seven radians')
    with localcontext() as context:
        context.prec=110;x=Decimal.from_float(value)
        term=Decimal(1) if cosine else x;total=term;index=0
        while True:
            index+=1
            denominator=(2*index-1)*(2*index) if cosine else (2*index)*(2*index+1)
            term*=-x*x/Decimal(denominator);total+=term
            if abs(term)<Decimal('1e-105'):return float(total)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('windows','native','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();windows=list(csv.DictReader(args.windows.open()));native=list(csv.DictReader(args.native.open()))
    if len(windows)>len(native) or not windows:raise ValueError('Incomplete observation history')
    first={};same_input={}
    functions={f'{fn}_{angle}':(angle,fn=='cos') for fn in ('sin','cos') for angle in ('rotation','latitude','longitude')}
    for reference,candidate in zip(windows,native):
        if reference.keys()!=candidate.keys() or reference['tick']!=candidate['tick'] or reference['seconds']!=candidate['seconds']:
            raise ValueError('Observation indices or schema differ')
        for field in reference:
            left,right=float(reference[field]),float(candidate[field])
            if not math.isfinite(left) or not math.isfinite(right):raise ValueError('Nonfinite math observation')
            if left==right:continue
            first.setdefault(field,dict(tick=int(reference['tick']),windows=left,native=right,difference=right-left))
            if field in functions:
                angle,cosine=functions[field];argument=float(reference[angle])
                if argument==float(candidate[angle]):
                    record=same_input.setdefault(field,dict(samples=0,max_ulps=0,first=None))
                    distance=abs(bits(left)-bits(right));record['samples']+=1;record['max_ulps']=max(record['max_ulps'],distance)
                    if record['first'] is None:record['first']=dict(tick=int(reference['tick']),argument=argument,
                        windows=left,native=right,nearest=nearest_trig(argument,cosine),ulps=distance)
    result=dict(status='diagnostic only',windows_samples=len(windows),native_samples=len(native),
        input_sha256={name:hashlib.sha256(getattr(args,name).read_bytes()).hexdigest() for name in ('windows','native')},
        first_differences=first,same_input_trigonometry=same_input,
        interpretation='Primitive differences do not establish the cause of the full contact divergence; flight acceptance remains separate.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(same_input,indent=2))
if __name__=='__main__':main()
