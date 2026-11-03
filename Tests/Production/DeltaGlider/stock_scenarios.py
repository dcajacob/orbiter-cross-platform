#!/usr/bin/env python3
"""Run unchanged DG scenarios whose complete vessel manifests the native host can load."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
SUPPORTED={'deltaglider','dg-s','shuttlepb','projectalpha_iss'}


def vessel_classes(lines):
    ships={}
    inside=False
    for line in lines:
        line=line.strip()
        if line.upper()=='END_SHIPS':break
        if inside:
            if line.upper()=='END':inside=False
        elif line and not line.startswith(';'):
            name,sep,kind=line.partition(':')
            ships[name]=kind.strip() if sep else name
            inside=True
    return ships


def stock_missions():
    for path in sorted((ROOT/'Scenarios').rglob('*.scn')):
        data=path.read_bytes().replace(b'\r\n',b'\n')
        lines=data.decode('cp1252').splitlines()
        begin=next((i for i,s in enumerate(lines) if s.strip().upper()=='BEGIN_SHIPS'),None)
        if begin is None:continue
        ships=vessel_classes(lines[begin+1:])
        classes={c.casefold() for c in ships.values()}
        if classes & {'deltaglider','dg-s'}:
            yield path.relative_to(ROOT/'Scenarios'),ships,classes-SUPPORTED,data


def fly(args,folder,name,ships,data):
    scenario=args.assets/'Scenarios'/name
    if scenario.read_bytes().replace(b'\r\n',b'\n')!=data:raise ValueError('Staged scenario differs from the stock source')
    folder.mkdir()
    config=folder/'Orbiter.cfg'
    config.write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+'\nMenubarMode = 1\nInfobarMode = 0\n')
    (folder/'playback.enabled').touch()
    with (folder/'console.txt').open('w') as console:
        process=subprocess.run([args.executable,'--config',config,'--scenario',scenario,'--assets',args.assets,'--data',args.data,
            '--modules',args.modules,'--planets',args.planets,'--evidence',folder,'--save',folder/'saved.scn',
            '--frames','60','--fixed-step','0.25','--run'],cwd=folder,stdout=console,stderr=subprocess.STDOUT,timeout=180)
    return inspect(folder,ships,process.returncode)


def inspect(folder,ships,exit_code):
    log=(folder/'console.txt').read_text(errors='replace')
    markers=('Lua error:','LuaCall (','Orbiter native production:','runtime error:',
             'ERROR: AddressSanitizer:','ERROR: LeakSanitizer:')
    problems=[line for line in log.splitlines() if any(marker in line for marker in markers)]
    if exit_code:problems.append('process exit '+str(exit_code))
    lifecycle=folder/'graphics-lifecycle.json'
    life=json.loads(lifecycle.read_text()) if lifecycle.exists() else {}
    if life!=dict(rendered_frames=60,successful_presents=60,context_deleted=True):problems.append('Incomplete presentation or teardown')
    state=folder/'playback-state.csv'
    states=list(csv.DictReader(state.read_text().splitlines())) if state.exists() else []
    if [int(r['tick']) for r in states]!=list(range(61)):problems.append('Incomplete finalized state')
    if any(r['object'] not in ships or r['class'].casefold()!=ships[r['object']].casefold() for r in states):
        problems.append('Unexpected focus or vessel class')
    return dict(frames=life.get('successful_presents',0),focus=sorted({r['object'] for r in states}),
                exit_code=exit_code,playback=bool(states and states[0]['playback']=='1'),problems=problems)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args()
    for key,value in vars(args).items():setattr(args,key,value.resolve())
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),missions={})
    for i,(name,ships,other,data) in enumerate(stock_missions()):
        entry=dict(ships=ships,sha256_lf=hashlib.sha256(data).hexdigest(),other_required_classes=sorted(other))
        if not other:
            try:entry.update(fly(args,args.output/f'{i:03d}',name,ships,data))
            except (OSError,ValueError,subprocess.TimeoutExpired) as e:entry['problems']=[str(e)]
            print(name,entry.get('frames'),entry['problems'],flush=True)
        report['missions'][name.as_posix()]=entry
        (args.output/'stock-scenarios.json').write_text(json.dumps(report,indent=2)+'\n')
    failures={n:v['problems'] for n,v in report['missions'].items() if v.get('problems')}
    if failures:raise SystemExit(json.dumps(failures,indent=2))

if __name__=='__main__':main()
