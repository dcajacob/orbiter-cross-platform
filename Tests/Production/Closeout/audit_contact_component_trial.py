#!/usr/bin/env python3
"""Independently replay original readers and complete finite-state checks on published trial bytes."""
import csv,hashlib,json,math,os,shutil,subprocess,sys,zipfile
from pathlib import Path
from contracts import ROOT,atomic_json,load,require,sha
from frozen_admission_api import candidate,hosted
from restore_rejection_input_bundle import restore
from rejection_input_bundle import safe
import hosted_contact_component_trial as producer
RUN=42964822330
SOURCE='fb619df9b44550d2797cab0b92b602813f5e5319'
PRIOR_ID=13827115523
PRIOR_SHA='18da8a441c1ed94248650f858a89b6836613240c4edc8516f2e24142b945cc0d'
BASE=ROOT/'out/contact-component-independent'
HEADER='tick,frame,seconds,mjd,object,class,rx,ry,rz,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,altitude_agl,altitude_mean,airspeed,density,dynamic_pressure,lift,drag,ground,dock,focus,navmask,attached'.split(',')
STRINGS={'object','class','dock','focus','attached'}


def api_binding(api,archive):
    r=api['run'];a=api['artifact'];jobs=api['jobs']
    require(r['id']==RUN and r['head_sha']==SOURCE and r['head_branch']=='qualification/assembly-contact-component-v3' and r['run_attempt']==1 and r['status']=='completed' and r['conclusion'] in ('success','failure') and r['repository']['full_name']=='dcajacob/orbiter-cross-platform' and r['repository']['private'] is False,'Exact completed public diagnostic source required')
    require(len(jobs)==1 and jobs[0]['name']=='trial' and jobs[0]['head_sha']==SOURCE and jobs[0]['run_id']==RUN and jobs[0]['status']=='completed' and jobs[0]['conclusion']==r['conclusion'] and jobs[0]['labels']==['ubuntu-24.04'],'Exact completed standard trial job required')
    require(a['name']=='assembly-contact-component-trial-raw' and a['expired'] is False and a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==SOURCE and archive.stat().st_size==a['size_in_bytes'] and 'sha256:'+sha(archive)==a['digest'],'Exact published trial raw API length/SHA/source required')


def restore_trial(archive,index,root=ROOT):
    return restore(root,archive,index,Path(root)/'out/rejection-independent/contact-component')


def flight(path,ships):
    expected={(n,c.lower()) for n,c in ships.items()};groups={}
    with path.open() as f:
        reader=csv.DictReader(f);require(reader.fieldnames==HEADER,'Complete unchanged original flight observation columns required')
        for row in reader:
            require(None not in row and all(v is not None for v in row.values()),'Truncated flight record')
            for key in HEADER:
                if key not in STRINGS:require(math.isfinite(float(row[key])),'Nonfinite original flight field '+key+' at tick '+row['tick'])
            tick=int(row['tick']);require(float(row['seconds'])==tick*.25 and int(row['frame'])==tick,'Original point25 clock/frame required')
            groups.setdefault(tick,[]).append(row)
    require(set(groups)==set(range(61)),'All original61complete ticks required')
    for group in groups.values():require(len(group)==len(expected) and {(v['object'],v['class'].lower()) for v in group}==expected,'Complete unchanged original initialized vessel roster required at every tick')
    return dict(ticks=61,vessels=len(expected),all_original_numeric_fields_finite=True,original_point25_clock=True,sha256=sha(path))


def original_inspection(folder,case,name,code,destination):
    for relative in ('Tests/Production/StockScenarios/run.py','Tests/Production/StockScenarios/intentional_exit.py','Tests/Production/GeneralApiCorrection/admission.py'):
        require((ROOT/relative).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+relative],cwd=ROOT),'Unchanged original scenario reader required')
    metadata=destination.with_suffix('.original-case.json');atomic_json(metadata,case)
    program="import sys,pathlib,json;sys.path.insert(0,str(pathlib.Path('Tests/Production/StockScenarios').resolve()));import run as original;result=original.inspect(pathlib.Path(sys.argv[1]),json.load(open(sys.argv[2])),int(sys.argv[4]),scenario=sys.argv[3],profile='Debug-automatic');pathlib.Path(sys.argv[5]).write_text(json.dumps(result,indent=2)+'\\n')"
    subprocess.run([sys.executable,'-B','-c',program,str(folder),str(metadata),name,str(code),str(destination)],cwd=ROOT,check=True)
    return load(destination)


