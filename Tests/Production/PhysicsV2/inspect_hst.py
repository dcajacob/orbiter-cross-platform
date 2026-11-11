#!/usr/bin/env python3
"""Independently retain original-passed and new-failed HST raw state on hosted runners."""
import csv,hashlib,json,math,os,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,load,atomic_json
from inspect_published_numerical_observers import restore_outer
from stream_retained_numerical_inputs import verify


def read_trace(path):
    from audit_contact_component_trial import HEADER,STRINGS
    groups={};problems=[];summary={}
    with path.open() as stream:
        reader=csv.DictReader(stream);require(reader.fieldnames==HEADER,'Exact original HST trace columns required')
        for line,row in enumerate(reader,start=2):
            require(None not in row,'Unexpected extra HST fields')
            tick=int(row['tick']);groups.setdefault(tick,[]).append(row)
            for k in HEADER:
                if k in STRINGS:continue
                try:finite=math.isfinite(float(row[k]))
                except (ValueError,TypeError):finite=False
                if not finite:problems.append(dict(line=line,tick=row['tick'],object=row['object'],field=k,value=row[k]))
    def maximum(group,keys):
        values=[]
        for row in group:
            for key in keys:
                try:value=float(row[key])
                except (ValueError,TypeError):continue
                if math.isfinite(value):values.append(abs(value))
        return max(values) if values else None
    for tick,group in groups.items():
        summary[tick]=dict(objects=len(group),mass={r['object']:r['mass'] for r in group},max_abs_angular_speed=maximum(group,('wx','wy','wz')),max_abs_velocity=maximum(group,('vx','vy','vz')),altitude_agl={r['object']:r['altitude_agl'] for r in group})
    return dict(ticks=groups,per_tick=summary,nonfinite_or_missing=problems)


def main():
    cohort=os.environ['COHORT'];base=ROOT/'out/physics-v2-HST-source'/cohort;api=load(base/'api.json');archive=base/'producer.zip';output=ROOT/'out/physics-v2-HST-inspection'/cohort;output.mkdir(parents=True,exist_ok=False)
    require('sha256:'+sha(archive)==api['artifact']['digest'] and archive.stat().st_size==api['artifact']['size_in_bytes'],'Exact original full HST cohort bytes required')
    prefix='hosted-normal-admission/Release-sse2';raw=prefix+'/capture-raw.tar.gz';outer=output/'outer';members=restore_outer(archive,outer,raw);index=load(outer/prefix/'capture-raw-index.json');rel='out/'+prefix
    requested={rel+'/'+n for n in ('collection.json','independent-full-stock-audit.json','capture/stock-scenarios.json')}
    requested.update(n for n in index['files'] if n.startswith(rel+'/capture/085/') and len(Path(n).parts)==6)
    with zipfile.ZipFile(archive) as z,z.open(raw) as stream:verified,closure=verify(ROOT,stream,index,requested,output/'original-objects')
    capture=ROOT/rel/'capture';report=load(capture/'stock-scenarios.json');name='Satellites and Probes/Hubble Space Telescope/HST Launch.scn';case=report['cases'][name];folder=capture/'085'
    require(case['output']=='085' and report['runtime_identity']['profile']=='Release-sse2' and report['observer_commit']==api['run']['head_sha'] and case['sha256_lf']==hashlib.sha256((ROOT/'Scenarios'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'Original actual HST scenario/source/profile required')
    require(case['status']==('passed' if cohort=='original' else 'failed'),'Preserve both actual original HST conclusions without relabelling')
    kept=output/'actual-HST-output';kept.mkdir()
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in ('.csv','.json','.log','.txt','.cfg','.scn'):(kept/p.name).write_bytes(p.read_bytes())
    trace=read_trace(folder/'flight-state.csv');numbers=trace['nonfinite_or_missing'];summary=trace['per_tick'];groups=trace['ticks']
    if cohort=='original':require(case['status']=='passed' and not numbers and set(groups)==set(range(61)),'Actual old HST must independently have61complete finite ticks')
    atomic_json(output/'verification.json',dict(status='independently-read-actual-'+cohort+'-HST-only',source=api['run']['head_sha'],compiled_source=report['runtime_identity']['runtime_source_commit'],original_status=case['status'],original_problems=case['problems'],full_summary=report['summary'],raw_closure=closure,observed_tick_groups=len(groups),original_reported_finalized_ticks=case['finalized_ticks'],all_nonfinite_or_missing=numbers,first_nonfinite=numbers[:24],per_tick=summary,api_artifact=api['artifact'],new_simulator_processes=0,qualification_granted=False))
    print(json.dumps(dict(cohort=cohort,original_status=case['status'],summary=report['summary'],ticks=len(groups),first_nonfinite=numbers[:8],last_ticks={k:v for k,v in summary.items() if k>=35}),indent=2))


if __name__=='__main__':main()
