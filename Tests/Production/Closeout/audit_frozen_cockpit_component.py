#!/usr/bin/env python3
"""Independently reread published frozen cockpit bytes with every original comparison budget."""
import argparse,csv,importlib.util,json,math,os
from pathlib import Path
import subprocess,sys,zipfile,shutil
from contracts import ROOT,PROFILES,atomic_json,load,require,sha
from frozen_admission_api import candidate,hosted
from restore_rejection_input_bundle import restore
import hosted_frozen_cockpit_component as core

RUN=42954705888
SOURCE='43cf2010c287ccf00b5700a231b71a40c4c8ff32'


def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def original_module(relative,name):
    path=ROOT/'Tests/Production'/relative
    require(path.read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Exact original comparison module source required: '+relative)
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def restore_original(profile,base):
    api=load(base/'api.json');run=api['run'];artifact=api['artifact'];archive=base/'producer.zip';lock=candidate()
    require(run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/frozen-core-cockpit-v2' and
            run['path']=='.github/workflows/phase6-frozen-core-cockpit.yml' and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success' and run['repository']['private'] is False and
            run['repository']['full_name']=='dcajacob/orbiter-cross-platform','Exact completed repaired public cockpit component required')
    jobs=api['jobs'];expected={'controls'}|{'Frozen core cockpit '+p for p in PROFILES}
    require(len(jobs)==5 and {j['name'] for j in jobs}==expected and all(j['head_sha']==SOURCE and j['run_id']==RUN and
            j['status']=='completed' and j['conclusion']=='success' and j['labels']==['ubuntu-24.04'] for j in jobs),
            'Every actual source control and completed original profile job required')
    require(artifact['name']=='frozen-core-cockpit-'+profile+'-raw' and not artifact['expired'] and
            artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE and
            archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],'Exact published raw ZIP API/bytes required')
    raw=base/'selected-raw';raw.mkdir()
    with zipfile.ZipFile(archive) as z:
        for suffix in ('/raw-results.tar.gz','/raw-index.json','/collection.json'):
            found=[i for i in z.infolist() if i.filename.endswith(suffix)]
            require(len(found)==1 and found[0].file_size<512*1024**2,'One bounded exact original raw archive/member required')
            with z.open(found[0]) as incoming,(raw/suffix[1:]).open('xb') as out:shutil.copyfileobj(incoming,out,1024**2)
    index=load(raw/'raw-index.json');prefix='out/frozen-core-cockpit/'+profile+'/'
    require(all(n.startswith(prefix) for n in index['files']),'Original component archive must contain only its actual owned profile')
    proof=restore(ROOT,raw/'raw-results.tar.gz',index,ROOT/'out/rejection-independent'/('core-'+profile))
    output=ROOT/'out/frozen-core-cockpit'/profile;collection=load(output/'collection.json')
    require(sha(output/'collection.json')==sha(raw/'collection.json') and
            collection['protocol']=='phase6-frozen-cockpit-component-v1' and
            collection['status']=='completed-frozen-cockpit-interface-component-only' and collection['collector_source']==SOURCE and
            collection['candidate_id']==lock['id'] and collection['compiled_runtime_source']=='ccc02c8a34bd1f227624d8778a141e8736ae8111' and
            collection['complete_core_gate_qualified'] is False and collection['phase6_complete'] is False,
            'Original exact final guarded component completion required')
    for name,h in collection['original_fixture_sources_sha256'].items():
        require(sha(ROOT/name)==h and (ROOT/name).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT),
                'Every original fixture/comparator source byte required')
    require(sha(output/'native-runtime-system-packages.txt')==collection['native_host_dependencies']['full_inventory_sha256'] and
            load(output/'native-runtime-dependencies.json')==collection['native_host_dependencies'] and
            load(output/'x11.json')==collection['x11'],'Exact recorded native and X11 dependency witnesses required')
    stages=[c for c in collection['commands'] if c['label'].endswith('-unchanged-original-fixtures')]
    require({c['label'] for c in stages}=={p+'-unchanged-original-fixtures' for p in ('cockpit','dialogs','window-dialog','recording')} and
            len(stages)==4 and all(c['actual_pid']>0 and c['actual_returncode']==0 for c in stages),'Four actual original complete fixture groups required')
    require(core.result(output)==collection['core_component_result'],'Original component summary differs from independently reread reports')
    atomic_json(base/'restoration.json',dict(original_api=api,original_raw_closure=proof,collection_sha256=sha(output/'collection.json'),
        every_original_byte_unchanged=True,core_gate_qualified=False))
    return output,index