def main():
    hosted();require(not (BASE/'verification.json').exists(),'Fresh independent trial reader required')
    api=load(BASE/'api.json');archive=BASE/'producer.zip';api_binding(api,archive);raw=BASE/'selected';raw.mkdir();prefix='out/contact-component-trial/Debug-automatic/'
    selected={}
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist();names=[safe(i.filename).as_posix() for i in entries];require(len({n.casefold() for n in names})==len(names),'No ambiguous/unsafe original ZIP members permitted')
        for ending in ('/trial-raw.tar.gz','/trial-raw-index.json','/collection.json','/frozen-postflight.json','/compiler.json','/original-methods.cpp','/original-methods.so','/contact-initialization-prototype.cpp','/contact-initialization-prototype.so'):
            found=[i for i in entries if i.filename.endswith(ending)];require(len(found)==1 and found[0].file_size<512*1024**2,'One bounded original trial witness required: '+ending)
            p=raw/ending[1:]
            with z.open(found[0]) as source,p.open('xb') as target:shutil.copyfileobj(source,target,1024**2)
            selected[ending]=p
    index=load(raw/'trial-raw-index.json');require(all(n.startswith(prefix) for n in index['files']),'Only the original trial output subtree may restore')
    restored=restore_trial(raw/'trial-raw.tar.gz',index);out=ROOT/prefix
    require(sha(out/'collection.json')==sha(raw/'collection.json') and sha(out/'frozen-postflight.json')==sha(raw/'frozen-postflight.json'),'Outer and exact restored final records differ')
    record=load(out/'collection.json');post=load(out/'frozen-postflight.json');compiler=load(raw/'compiler.json');lock=candidate()
    generator=Path(producer.__file__);require(generator.read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+generator.relative_to(ROOT).as_posix()],cwd=ROOT),'Exact original declared prototype generator required')
    require(record['phase6_complete'] is False and record['native_admission_qualified'] is False and record['original_source_guards_unchanged'] is True,'Prototype must preserve original guards and remain explicitly unqualified')
    require(record['collector_source']==SOURCE and record['frozen_application_source']==producer.SOURCE and record['actual_application_rebuilt'] is False and record['candidate_id']==compiler['candidate_id']==post['candidate_id']==lock['id'] and post['status']=='passed' and not post['changed'],'Actual unchanged frozen runtime/prototype postflight required')
    require(compiler['source']==SOURCE and compiler['host_macros']['actual_cpp_abi']==compiler['actual_engine_cpp_abi'] and compiler['original_source_guard_modified'] is False,'Actual exact original SDK/compiler ABI proof required')
    for mode,item in compiler['variants'].items():
        expected,_=producer.source_variant(mode);require((raw/(mode+'.cpp')).read_text()==expected and sha(raw/(mode+'.cpp'))==item['cpp_sha256'] and sha(raw/(mode+'.so'))==item['library_sha256'] and item['actual_returncode']==0 and item['actual_pid']>0 and '-fsanitize=address,undefined' in item['argv'],'Complete declared source/actual compiled component identity differs')
    prior=BASE/'prior.zip';pa=load(BASE/'prior-api.json')['artifact'];require(pa['id']==PRIOR_ID and pa['size_in_bytes']==prior.stat().st_size==324434 and pa['digest']=='sha256:'+PRIOR_SHA and sha(prior)==PRIOR_SHA,'Exact independently verified original failed-trace archive required')
    with zipfile.ZipFile(prior) as z:
        original=json.loads(z.read(next(n for n in z.namelist() if n.endswith('/inspection.json'))));require(original['source_run_id']==42926670117 and original['original_source']=='2cf4163dd55cab88337bcdf5890a4a34c1b3334b','Original failed source identity differs')
        traces={number:z.read(next(n for n in z.namelist() if n.endswith('/original-partials/'+number+'/flight-state.csv'))) for number in load(producer.HERE/'failed-normal-admission-v4.lock.json')['failed_cases'].values()}
    cases=load(producer.HERE/'failed-normal-admission-v4.lock.json')['failed_cases'];require(set(record['trials'])=={'unchanged-application','original-methods','contact-initialization-prototype'},'Every declared trial mode required');pids=set();results={};passes=0
    for mode,values in record['trials'].items():
        require(set(values)==set(cases),'Every original failed scene required in every mode');results[mode]={}
        for name,number in cases.items():
            item=values[name];folder=out/(mode+'-'+number);receipt=load(folder/'process-receipt.json');require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_collector_pid']==item['actual_pid'] and receipt['actual_returncode']==item['actual_exitcode'] and item['actual_pid'] not in pids,'Distinct completed actual simulator PID/exit required');pids.add(item['actual_pid'])
            inspected=original_inspection(folder,original['cases'][name]['original_case'],name,item['actual_exitcode'],BASE/(mode+'-'+number+'-inspection.json'));require(inspected==item['original_inspection'],'Published original scenario reader result differs from fresh unchanged original reader')
            if mode!='unchanged-application':require(set((folder/'actual-component-calls.txt').read_text().splitlines())=={'defaults','moments','surface'},'Actual dispatch of every declared method required')
            result=dict(original_reader=inspected['status'],actual_pid=item['actual_pid'],actual_exitcode=item['actual_exitcode'])
            if mode!='contact-initialization-prototype':require((folder/'flight-state.csv').read_bytes()==traces[number] and inspected['status']=='failed','Both unchanged controls must reproduce complete original partial bytes')
            elif inspected['status']=='passed' and item['actual_exitcode']==0:
                result['complete_finite_state']=flight(folder/'flight-state.csv',original['cases'][name]['original_case']['initial_ships']);passes+=1
            results[mode][name]=result
    require(all(sha(ROOT/n)==v['sha256'] for n,v in index['files'].items()),'Original restored trial byte changed during independent audit')
    status='independently-validated-physics-prototype-only' if passes==4 else 'independently-reproduced-rejected-physics-prototype'
    require((api['run']['conclusion']=='success')==(passes==4),'Actual source job conclusion contradicts complete prototype outcomes')
    atomic_json(BASE/'verification.json',dict(status=status,source_run_id=RUN,producer_source=SOURCE,auditor_source=os.environ['GITHUB_SHA'],candidate_id=lock['id'],actual_simulator_processes_reaudited=len(pids),new_simulator_processes=0,byte_exact_original_failure_controls=8,prototype_passes=passes,prototype_failures=4-passes,original_raw_closure=restored,results=results,every_original_raw_byte_unchanged=True,production_patch_applied=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False))


if __name__=='__main__':main()
