#!/usr/bin/env python3
"""Run unchanged HUD/MFD, dialogs and recording fixtures on the frozen native builds."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from contracts import ROOT,PROFILES,atomic_json,load,require,sha
from frozen_admission_api import candidate,hosted
from hosted_normal_admission import prepare_package,prepare_snapshot
import capture_hosted_native_writer_runtime as original_setup
from rejection_input_bundle import pack

HERE=Path(__file__).resolve().parent
BASE=ROOT/'out/frozen-core-cockpit'
RUNTIME=ROOT/'out/phase6-hosted-native'
FIXTURES=('Cockpit/native.py','CockpitUI/native.py','CockpitUI/mouse_smoke.py','CockpitUI/recording.py')
STAGING=('Cockpit/frozen.py','CockpitUI/frozen_ui.py','additional_references.py')


def prepare(profile):
    lock=candidate();prepare_package(profile,lock);prepare_snapshot(profile)
    base=ROOT/'out/admission-package-source'/profile
    for source,old,new,destination in [
        (base/'network.sh','Tests/Production/Closeout/prepare_hosted_normal_admission.sh',
         'out/admission-package-source/'+profile+'/cockpit-bootstrap.sh',base/'cockpit-network.sh'),
        (HERE/'prepare_hosted_normal_admission.sh','Tests/Production/Closeout/hosted_normal_admission.py --profile',
         'Tests/Production/Closeout/hosted_frozen_cockpit_component.py --profile',base/'cockpit-bootstrap.sh')]:
        body=source.read_text();require(body.count(old)==1,'Exact original hosted setup anchor required')
        destination.write_text(body.replace(old,new,1))
    checks=(base/'before.sha256').read_text()
    for path in (base/'cockpit-network.sh',base/'cockpit-bootstrap.sh',HERE/'prepare_hosted_normal_admission.sh'):
        checks+=sha(path)+'  '+path.relative_to(ROOT).as_posix()+'\n'
    (base/'cockpit-before.sha256').write_text(checks)
    out=ROOT/'out/frozen-core-reference';out.mkdir()
    for file,extra,name in [(STAGING[0],[],'cockpit'),(STAGING[1],[],'dialogs'),(STAGING[2],['ui-timing'],'dialog-timing')]:
        command=[sys.executable,'-B','Tests/Production/'+file,*extra,'--cache',str(out/(name+'-cache')),'--output',str(out/name)]
        with (out/(name+'-restoration.log')).open('xb') as log:
            subprocess.run(command,cwd=ROOT,check=True,timeout=900,stdout=log,stderr=subprocess.STDOUT)
    atomic_json(out/'reference-staging.json',dict(candidate_id=lock['id'],source=os.environ['GITHUB_SHA'],profile=profile,
        frozen_reference_sha256={name:sha(out/name/'provenance.json') for name in ('cockpit','dialogs','dialog-timing')},
        all_original_image_and_text_tolerances_unchanged=True,new_simulator_processes=0))


def runtime_proof(profile,lock,build):
    manifest=load(build/'build.json');a=lock['identities']['application'][profile]
    restore=load(ROOT/'out/native-api-source/native/candidate-restoration.json')
    require(restore['candidate_id']==lock['id'] and restore['profile']==profile and
            sha(build/'build.json')==a['build_record_sha256'] and manifest['source_base']==a['compiled_source'] and
            manifest['instrumentation']=='address,undefined' and
            all(sha(ROOT/n)==h for n,h in manifest['runtime_files_sha256'].items()),'Exact complete frozen instrumented runtime required')
    return dict(build_sha256=a['build_record_sha256'],compiled_source=a['compiled_source'],
                original_unit_inventory=lock['unit_inventory'][profile],source=os.environ['GITHUB_SHA'])


def result(output):
    inst=load(output/'cockpit/native-cockpit-report.json');gui=load(output/'dialogs/native-ui-report.json')
    rec=load(output/'recording/verification.json')
    window=load(output/'window-dialog/ui-verification.json')
    require(window['status']=='passed' and window['target']=='ISS' and
            all(window[n] is True for n in ('parameter_entry','parameter_cancel','text_captures_flight_key','flight_resumes_after_dialog')) and
            window['lifecycle']['context_deleted'] is True,'Original real X11 input/dialog lifecycle required')
    expected_inst={c['id'] for c in load(ROOT/'Tests/Production/Cockpit/cases.json')['cases']}
    expected_gui={c['id'] for c in load(ROOT/'Tests/Production/CockpitUI/cases.json')['cases']}
    require(inst['status']==gui['status']=='passed' and len(expected_inst)==9 and set(inst['cases'])==expected_inst and
            len(expected_gui)==3 and set(gui['cases'])==expected_gui and
            all(x['identical_repeats'] is True for x in inst['cases'].values()) and
            all(rec[k] is True for k in ('replayed_focus','replayed_warp','playback_ended','editor_committed',
                'editor_deleted','editor_discarded','exit_flushed','lifecycle')),
            'Unchanged complete 9 instrument, 3 dialog and actual recording workflows required')
    require({f.name for f in (output/'recording').iterdir() if f.is_dir()}==
            {'record','playback','editor','edited-playback','record-until-exit'},'Original five recording processes required')
    from recheck_native_discovery import clean_sanitizers
    for root in (output/'cockpit',output/'dialogs',output/'window-dialog',output/'recording'):
        for log in root.rglob('console*'):
            if log.is_file():clean_sanitizers(log.read_text(errors='replace'))
    return dict(actual_instrument_cases=9,actual_dialog_cases=3,actual_recording_processes=5,actual_window_routed_dialog_controls=True,original_repeats=2,
        instrument_and_dialog_reports_sha256=[sha(output/'cockpit/native-cockpit-report.json'),sha(output/'dialogs/native-ui-report.json')],
        original_recording_report_sha256=sha(output/'recording/verification.json'),original_window_input_report_sha256=sha(output/'window-dialog/ui-verification.json'),complete_core_gate_qualified=False)


def prepared_body():
    body=original_setup.prepared_body()
    for old,new,count in [
        ("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-frozen-cockpit-component-v1'",1),
        ("ROOT/'out/hosted-native-writer'","ROOT/'out/frozen-core-cockpit'",1),
        ("ROOT/'out/native-writer-container.json'","ROOT/'out/frozen-core-cockpit-container.json'",2)]:
        require(body.count(old)==count,'Conserved original provider setup anchor differs');body=body.replace(old,new)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from types import SimpleNamespace
        from hosted_frozen_cockpit_component import candidate,runtime_proof,result,RUNTIME,FIXTURES
        from hosted_class_interactions import install_x11,verify_x11
        sys.path.insert(0,str(ROOT/'Tests/Production/RemainingVessels'))
        from interactions import display_backend
        lock=candidate();report['candidate_id']=lock['id'];build=RUNTIME/a.profile;engine=build/'engine'
        report['runtime_proof']=runtime_proof(a.profile,lock,build);save()
        x11=install_x11(output,run);report['x11']=x11;save()
        watched={ROOT/'Tests/Production'/n for n in FIXTURES}|{ROOT/'Tests/Production'/n for n in
            ('Cockpit/cases.json','CockpitUI/cases.json','Cockpit/compare.py','Cockpit/reference.py',
             'Client/compare_client.py','CockpitUI/capture.py','CockpitUI/frozen_ui.py','Cockpit/frozen.py','additional_references.py')}
        sources={str(p.relative_to(ROOT)):sha(p) for p in watched}
        require(all(subprocess.check_output(['git','show',report['collector_source']+':'+n],cwd=ROOT)==(ROOT/n).read_bytes() for n in sources),
                'Exact immutable original fixture and comparator source required')
        report['original_fixture_sources_sha256']=sources;save()
        require(shutil.disk_usage(ROOT).free>=10*1024**3,'Full interface raw evidence and eight GiB free reserve required')
        ref=ROOT/'out/frozen-core-reference';ref_record=load(ref/'reference-staging.json')
        require(ref_record['candidate_id']==lock['id'] and ref_record['source']==report['collector_source'] and
                ref_record['profile']==a.profile and all(sha(ref/k/'provenance.json')==v for k,v in ref_record['frozen_reference_sha256'].items()),
                'Exact original frozen HUD/MFD, dialog and timing reference restoration required')
        modules=engine/'NativeModules';config=a.profile.split('-')[0]
        common=['--executable',str(engine/'orbiter-production'),'--assets','out/native-stock-assets',
                '--data','out/native-stock-data','--planets','out/native-stock-planets','--modules',str(modules)]
        arguments=SimpleNamespace(compositor_tools=providers/'compositor')
        failures=[]
        for key,file,extra in [
            ('cockpit','Cockpit/native.py',['--configuration',config,'--frozen',str(ref/'cockpit')]),
            ('dialogs','CockpitUI/native.py',['--configuration',config,'--frozen',str(ref/'dialogs'),'--timing-frozen',str(ref/'dialog-timing')]),
            ('window-dialog','CockpitUI/mouse_smoke.py',[]),
            ('recording','CockpitUI/recording.py',[])]:
            try:
                with display_backend(arguments,output/(key+'-X11'),{'window_system':'x11'}) as desktop:
                    libraries=[engine,*(providers/f/'install/lib/x86_64-linux-gnu' for f in ('fontconfig-candidate','gdk-candidate')),
                        mesa/'install/lib/x86_64-linux-gnu']
                    environment=dict(desktop,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'),
                        LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LD_LIBRARY_PATH=':'.join(map(str,libraries)),
                        ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                        UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                    run(key+'-unchanged-original-fixtures',py+['Tests/Production/'+file,*common,*extra,'--output',str(output/key)],2400,environment)
            except Exception as error:
                failures.append(dict(component=key,error=str(error)));report['failures']=failures;save()
        require(not failures,'One or more original core cockpit fixture groups failed; all partial evidence retained')
        report['core_component_result']=result(output);save()
        require(runtime_proof(a.profile,lock,build)==report['runtime_proof'] and candidate()==lock,'Exact frozen source/binary changed during core comparison')
        require(all(sha(ROOT/n)==v for n,v in sources.items()),'Original interface fixture or comparison source changed')
        verify_x11(x11)
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    before="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    require(body.count(before)==1,'Original exact completion anchor required')
    return body.replace(before,"        report.update(status='completed-frozen-cockpit-interface-component-only',complete_core_gate_qualified=False,phase6_complete=False)",1)


def main():
    hosted()
    require(len(sys.argv)==3 and sys.argv[1] in ('--prepare','--profile') and sys.argv[2] in PROFILES,'Exact original four profiles only')
    profile=sys.argv[2]
    if sys.argv[1]=='--prepare':prepare(profile);return
    try:exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
    finally:
        folder=BASE/profile
        if folder.is_dir():
            pack(ROOT,{p for p in folder.rglob('*') if p.is_file() or p.is_symlink()},folder/'raw-results.tar.gz',folder/'raw-index.json')


if __name__=='__main__':main()
