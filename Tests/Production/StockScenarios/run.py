#!/usr/bin/env python3
"""Attempt every unchanged locked stock scenario; retain every failure explicitly."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import time

from inventory import ROOT,corpus,digest,require


def rows(path):
    if not path.exists():return []
    with path.open() as stream:return list(csv.DictReader(stream))


def inspect(out,case,returncode):
    log=(out/'console.log').read_text(errors='replace')
    markers=('Lua error:','LuaCall (','Orbiter native production:','runtime error:',
             'ERROR: AddressSanitizer:','ERROR: LeakSanitizer:','WARNING: ThreadSanitizer:')
    problems=[line for line in log.splitlines() if any(marker in line for marker in markers)]
    if returncode:problems.append('process exit '+str(returncode))
    life_path=out/'graphics-lifecycle.json'
    life=json.loads(life_path.read_text()) if life_path.exists() else {}
    if life!=dict(rendered_frames=60,successful_presents=60,context_deleted=True):
        problems.append('Incomplete sixty-frame presentation or context deletion')
    states=rows(out/'flight-state.csv');groups={}
    for row in states:groups.setdefault(int(row['tick']),[]).append(row)
    expected={(name,kind.lower()) for name,kind in case['ships'].items()}
    if set(groups)!=set(range(61)):problems.append('Incomplete finalized all-vessel ticks')
    for tick,group in groups.items():
        actual={(r['object'],r['class'].lower()) for r in group}
        if len(group)!=len(expected) or actual!=expected:
            problems.append('Incomplete or substituted vessel manifest at tick '+str(tick));break
    if case['dependency_problems']:problems.append('Declared vessel dependencies are incomplete')
    meshes=rows(out/'visual-meshes.csv')
    return dict(status='passed' if not problems else 'failed',problems=problems,returncode=returncode,
        lifecycle=life,finalized_ticks=len(groups),declared_vessels=len(expected),
        observed_vessels=sorted({(r['object'],r['class']) for r in states}),
        initial_mjd=float(states[0]['mjd']) if states else None,
        visual_mesh_records=len(meshes),
        files_sha256={name:digest(out/name) for name in ('console.log','flight-state.csv','visual-meshes.csv',
            'graphics-lifecycle.json','native-window.json','invocation.json') if (out/name).exists()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--inventory-only',action='store_true')
    p.add_argument('--case',action='append')
    p.add_argument('--backend',choices=('x11','wayland'),required=True)
    a=p.parse_args()
    for name in ('executable','assets','data','modules','planets','output'):setattr(a,name,getattr(a,name).resolve())
    report=corpus(a.assets,a.modules)
    require(not a.case or set(a.case)<=set(report['cases']),'Unknown stock scenario selection')
    a.output.mkdir(parents=True,exist_ok=False)
    report.update(status='inventory-only' if a.inventory_only else 'running',phase6_complete=False,
        scope='Unchanged complete 157-scenario corpus; initialization/smoke, not physical interaction or new Windows state/image parity',
        backend=a.backend,engine_default_mjd_without_numeric_date=51982.5,
        source_sha256={str(path.relative_to(ROOT)):digest(path) for path in
            (Path(__file__),Path(__file__).with_name('inventory.py'),ROOT/'Src/Orbiter/Production/NativeApplication.cpp')},
        runtime_sha256=dict(executable=digest(a.executable),renderer=digest(a.modules/'Graphics/OGLClient.so'),
                            vessels=digest(a.executable.parent/'liborbiter_production_vessels.so')))
    manifest=a.output/'stock-scenarios.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    if a.inventory_only:
        print(json.dumps(dict(scenarios=157,inventory_ready=sum(c['inventory_ready'] for c in report['cases'].values()))));return
    try:
        for number,(name,case) in enumerate(report['cases'].items()):
            if a.case and name not in a.case:continue
            out=a.output/f'{number:03d}';out.mkdir()
            (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 0\n')
            argv=[str(a.executable)]
            for key in ('assets','data','modules','planets'):argv+=['--'+key,str(getattr(a,key))]
            argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(a.assets/'Scenarios'/name),
                   '--evidence',str(out),'--save',str(out/'saved.scn'),'--frames','60','--fixed-step','.25','--run']
            (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
            started=time.monotonic()
            try:
                with (out/'console.log').open('w') as console:
                    process=subprocess.run(argv,cwd=out,stdout=console,stderr=subprocess.STDOUT,timeout=180)
                case.update(inspect(out,case,process.returncode))
                window=out/'native-window.json'
                if window.exists() and json.loads(window.read_text())['backend']!=a.backend:
                    case['status']='failed';case['problems'].append('Actual window backend differs')
            except (OSError,ValueError,subprocess.TimeoutExpired) as error:
                case.update(status='failed',problems=[str(error)])
            case.update(output=out.name,elapsed_seconds=time.monotonic()-started)
            print(json.dumps(dict(scenario=name,status=case['status'],ready=case['inventory_ready'],
                                  frames=case.get('lifecycle',{}).get('successful_presents',0),problems=case.get('problems',[]))),flush=True)
            save()
        attempted=[c for c in report['cases'].values() if c['status']!='not-run']
        report['summary']=dict(attempted=len(attempted),passed=sum(c['status']=='passed' for c in attempted),
            failed=sum(c['status']=='failed' for c in attempted),inventory_ready=sum(c['inventory_ready'] for c in report['cases'].values()),
            source_metadata_mismatches=sum(c['locked_inventory_metadata_differs'] for c in report['cases'].values()))
        require(digest(a.executable)==report['runtime_sha256']['executable'] and
                digest(a.modules/'Graphics/OGLClient.so')==report['runtime_sha256']['renderer'] and
                digest(a.executable.parent/'liborbiter_production_vessels.so')==report['runtime_sha256']['vessels'],
                'Application binaries changed during stock sweep')
        report['status']='passed' if len(attempted)==157 and all(c['status']=='passed' for c in attempted) else 'incomplete'
    finally:save()
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