def audit_instruments(profile,output,refs):
    sys.path[:0]=[str(ROOT/'Tests/Production/Cockpit'),str(ROOT/'Tests/Production/Client'),str(ROOT/'Tests/Production')]
    native=original_module('Cockpit/native.py','original_native_cockpit')
    regression=original_module('Cockpit/regression.py','original_cockpit_regression')
    settings=load(ROOT/'Tests/Production/Cockpit/cases.json');directory=output/'cockpit';results={}
    for case in settings['cases']:
        name=case['id'];runs=[directory/(name+'-'+str(n)) for n in (1,2)]
        for p in runs:
            require((p/'cockpit.scn').read_text()==native.fixture(case),'Exact original instrument scenario required')
            state=rows(p/'cockpit-state.csv');require(len(state)==61 and all(math.isfinite(float(v)) for row in state for k,v in row.items() if k not in ('object','class')),'Complete finite original cockpit state required')
            require(load(p/'graphics-lifecycle.json')==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Original instrument presentation/context scope required')
            require('llvmpipe' in load(p/'renderer-info.json')['renderer'].lower(),'Original instrument software renderer required')
            error=p/'graphics-errors.txt';require(not error.exists() or not error.read_text().strip(),'Original instrument GL diagnostics')
        for name_file in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
            require((runs[0]/name_file).read_bytes()==(runs[1]/name_file).read_bytes(),'Original instrument deterministic repeat differs')
        for frame in (20,50):
            for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                require((runs[0]/(stem+'.rgba')).read_bytes()==(runs[1]/(stem+'.rgba')).read_bytes(),'Original instrument raw image repeat differs')
        one={**settings,'cases':[case]};results[name]=dict(comparison=native.compare(refs/'cockpit'/profile.split('-')[0],directory,one)[name],mfd_images=regression.mfd_images(refs/'cockpit'/profile.split('-')[0],directory,one)[name])
    require(len(results)==9,'Every original9instrument case required');return results


def audit_dialogs(profile,output,refs):
    sys.path[:0]=[str(ROOT/'Tests/Production/CockpitUI'),str(ROOT/'Tests/Production/Cockpit'),str(ROOT/'Tests/Production/Client'),str(ROOT/'Tests/Production')]
    native=original_module('CockpitUI/native.py','original_native_dialogs');settings=native.settings();directory=output/'dialogs';results={};config=profile.split('-')[0]
    for case in settings['cases']:
        name=case['id'];runs=[directory/(name+'-'+str(n)) for n in (1,2)];original=refs/'dialogs'/config/(name+'-1');timed=refs/'dialog-timing'/config/(name+'-1')
        require(native.read_rows(timed/'ui-inputs.csv')==native.read_rows(original/'ui-inputs.csv'),'Original timing source input schedule differs')
        for p in runs:
            require(load(p/'graphics-lifecycle.json')==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Complete original dialog presentation/context required')
            if case['expected']=='cancel':require((p/'ui-cancel.txt').read_text().strip()=='draft','Original dialog cancellation differs')
            else:require(case['expected'] in (p/'saved.scn').read_text().split('BEGIN_MFD Left',1)[1].split('END_MFD',1)[0],'Actual original dialog outcome differs')
            require(load(p/'ui-clock.json')==load(timed/'ui-clock.json') and native.read_rows(p/'ui-clock-trace.csv')==native.read_rows(timed/'ui-clock-trace.csv'),'Original exact fixed UI clock differs')
            native.compare_ui(original,p,compare_popup_pixels=False);native.compare_ui(timed,p)
            error=p/'graphics-errors.txt';require(not error.exists() or not error.read_text().strip(),'Original dialog GL diagnostics')
        for filename in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
            require((runs[0]/filename).read_bytes()==(runs[1]/filename).read_bytes(),'Original dialog deterministic repeat differs')
        for frame in (20,50):
            for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                require((runs[0]/(stem+'.rgba')).read_bytes()==(runs[1]/(stem+'.rgba')).read_bytes(),'Original dialog raw image repeat differs')
        one={**settings,'cases':[case]};results[name]=dict(ui=native.compare_ui(timed,runs[0]),comparison=native.compare(refs/'dialogs'/config,directory,one)[name],timing=native.compare(refs/'dialog-timing'/config,directory,one)[name],mfd_images=native.mfd_images(refs/'dialogs'/config,directory,one)[name])
    require(len(results)==3,'All three original dialog cases required');return results


def audit_recording(output):
    sys.path[:0]=[str(ROOT/'Tests/Production/CockpitUI'),str(ROOT/'Tests/Production')]
    original=original_module('CockpitUI/recording.py','original_recording_reader');directory=output/'recording'
    saved,counts,events=original.verify_streams(directory/'record');played=rows(directory/'playback/playback-state.csv')
    require(played[0]['playback']=='1' and any(r['object']=='DG2' for r in played) and any(float(r['warp'])==2 for r in played) and played[-1]['playback']=='0','Original playback focus/warp/end differs')
    copied=directory/'editor/Flights/test_record';edited=(copied/'system.dat').read_text().splitlines()
    require(len(edited)==len(events)+1 and sum(' NOTE New note' in x for x in edited)==1 and not any(' CAMERA ' in x or ' NOTEOFF' in x for x in edited),'Original editor commit/delete/discard outcomes differ')
    require((directory/'record/Flights/test_record/system.dat').read_text().splitlines()==events and
            all((copied/n).read_bytes()==(directory/'record/Flights/test_record'/n).read_bytes() for n in counts),'Original source flight and all original per-vessel streams changed')
    require(rows(directory/'editor/playback-state.csv')[-1]['playback']=='0' and (directory/'editor/Playback/test_record.scn').is_file(),'Original editor free flight/save outcome differs')
    replay=rows(directory/'edited-playback/playback-state.csv');require(replay[0]['playback']=='1' and any(r['object']=='DG2' for r in replay),'Original edited flight fresh playback differs')
    for vessel in ('dg','dg2','iss'):
        lines=(directory/'record-until-exit/Flights/initial'/(vessel+'.pos')).read_text().splitlines();samples=[x for x in lines if x and x[0].isdigit()]
        require(len(samples)>=2 and float(samples[-1].split()[0])>=4,'Original last vessel recorder sample not flushed')
    for name,frames in [('record',80),('playback',70),('editor',55),('edited-playback',35),('record-until-exit',20)]:
        require(load(directory/name/'graphics-lifecycle.json')==dict(rendered_frames=frames,successful_presents=frames,context_deleted=True),'Original recording process lifecycle incomplete')
    window=output/'window-dialog';text=(window/'saved.scn').read_text();require('TARGET ISS' in text.split('BEGIN_MFD Left',1)[1].split('END_MFD',1)[0] and 'LISTLEN 3' in text,'Original actual X11 dialog target and parameter outcome differs')
    return dict(original_recording_samples=counts,original_editor_and_playback_outcomes_reproduced=True,actual_saved_X11_target='ISS',actual_saved_X11_parameter=3,complete_core_gate_qualified=False)


def main():
    hosted();cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--profile',choices=PROFILES,required=True);cli.add_argument('--worker',choices=('instruments','dialogs','recording'))
    a=cli.parse_args();base=ROOT/'out/core-cockpit-independent'/a.profile;output=ROOT/'out/frozen-core-cockpit'/a.profile;refs=base/'reference'
    if a.worker:
        result={'instruments':lambda:audit_instruments(a.profile,output,refs),'dialogs':lambda:audit_dialogs(a.profile,output,refs),'recording':lambda:audit_recording(output)}[a.worker]()
        atomic_json(base/(a.worker+'-audit.json'),dict(status='independently-reproduced-original-comparisons-only',result=result,complete_core_gate_qualified=False));return
    _,index=restore_original(a.profile,base)
    for source,extra,name in [('Cockpit/frozen.py',[],'cockpit'),('CockpitUI/frozen_ui.py',[],'dialogs'),('additional_references.py',['ui-timing'],'dialog-timing')]:
        subprocess.run([sys.executable,'-B','Tests/Production/'+source,*extra,'--cache',str(refs/(name+'-cache')),'--output',str(refs/name)],cwd=ROOT,check=True)
    for worker in ('instruments','dialogs','recording'):
        subprocess.run([sys.executable,'-B',str(Path(__file__)),'--profile',a.profile,'--worker',worker],cwd=ROOT,check=True)
    require(all(sha(ROOT/n)==v['sha256'] for n,v in index['files'].items()),'Any original raw captured byte changed during independent audit')
    atomic_json(base/'verification.json',dict(status='independently-reproduced-frozen-core-cockpit-component-only',profile=a.profile,source_run_id=RUN,original_source=SOURCE,
        auditor_source=os.environ['GITHUB_SHA'],candidate_id=candidate()['id'],original_raw_index_sha256=sha(base/'selected-raw/raw-index.json'),
        comparison_reports_sha256={n:sha(base/(n+'-audit.json')) for n in ('instruments','dialogs','recording')},every_original_source_and_raw_byte_unchanged=True,
        new_simulator_processes=0,complete_core_gate_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False))


if __name__=='__main__':main()
