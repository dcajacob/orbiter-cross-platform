#!/usr/bin/env python3
"""Run the unchanged full stock collector and verifier on the frozen native application."""
import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tarfile
import zipfile
from contracts import ROOT,PROFILES,atomic_json,load,require,sha
from frozen_admission_api import candidate,hosted,REFERENCE
import capture_hosted_native_writer_runtime as original_setup
from rejection_input_bundle import pack
import recheck_native_discovery as retained

HERE=Path(__file__).resolve().parent
NAME='phase6-frozen-native-normal-admission-v1'
BASE=ROOT/'out/hosted-normal-admission'
EXIT=ROOT/'out/frozen-stock-exit'
RUNTIME='ccc02c8a34bd1f227624d8778a141e8736ae8111'


def prepare_package(profile,lock):
    """Verify the full frozen package and original completed unit receipts without running them again."""
    require(profile in PROFILES,'Exact frozen native profile required')
    app=lock['identities']['application'][profile];p=app['archive'];root=ROOT/'out/native-api-source/native'
    api=load(root/'api.json');job=retained.validate_api(api,profile);artifact=api['artifact'];zpath=root/'producer.zip'
    require(app['compiled_source']==p['source']==RUNTIME and p['run_id']==api['run']['id'] and
            p['artifact_id']==artifact['id'] and p['bytes']==artifact['size_in_bytes']==zpath.stat().st_size and
            'sha256:'+p['sha256']==artifact['digest'] and sha(zpath)==p['sha256'],
            'Exact frozen original native API and ZIP required')
    outer=root/'source-artifact';outer.mkdir()
    with zipfile.ZipFile(zpath) as zip:
        members=zip.infolist();names=[retained.safe(m.filename) for m in members]
        require(len({n.casefold() for n in names})==len(members) and sum(m.file_size for m in members)<1024**3 and
                all(not stat.S_ISLNK(m.external_attr>>16) for m in members),
                'Complete safe original native ZIP required')
        for m in members:
            if m.is_dir():continue
            f=outer/m.filename;f.parent.mkdir(parents=True,exist_ok=True)
            with zip.open(m) as source,f.open('xb') as sink:shutil.copyfileobj(source,sink,1024**2)
    manifest=outer/profile/'hosted-package.json';sealed=load(manifest);archive=outer/(profile+'.tar.gz')
    require(sha(manifest)==app['original_failure_manifest_sha256'] and sealed['test_errors']==retained.DISCOVERY_ERROR and
            sealed['status']=='built-only-tests-failed-or-incomplete' and sealed['source_commit']==RUNTIME and
            sealed['configuration']+'-'+sealed['math_profile']==profile and
            sealed['archive_sha256']==sha(archive) and sealed['archive_bytes']==archive.stat().st_size,
            'Preserve original failed discovery and actual complete package bytes')
    prefix='out/phase6-hosted-native/'+profile;package=ROOT/prefix;expected=sealed['archive_members_sha256']
    require(not package.exists(),'Fresh exact native runtime destination required')
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();names=[retained.safe(m.name) for m in members]
        require(len({n.casefold() for n in names})==len(members)==len(expected) and set(names)==set(expected) and
                sum(m.size for m in members)<4*1024**3,'Complete bounded original native package required')
        for m in members:
            path=ROOT/m.name
            require(m.isfile() and not m.mode&0o7000 and path.is_relative_to(package) and
                    not path.exists() and path.resolve()==path,'Original archive contains unsafe or colliding member')
            path.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(m) as source,path.open('xb') as sink:shutil.copyfileobj(source,sink,1024**2)
            path.chmod(m.mode&0o777)
            require(sha(path)==expected[m.name],'Original native package member changed: '+m.name)
    build=package/'build.json';record=load(build)
    require(sha(build)==sealed['build_manifest_sha256']==app['build_record_sha256'] and record['status']=='built' and
            record['source_base']==RUNTIME and record['instrumentation']=='address,undefined' and
            record['owning_sources_unchanged'] is True and sha(package/'engine/orbiter-production')==app['exe_sha256'],
            'Actual normal sanitized candidate application required')
    for name,h in (record['source_sha256_lf']|record['dependency_sha256_lf']).items():
        frozen=subprocess.check_output(['git','show',RUNTIME+':'+name],cwd=ROOT)
        require(all(hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()==h for b in (frozen,(ROOT/name).read_bytes())),
                'Actual frozen compiled owning input differs: '+name)
    tests={k:retained.test_result(package/i,package/j) for k,i,j in (
        ('engine','registered-unit-tests.json','engine-tests.xml'),
        ('upstream','upstream-registered-unit-tests.json','upstream-tests.xml'))}
    require(tests==sealed['tests']==lock['unit_inventory'][profile]['original'],'Original frozen unit inventory and results differ')
    for name in ('engine-tests.xml','upstream-tests.xml','engine-tests.log','upstream-tests.log'):
        retained.clean_sanitizers((package/name).read_text(errors='replace'))
    atomic_json(root/'candidate-restoration.json',dict(status='restored-exact-original-frozen-native-only',
        source=os.environ['GITHUB_SHA'],candidate_id=lock['id'],profile=profile,archive=p,original_job_id=job['id'],
        complete_original_package_members=len(expected),build_record_sha256=sha(build),unit_results=tests,
        original_failure_preserved=True,new_unit_or_simulator_processes=0,normal_admission_qualified=False))


