#!/usr/bin/env python3
"""Renew only original positive family and paused-world lifetime facets on hosted retained packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from hosted_native_package import ROOT,require,sha,load
import capture_hosted_native_writer_runtime as runtime_writer

COMPILED='ccc02c8a34bd1f227624d8778a141e8736ae8111'
FAMILY_CASES={'Atlantis':'remaining_stock_003','Atlantis_SRB':'remaining_stock_003','Atlantis_Tank':'remaining_stock_003',
 'Carina':'remaining_stock_026','Leonardo_mplm':'remaining_stock_003','Module2':'remaining_stock_009',
 'Dragonfly':'remaining_stock_009','HST':'remaining_stock_018','LDEF':'remaining_stock_022','SolarSail':'remaining_stock_013','Quadcopter':'remaining_stock_017'}
CASES=sorted(set(FAMILY_CASES.values()))
CONSERVED={
 'Tests/Production/RemainingVessels/native.py':'68a640905d163f409a138985d36cbf5fd912d4141b1c86fd05ba6a7572c47a01',
 'Tests/Production/RemainingVessels/lifetimes.py':'722fac7bce6720cdd757c51453e06d9a8f697195f095dd896fa9021dbe6723d2',
 'Tests/Production/RemainingVessels/paused_attachments.py':'5bb412921d2c247bfe0b3a8070e4ac1d0985329c3f2fd24ce9b11cf1faceb767',
 'Tests/Production/Closeout/class_eligibility.py':'32f564b22c48870c4cbd03a65f23bbb5d6966239302405273f7246b63b738b14'}


def conserved_sources():
    result={}
    for relative,value in CONSERVED.items():
        body=(ROOT/relative).read_bytes();original=subprocess.check_output(['git','-C',str(ROOT),'show',COMPILED+':'+relative])
        require(body==original and hashlib.sha256(body).hexdigest()==value,'Original complete class collector/auditor changed: '+relative)
        result[relative]=value
    config=load(ROOT/'Tests/Production/RemainingStock/cases.json');cases={c['id']:c for c in config['cases']}
    require(len(CASES)==7 and len(FAMILY_CASES)==11 and all(kind in cases[name]['declared_vessels'].values() for kind,name in FAMILY_CASES.items()),
        'Every original family must remain present in its complete seven-scene scope')
    return dict(compiled_source=COMPILED,original_collector_and_auditor_sha256=result,family_cases=FAMILY_CASES,
        selected_complete_scenes=CASES,frames_per_world=60,worlds_per_scene=20,paused_worlds=20,
        normal_admission_qualified=False,phase6_complete=False)


def paused_body():
    path=ROOT/'Tests/Production/RemainingVessels/paused_attachments.py';body=path.read_bytes()
    require(hashlib.sha256(body).hexdigest()==CONSERVED[path.relative_to(ROOT).as_posix()],'Original paused collector changed')
    old='cloud_builds_used=False, raw_evidence_uploaded=False'
    new='cloud_builds_used=True, raw_evidence_uploaded=False'
    require(body.decode().count(old)==1,'Original paused collector transport declaration differs')
    return body.decode().replace(old,new,1)


def inspect_profile(profile,family_capture,family_audit,paused_capture,paused_audit):
    capture=load(family_capture);audited=load(family_audit);paused=load(paused_capture);checked=load(paused_audit)
    require(capture['status']=='captured-lifetimes-awaiting-independent-audit' and set(capture['cases'])==set(CASES) and
        capture['cases_requested']==CASES and capture['failures']=={} and audited['status']=='audited-twenty-world-lifetimes-diagnostic-only' and
        set(audited['cases'])==set(CASES) and audited['runtime_identity']['profile']==profile and
        audited['runtime_identity']['runtime_source_commit']==COMPILED and audited['runtime_identity']['sanitizer_linked'] is True and
        audited['worlds']==140 and audited['successful_presents']==8400 and audited['owning_bytes_unchanged'] is True,
        'Complete seven-scene original positive twenty-world facet required')
    require(paused['status']=='passed-actual-paused-attached-docked-world-lifetimes' and paused['cloud_builds_used'] is True and
        paused['runtime_identity']['profile']==profile and paused['runtime_identity']['runtime_source_commit']==COMPILED and
        paused['requested_worlds']==paused['worlds_observed_ready']==paused['clean_contexts']==20 and
        checked['status']=='audited-paused-attachment-lifetime-facet-only' and checked['real_F5_reloads']==19 and
        checked['owning_bytes_unchanged'] is True and checked['sanitizer_suppressions'] is False,
        'Complete original paused twenty-world and nineteen real dispatched-F5 facet required')
    require(all(not r['native_admission_qualified'] and not r['phase6_complete'] for r in (capture,audited,paused,checked)),
        'Partial family lifetime facets cannot grant admission or acceptance')
    return dict(status='captured-and-audited-original-family-and-paused-lifetime-facets-only',profile=profile,
        actual_family_processes=7,actual_paused_processes=1,active_worlds=140,paused_worlds=20,
        active_successful_presents=8400,paused_successful_presents=paused['successful_presents'],
        real_F5_reloads=19,passed_positive_facets=['source-abi','resource-ownership','twenty-cycle-teardown'],
        capability_interaction_persistence_rejection_and_complete_class_eligibility_pending=True,
        metadata_sha256={str(p):sha(p) for p in (family_capture,family_audit,paused_capture,paused_audit)},
        normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)


def prepared_body():
    body=runtime_writer.prepared_body()
    changes=[
        ("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-lifetimes-v1'"),
        ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-lifetimes'"),
        ("ROOT/'out/native-writer-container.json'","ROOT/'out/native-class-container.json'")]
    for before,after in changes:
        require(body.count(before)==(2 if 'container.json' in before else 1),'Original complete runtime setup anchor differs: '+before)
        body=body.replace(before,after)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from hosted_native_general_api import source_identity
        from hosted_class_lifetimes import conserved_sources,inspect_profile,CASES
        report['core_source_identity']=source_identity()
        report['original_class_source_identity']=conserved_sources();save()
        build=ROOT/'out/phase6-hosted-native'/a.profile
        family=ROOT/'out/native-class-lifetimes'/a.profile
        paused=ROOT/'out/native-class-paused'/a.profile
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/RemainingVessels/native.py','--owner',str(ROOT),
            '--build',str(build/'engine'),'--build-record',str(build/'build.json'),
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--gtk-build-record',str(providers/'libdecor-candidate/build.json'),
            '--lifetime-sessions','20','--runtime-role','diagnostic','--jobs','1','--output',str(family)]
        for case in CASES:argv+=['--case',case]
        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('all-seven-original-family-scenes-twenty-worlds',argv,14400,environment)
        family_audit=output/'independent-family-lifetimes.json'
        run('independent-original-family-lifetime-audit',py+['Tests/Production/RemainingVessels/lifetimes.py',
            '--capture',str(family/'lifetimes.json'),'--output',str(family_audit)],1200,environment)
        paused_argv=py+['Tests/Production/Closeout/hosted_class_lifetimes.py','--paused-only','--owner',str(ROOT),
            '--package',str(build),'--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--worlds','20','--output',str(paused)]
        for folder in ('fontconfig-candidate','gdk-candidate'):paused_argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        paused_argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('original-paused-complete-graph-nineteen-F5-reloads',paused_argv,7200,environment)
        paused_audit=output/'independent-paused-lifetimes.json'
        run('independent-original-paused-lifetime-audit',py+['Tests/Production/Closeout/class_eligibility.py',
            '--paused-capture',str(paused/'verification.json'),'--output',str(paused_audit)],1200,environment)
        report['actual_lifetime_facets']=inspect_profile(a.profile,family/'lifetimes.json',family_audit,paused/'verification.json',paused_audit)
        require(source_identity()==report['core_source_identity'] and conserved_sources()==report['original_class_source_identity'],
            'Actual compiled core or original class collectors changed during capture')
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    new="        report.update(status='captured-and-audited-original-family-and-paused-lifetime-facets-only',actual_processes=8,\n            active_worlds=140,paused_worlds=20,normal_admission_qualified=False,complete_class_eligibility_qualified=False,hands_on_ready=False)"
    require(body.count(old)==1,'Original writer completion anchor differs')
    return body.replace(old,new,1)


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux',
        'Class renewal must run on the actual standard hosted Linux worker; no local runtime allowed')
    conserved_sources()
    if '--paused-only' in sys.argv:
        sys.argv.remove('--paused-only')
        path=ROOT/'Tests/Production/RemainingVessels/paused_attachments.py'
        exec(compile(paused_body(),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
        return
    exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})


if __name__=='__main__':main()
