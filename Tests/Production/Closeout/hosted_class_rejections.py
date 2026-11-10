#!/usr/bin/env python3
"""Run every unchanged original negative loader/class control in retained hosted normal hosts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from contracts import ROOT,PROFILES,load,sha,require,atomic_json
import capture_hosted_native_writer_runtime as runtime
import hosted_class_lifetimes as family
import rejection_input_bundle as bundle

LOCK=ROOT/'Tests/Production/Closeout/class-rejection-original-source-v1.lock.json'
COMPILED=family.COMPILED
CASES=family.CASES


def conserved_sources():
    lock=load(LOCK);require(lock['compiled_runtime_source']==COMPILED,'Exact retained original rejection runtime required')
    for name,digest in lock['source_sha256'].items():
        body=(ROOT/name).read_bytes();require(hashlib.sha256(body).hexdigest()==digest and
            body==subprocess.check_output(['git','-C',str(ROOT),'show',COMPILED+':'+name]),'Original rejection/fixture/source reader changed: '+name)
    sys.path.insert(0,str(ROOT/'Tests/Production/RemainingVessels'));import rejections
    config=load(ROOT/'Tests/Production/RemainingStock/cases.json');cases=[v for v in config['cases'] if v['id'] in CASES]
    controls=rejections.controls(config,cases)
    require(len(cases)==7 and len(controls)==45 and controls==lock['exact_original_controls'] and
            len({v['id'] for v in controls})==45 and {v['family'] for v in controls}==set(config['required_classes']),
            'All original families, seven complete scenes and exactly45 actual negative controls required')
    return lock


def preserved_pe(profile):
    require(profile in PROFILES,'Exact preserved Windows configuration/profile required')
    import audit_native_original_phase as physical
    reader=physical.persistence.bind_owner(ROOT,physical.writers.SOURCE)
    configuration=profile.split('-',1)[0];folder=ROOT/'out/rejection-preserved'/configuration
    guards=reader.original_audit.preserved(folder);pins=load(ROOT/'Tests/Production/Cockpit/Reference/provenance.json');meta=load(folder/'control-reference-runtime.json')
    require(meta['application_source']==pins['application_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37' and
            meta['runtime_archive_sha256']==pins['runtime_artifacts'][configuration]['sha256'] and
            meta['client_archive_sha256']==pins['artifacts'][configuration]['sha256'],
            'Exact preserved original application/SDK/client artifact identities required')
    selected=[name for name in guards if Path(name).name.lower()=='hst.dll']
    require(len(selected)==1 and (folder/selected[0]).read_bytes()[:2]==b'MZ' and reader.original_audit.PE(folder/selected[0]).width==8,
            'Actual source-bound original x64 Windows HST PE required')
    return dict(protocol='phase6-original-Windows-HST-PE-rejection-input-v1',profile=profile,configuration=configuration,
        application_source=pins['application_source'],dll=str(folder/selected[0]),dll_sha256=guards[selected[0]],
        preserved_package=str(folder),all_original_package_files_sha256={str(folder/name):digest for name,digest in guards.items()},
        runtime_archive_sha256=meta['runtime_archive_sha256'],client_archive_sha256=meta['client_archive_sha256'],
        Windows_code_executed=False,phase6_complete=False)


def inspect_profile(profile,capture_path,audit_path):
    lock=conserved_sources();capture=load(capture_path);audit=load(audit_path)
    require(capture['status']=='passed-negative-loader-and-class-controls-only' and not capture['failures'] and
            capture['controls_requested']==lock['exact_original_controls'] and capture['cases_requested']==CASES and
            capture['runtime_identity']['profile']==profile and capture['runtime_identity']['runtime_source_commit']==COMPILED and
            capture['runtime_identity']['sanitizer_linked'] is True and capture['runtime_role']=='normal' and
            Path(capture['runtime_executable']).name=='orbiter-production' and
            audit['status']=='audited-negative-loader-and-class-controls-only' and audit['runtime_identity']==capture['runtime_identity'] and
            audit['capture_sha256']==sha(capture_path) and audit['actual_processes']==45 and audit['runtime_role']=='normal' and
            audit['owning_bytes_unchanged'] is True and audit['sanitizer_suppressions'] is False and
            audit['controls']==capture['controls'] and all(v['actual_exitcode']==1 and
                v['lifecycle']==dict(rendered_frames=0,successful_presents=0,context_deleted=True) for v in audit['controls'].values()) and
            all(v['diagnostic_only'] is True and v['native_admission_qualified'] is False and v['phase6_complete'] is False for v in (capture,audit)),
            'Every actual original normal-host negative input/exit/cleanup/sanitizer check required')
    identities=[]
    for value in lock['exact_original_controls']:
        folder=capture_path.parent/value['id'];receipt=load(folder/'process-receipt.json');invocation=load(folder/'invocation.json')
        actual=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']]
        require(len(actual)==1 and actual[0]['start_ticks']>0 and actual[0]['argv']==invocation['argv'] and
                invocation['argv'][0]==capture['runtime_executable'],'Distinct actual original OS process/start/argv witness required')
        identities.append(dict(control=value['id'],pid=actual[0]['pid'],start_ticks=actual[0]['start_ticks'],argv=actual[0]['argv'],
            receipt_sha256=sha(folder/'process-receipt.json'),invocation_sha256=sha(folder/'invocation.json')))
    require(len({(v['pid'],v['start_ticks']) for v in identities})==45,'One actual process cannot supply more than one rejection control')
    return dict(status='captured-and-audited-original-normal-host-rejection-controls-only',profile=profile,actual_original_processes=45,
        compiled_runtime_source=COMPILED,exact_original_controls=lock['exact_original_controls'],actual_original_process_identities=identities,
        no_frames_presented=True,all_contexts_clean=True,no_rejected_world_saved=True,no_invalid_fixture_initialized=True,
        unsuppressed_original_sanitizers=True,metadata_sha256={str(p):sha(p) for p in (capture_path,audit_path)},
        published_raw_independent_replay_pending=True,complete_class_eligibility_qualified=False,
        normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)


def prepared_body():
    body=runtime.prepared_body()
    for old,new in [("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-rejections-v1'"),
                    ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-rejections'"),
                    ("ROOT/'out/native-writer-container.json'","ROOT/'out/native-rejection-container.json'")]:
        require(body.count(old)==(2 if 'container.json' in old else 1),'Conserved original runtime setup anchor differs');body=body.replace(old,new)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from hosted_native_general_api import source_identity
        from hosted_class_rejections import conserved_sources,preserved_pe,inspect_profile,CASES
        report['core_source_identity']=source_identity();report['original_rejection_source_identity']=conserved_sources()
        pe=preserved_pe(a.profile);report['original_Windows_PE']=pe;atomic_json(output/'original-Windows-PE.json',pe);save()
        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-class-rejections'/a.profile
        sdk={str(path):sha(path) for path in (build/'engine/native-sdk').rglob('*') if path.is_file()}
        require(sdk,'Actual retained native SDK required for original seven sanitizer fixtures')
        atomic_json(output/'original-fixture-SDK.json',dict(files_sha256=sdk,fixture_source_sha256=sha(ROOT/'Tests/Production/RemainingVessels/RejectedModule.cpp'),
            original_commands_generated_by_unchanged_collector=True,phase6_complete=False))
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/RemainingVessels/native.py','--rejection-control','--owner',str(ROOT),
            '--build',str(build/'engine'),'--build-record',str(build/'build.json'),
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--gtk-build-record',str(providers/'libdecor-candidate/build.json'),
            '--rejection-windows-dll',pe['dll'],'--runtime-role','normal','--jobs','1','--output',str(capture)]
        for case in CASES:argv+=['--case',case]
        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('all-original-forty-five-normal-host-rejection-controls',argv,14400,environment)
        audited=output/'original-rejections-audit.json'
        run('unchanged-original-independent-rejection-audit',py+['Tests/Production/RemainingVessels/rejections.py',
            '--capture',str(capture/'rejections.json'),'--output',str(audited)],1800,environment)
        report['actual_original_rejection_scope']=inspect_profile(a.profile,capture/'rejections.json',audited)
        require(source_identity()==report['core_source_identity'] and conserved_sources()==report['original_rejection_source_identity'] and
                preserved_pe(a.profile)==pe and all(sha(name)==value for name,value in sdk.items()),
                'Actual core/collector/PE/native SDK source changed during original rejection controls')
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    new="        report.update(status='captured-and-audited-original-normal-host-rejection-controls-only',actual_processes=45,\n            published_raw_independent_replay_pending=True,complete_class_eligibility_qualified=False,normal_admission_qualified=False,hands_on_ready=False)"
    require(body.count(old)==1,'Conserved original collection completion anchor differs')
    return body.replace(old,new,1).replace('from hosted_native_package import ROOT,require,sha,load','from hosted_native_package import ROOT,require,sha,load\nfrom contracts import atomic_json')


def preserve_inputs(profile):
    capture=ROOT/'out/native-class-rejections'/profile;output=ROOT/'out/hosted-native-class-rejections'/profile
    if not capture.exists():return
    require(output.exists(),'Original capture must have its separate hosted collection receipt')
    paths={p for p in capture.rglob('*') if p.is_file() or p.is_symlink()}
    manifest=capture/'rejections.json'
    if manifest.exists():paths.update(Path(name) for name in load(manifest)['guarded_files_sha256'])
    preserved=ROOT/'out/rejection-preserved'/profile.split('-',1)[0]
    paths.update(p for p in preserved.rglob('*') if p.is_file() or p.is_symlink())
    paths.update(p for p in output.rglob('*') if p.is_file() or p.is_symlink())
    for relative in load(LOCK)['source_sha256']:paths.add(ROOT/relative)
    paths.update({Path(__file__),Path(bundle.__file__),LOCK})
    record=bundle.pack(ROOT,paths,output/'raw-original-inputs.tar.gz',output/'raw-index.json')
    if load(output/'collection.json')['status']=='captured-and-audited-original-normal-host-rejection-controls-only':
        require(not record['missing_guarded_paths'],'Passed original controls cannot lose any guarded input')
        sys.path.insert(0,str(ROOT/'Tests/Production/RemainingVessels'));import rejections
        require(rejections.audit(manifest)==load(output/'original-rejections-audit.json'),'Original rejection evidence changed during lossless packing')


def main():
    if '--source-preflight' in sys.argv:
        p=argparse.ArgumentParser();p.add_argument('--source-preflight',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
        require(not a.output.exists(),'Fresh original rejection source preflight required');atomic_json(a.output,conserved_sources());return
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted Linux required; no local rejection runtime')
    profile=sys.argv[sys.argv.index('--profile')+1];require(profile in PROFILES,'Exact original rejection profile required');conserved_sources()
    original_error=None
    try:exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
    except BaseException as error:original_error=error;raise
    finally:
        try:preserve_inputs(profile)
        except BaseException as packing_error:
            output=ROOT/'out/hosted-native-class-rejections'/profile;output.mkdir(parents=True,exist_ok=True)
            atomic_json(output/'packing-failure.json',dict(error=str(packing_error),original_capture_error=str(original_error),scope_qualified=False,phase6_complete=False))
            if original_error is None:raise


if __name__=='__main__':main()