def prepare_snapshot(profile):
    import original_package_snapshot_fallback as fallback
    paths=ROOT/'out/admission-package-source'/profile;paths.mkdir(parents=True,exist_ok=False)
    original=HERE/'prepare_hosted_numerical_observer_network.sh';body=original.read_text()
    pin='3f68e87168aaa71ea2183b953319edcb1add08bf'
    require(original.read_bytes()==subprocess.check_output(['git','show',pin+':'+original.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Original matching signed runtime transport changed')
    for old,new in [('Tests/Production/Closeout/prepare_hosted_numerical_observer.sh','Tests/Production/Closeout/prepare_hosted_normal_admission.sh'),
                    ('out/numerical-observer-network/$PROFILE','out/admission-network/$PROFILE')]:
        require(body.count(old)==1,'Exact prior network scope anchor required');body=body.replace(old,new)
    net=paths/'network.sh';net.write_text(body)
    plan=paths/'original-plan-with-explicit-snapshot-fallback.sh';plan.write_text(fallback.prepared_body())
    items=(original,fallback.ORIGINAL,Path(fallback.__file__),net,plan)
    (paths/'before.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in items))


def verify_scope(capture,audit,profile,lock):
    report=load(capture/'stock-scenarios.json');observed=load(audit)
    a=lock['identities']['application'][profile];rt=lock['identities']['runtime'][profile]
    require(report['status']==observed['status']=='passed' and report['summary']==observed['summary'] and
            report['summary']['attempted']==report['summary']['passed']==report['summary']['inventory_ready']==157 and
            report['summary']['failed']==0 and report['diagnostic_only'] is observed['diagnostic_only'] is False and
            report['execution_protocol']=='normal-stock-capture-v4' and report['backend']=='wayland' and
            report['runtime_identity']['runtime_source_commit']==RUNTIME and report['runtime_identity']['profile']==profile and
            report['runtime_identity']['sanitizer_linked'] is True and report['runtime_identity']['build_record_sha256']==a['build_record_sha256'] and
            report['runtime_sha256']['executable']==a['exe_sha256'] and report['runtime_sha256']['renderer']==rt['renderer_sha256'] and
            report['general_api_qualification']['sha256']==lock['identities']['reference']['joint_api']['qualified_report_sha256'] and
            report['sources_and_binaries_unchanged'] is True and observed['capture_sha256']==sha(capture/'stock-scenarios.json'),
            'Full actual candidate-bound normal admission and original independent audit required')
    expected={p['path'] for p in load(ROOT/'Tests/Production/production-source.lock.json')['scenarios']}
    require(set(report['cases_requested'])==set(report['cases'])==expected=={r['scenario'] for r in observed['runs']} and
            len(report['cases_requested'])==len(observed['runs'])==157 and len(expected)==157 and
            sum(c.get('intentional_exit') is not None for c in report['cases'].values())==1 and
            sum(c.get('general_api_startup_exit') is not None for c in report['cases'].values())==1,
            'All locked 157 scenario identities and both distinct original policies required')
    pids=set()
    for c in report['cases'].values():
        folder=capture/c['output'];receipt=load(folder/'process-receipt.json')
        require(c['status']=='passed' and not c['problems'] and receipt['terminal'] is True and receipt['cancelled'] is False and
                receipt['actual_returncode']==0 and receipt['actual_collector_pid'] not in pids,'Every actual normal launch must terminate cleanly once')
        pids.add(receipt['actual_collector_pid'])
        console=(folder/'console.log').read_text(errors='replace')
        retained.clean_sanitizers(console)
        require(not any(mark in console for mark in ('Native module rejected','Cannot load native module',
                'Native module initialization failed','Missing native module entry')),
                'No class can be rejected in a normal admission launch')
    return dict(candidate_id=lock['id'],profile=profile,actual_normal_launches=len(pids),
        exact_stock_cases=len(expected),versioned_api_startup_and_original_intentional_exit_audited=True,
        original_collector_and_verifier_sha256={k:v for k,v in lock['identities']['runner'].items() if '/StockScenarios/' in k},
        capture_sha256=sha(capture/'stock-scenarios.json'),independent_audit_sha256=sha(audit),published_raw_audit_pending=True)


def prepared_body():
    body=original_setup.prepared_body()
    for old,new,count in [
        ("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='"+NAME+"'",1),
        ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-normal-admission'",1),
        ("ROOT/'out/native-writer-container.json'","ROOT/'out/admission-container.json'",2)]:
        require(body.count(old)==count,'Original complete provider setup anchor changed: '+old)
        body=body.replace(old,new)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from hosted_normal_admission import candidate,verify_scope,REFERENCE,EXIT,RUNTIME
        lock=candidate();report['candidate_id']=lock['id'];save()
        build=ROOT/'out/phase6-hosted-native'/a.profile;engine=build/'engine';capture=output/'capture'
        modules=engine/'NativeModules';assets=ROOT/'out/native-stock-assets';audit=output/'independent-full-stock-audit.json'
        require(shutil.disk_usage(ROOT).free>=12*1024**3,'Require complete raw evidence space plus eight GiB reserve')
        restore=load(ROOT/'out/native-api-source/native/candidate-restoration.json')
        require(restore['candidate_id']==lock['id'] and restore['profile']==a.profile and restore['build_record_sha256']==sha(build/'build.json'),
                'Actual frozen native restoration required')
        gtk=providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'
        libraries=[engine,*(providers/f/'install/lib/x86_64-linux-gnu' for f in ('fontconfig-candidate','gdk-candidate')),
            mesa/'install/lib/x86_64-linux-gnu']
        with Compositor(providers/'compositor',output/'compositor') as display:
            environment=dict(display.environment,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'),
                LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LD_LIBRARY_PATH=':'.join(map(str,libraries)),
                LIBDECOR_PLUGIN_DIR=str(gtk.parent),ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            common=['--assets',str(assets),'--modules',str(modules),'--runtime-owner',str(ROOT),
                '--runtime-source-commit',RUNTIME,'--stock-exit-reference',str(EXIT),'--general-api-qualification',str(REFERENCE)]
            command=py+['Tests/Production/StockScenarios/run.py',*common,'--executable',str(engine/'orbiter-production'),
                '--data','out/native-stock-data','--planets','out/native-stock-planets','--output',str(capture),
                '--backend','wayland','--build-record',str(build/'build.json')]
            original_audit=py+['Tests/Production/StockScenarios/verify.py',*common,'--capture',str(capture),'--output',str(audit)]
            try:
                run('normal-host-all-157-original-stock-scenarios',command,13000,environment)
            finally:
                manifest=capture/'stock-scenarios.json'
                if manifest.exists() and 'summary' in load(manifest):
                    run('unchanged-independent-full-stock-auditor',original_audit,2400,environment)
            report['full_stock_scope']=verify_scope(capture,audit,a.profile,lock);save()
        require(display.process.returncode==0,'Owned compositor must exit normally')
        require(candidate()==lock,'Frozen application/reference/source lock changed')
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    before="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    require(body.count(before)==1,'Exact prior complete runtime summary anchor required')
    return body.replace(before,"        report.update(status='captured-and-audited-full-normal-admission-profile-only',actual_processes=157,\n            normal_admission_qualified=False,phase6_complete=False,published_raw_independent_audit_pending=True)",1)


def preserve(profile):
    folder=BASE/profile;folder.mkdir(parents=True,exist_ok=True)
    paths={p for p in folder.rglob('*') if p.is_file() or p.is_symlink()}
    manifest=folder/'capture/stock-scenarios.json'
    if manifest.is_file():
        # Raw collector output is complete; immutable application/reference inputs can be restored independently.
        body=load(manifest)
        atomic_json(folder/'external-guard-index.json',dict(capture_sha256=sha(manifest),
            protected_files_sha256=body.get('protected_files_sha256',{}),source_sha256=body['source_sha256']))
        paths.add(folder/'external-guard-index.json')
    if paths:pack(ROOT,paths,folder/'capture-raw.tar.gz',folder/'capture-raw-index.json')


def main():
    hosted()
    require(len(sys.argv)==3 and sys.argv[1] in ('--prepare','--profile') and sys.argv[2] in PROFILES,
            'Explicit complete frozen admission profile required')
    profile=sys.argv[2]
    if sys.argv[1]=='--prepare':
        prepare_package(profile,candidate());prepare_snapshot(profile);return
    try:exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
    finally:
        try:preserve(profile)
        except BaseException as e:
            folder=BASE/profile;folder.mkdir(parents=True,exist_ok=True)
            atomic_json(folder/'raw-retention-failure.json',dict(error=str(e),qualification_granted=False))
            raise


if __name__=='__main__':main()
