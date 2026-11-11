#!/usr/bin/env python3
"""Reuse the unchanged original Windows four-scene protocol with the freshly rebuilt v2 SDK."""
import csv,hashlib,json,math,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'Tests/Production/Closeout')]
from contracts import require,sha,load,atomic_json
from PhysicsV2.transforms import replace_once
SOURCE=load(HERE/'origins.json')['windows']['source']


def shader_plan(sdk_path,owner,config,collector,cell):
    sdk=load(sdk_path);manifest=load(Path(sdk['runtime'])/'test-runtime.json');require(sdk['compiled_source']==manifest['source_commit']==SOURCE,'Exact actual v2 shader/SDK owner required')
    names=subprocess.check_output(['git','-C',str(owner),'ls-tree','-r','--name-only',SOURCE,'--','OVP/OGLClient/shaders'],text=True).splitlines()
    require(names and {'Constellations.vs','Constellations.fs','Common.inc','LogDepth.inc','Types.inc','Uniforms.inc'}<={Path(n).name for n in names},'Every original compiled renderer shader/include required')
    files={}
    for name in names:
        body=(owner/name).read_bytes();immutable=subprocess.check_output(['git','-C',str(owner),'show',SOURCE+':'+name])
        require(body.replace(b'\r\n',b'\n')==immutable.replace(b'\r\n',b'\n') and hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==sdk['source_guard_sha256_lf'][name],'Actual v2 shader source differs from compiled owner')
        files['Modules/OGLClient/'+Path(name).name]=dict(source=name,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
    return dict(physics_version='assembly-contact-v2',compiled_source=SOURCE,files=files,source_shader_bytes_modified=False,qualification_granted=False)


def prepared_body():
    path=ROOT/'Tests/Production/Closeout/capture_failed_normal_windows.py';body=path.read_text()
    require(body.replace('\r\n','\n')==subprocess.check_output(['git','-C',str(ROOT),'show','07044f8ed28748e359a3a15448478ed2d8030c16:'+path.relative_to(ROOT).as_posix()]).decode().replace('\r\n','\n'),'Complete original Windows observer protocol must remain unchanged')
    body=replace_once(body,"APPLICATION='c08f93151827949ee3ad498f8021f35c11753fde'",'APPLICATION='+repr(SOURCE))
    body=body.replace("ROOT/'out/failed-normal-Windows'","ROOT/'out/physics-v2-Windows'")
    body=replace_once(body,"protocol='phase6-four-original-failed-normal-Windows-diagnostic-v1'","protocol='phase6-four-original-scenes-fresh-physics-v2-Windows'")
    body=replace_once(body,'import current_client_shaders as shaders','from windows_capture import shader_plan')
    body=replace_once(body,'plan=shaders.build_plan(','plan=shader_plan(')
    return body


def inspect():
    sys.path.insert(0,str(ROOT/'Tests/Production/StockScenarios'))
    from inventory import initial_ships
    config=os.environ['CONFIGURATION'];folder=ROOT/'out/physics-v2-Windows'/config;report=load(folder/'collection.json')
    require(report['application_source']==SOURCE and report['status']=='completed-diagnostic-only' and not report['failed_cells'] and report['actual_scene_processes']==8,'All eight actual v2 Windows scene processes must complete')
    expected=load(ROOT/'Tests/Production/Closeout/failed-normal-admission-v4.lock.json')['failed_cases'];pids=set();cases={}
    for mode in ('automatic','sse2'):
        for scene,number in expected.items():
            key=mode+'-'+number;case=report['cases'][key];path=folder/key;receipt=load(path/'process-receipt.json')
            require(case['error'] is None and not case['first_nonfinite'] and receipt['actual_returncode']==0 and receipt['timed_out'] is False and receipt['actual_pid'] not in pids,'Every original Windows clock must end cleanly in its unique real process')
            pids.add(receipt['actual_pid']);rows=list(csv.DictReader((path/'stock-vessel-state.csv').open()));groups={}
            for row in rows:
                groups.setdefault(int(row['tick']),[]).append(row)
                for k,v in row.items():
                    if k not in ('object','class'):require(v is not None and math.isfinite(float(v)),'Nonfinite new Windows state')
            required={(n,k.lower()) for n,k in initial_ships((ROOT/'Scenarios'/scene).read_text()).items()}
            require(set(groups)==set(range(61)) and all(len(g)==len(required) and {(r['object'],r['class'].lower()) for r in g}==required for g in groups.values()),'Complete original vessel roster at every one of61ticks required')
            cases[key]=dict(scene=scene,actual_pid=receipt['actual_pid'],actual_returncode=0,all_numeric_columns_finite=True,complete_original_vessel_roster=True,finalized_ticks=61,rows=len(rows),state_sha256=sha(path/'stock-vessel-state.csv'))
    atomic_json(folder/'independent-scene-inspection.json',dict(status='passed-all-four-original-scenes-both-math-modes-only',physics_version='assembly-contact-v2',compiled_source=SOURCE,configuration=config,actual_processes=len(pids),cases=cases,qualification_granted=False,phase6_complete=False))


def main():
    if sys.argv[1:]==['--inspect']:inspect();return
    exec(compile(prepared_body(),str(HERE/'windows_capture.py'),'exec'),{'__name__':'__main__','__file__':str(HERE/'windows_capture.py')})


if __name__=='__main__':main()
