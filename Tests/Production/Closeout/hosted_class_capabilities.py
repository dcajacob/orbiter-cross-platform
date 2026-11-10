#!/usr/bin/env python3
"""Run the unchanged nine-scene exact SDK and passive observer controls on hosted packages."""
import os
from pathlib import Path
import sys
from hosted_native_package import ROOT,require,load,sha
import capture_hosted_native_writer_runtime as runtime_writer
from hosted_capability_reference import CASES,FIELDS,COMPILED,sources,structural_projection
from contracts import PROFILES

INVENTORY_SOURCE='493ef1508ba2a09effec8a8bc30afb9f61d3aa0c'


def reference_inventory():
    path=ROOT/'out/class-capability-inventory/reference/inventory.json';report=load(path)
    require(report['protocol']=='phase6-full-original-SDK-capability-inventory-v2' and
            report['status']=='verified-full-original-SDK-initial-capability-inventory-only' and
            report['source']==INVENTORY_SOURCE and report['original_capture_source']=='ba38a7efccb5f770e87add95f5e966aa40270756' and
            report['fields']==list(FIELDS) and report['proposed_native_cases']==CASES and
            report['actual_original_initial_sdk_snapshots']==304 and report['signature_count']==22 and
            len(report['selected_case_unique_signatures'])==17 and report['structural_projection_signature_count']==16 and
            report['full_17_field_comparison_fields']==list(FIELDS) and
            report['full_17_field_additional_variant_audit_pending'] is True and
            report['historical_inventory_available'] is False and report['historical_inventory_relabelled'] is False and
            report['actual_new_simulator_processes']==0 and report['qualification_granted'] is False and
            report['complete_class_eligibility_qualified'] is False and report['normal_admission_qualified'] is False and
            report['phase6_complete'] is False and report['hands_on_ready'] is False,
            'Complete source-bound exact SDK inventory and all pending broader qualification required')
    require(report['original_capability_sources_sha256']==sources() and set(report['profiles'])==set(PROFILES),
            'Original capability collectors or inventory profile scope changed')
    return report


def inspect_profile(profile,capture_path,audit_path):
    capture=load(capture_path);audit=load(audit_path);inventory=reference_inventory()
    require(capture['status']=='captured-capability-controls-awaiting-independent-audit' and capture['failures']=={} and
            capture['cases_requested']==CASES and set(capture['cases'])==set(CASES) and capture['repeats']==2 and
            audit['status']=='audited-original-Windows-native-capabilities-and-observer-controls-diagnostic-only' and
            audit['capture_sha256']==sha(capture_path) and audit['runtime_identity']==capture['runtime_identity'] and
            audit['runtime_identity']['profile']==profile and audit['runtime_identity']['runtime_source_commit']==COMPILED and
            audit['runtime_identity']['sanitizer_linked'] is True and audit['owning_bytes_unchanged'] is True,
            'Original complete nine-scene two-repeat exact capability capture/audit required')
    from class_eligibility import capability_profile_cases
    cases,runtime_sources,processes=capability_profile_cases([audit],profile,CASES)
    require(runtime_sources=={COMPILED} and processes==36 and len(cases)==9,
            'All original observer-off/on processes required')
    families={v[0] for v in inventory['unique_signatures']};observed=set()
    for runs in cases.values():
        require(len(runs)==2,'Both original SDK repetitions required')
        for run in runs:
            for row in run['actual_capabilities'].values():
                require(set(row)=={'class',*FIELDS},'All original exact SDK capability fields required')
                if row['class'] in families:observed.add((row['class'],*(float(row[k]) for k in FIELDS)))
    require(observed=={tuple(v) for v in inventory['profiles'][profile]['selected_case_signatures']} and
            len(structural_projection(observed))==16,'Actual original nine-scene SDK coverage differs from immutable reference')
    require(all(r['diagnostic_only'] is True and r['native_admission_qualified'] is False and r['phase6_complete'] is False
                for r in (capture,audit)),'Diagnostic observer controls cannot grant normal or complete class qualification')
    return dict(status='captured-and-audited-original-nine-scene-capability-observer-controls-only',profile=profile,
                cases=CASES,repeats=2,observer_lanes=['off','on'],actual_processes=processes,
                full_17_field_signatures_observed=sorted(observed),non_mass_structural_combinations=16,
                all_22_full_17_field_variants_independent_audit_pending=True,published_raw_independent_replay_pending=True,
                metadata_sha256={str(p):sha(p) for p in (capture_path,audit_path)},
                complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)


def prepared_body():
    body=runtime_writer.prepared_body()
    changes=[("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-capabilities-v1'"),
             ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-capabilities'"),
             ("ROOT/'out/native-writer-container.json'","ROOT/'out/native-capability-container.json'")]
    for before,after in changes:
        require(body.count(before)==(2 if 'container.json' in before else 1),'Conserved complete native runtime setup anchor differs')
        body=body.replace(before,after)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from hosted_native_general_api import source_identity
        from hosted_class_capabilities import reference_inventory,inspect_profile,CASES,sources
        from hosted_native_retry_reload_reference import bind,verify
        report['core_source_identity']=source_identity()
        report['original_capability_source_identity']=sources()
        inventory=reference_inventory();report['reference_inventory_sha256']=sha(ROOT/'out/class-capability-inventory/reference/inventory.json')
        reference=bind(a.profile);report['unchanged_original_reference']=reference;save()
        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-class-capabilities'/a.profile
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/RemainingVessels/native.py','--capability-control','--owner',str(ROOT),
            '--build',str(build/'engine'),'--build-record',str(build/'build.json'),
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--gtk-build-record',str(providers/'libdecor-candidate/build.json'),
            '--windows-reference',reference['capture'],'--windows-build',reference['build'],'--preserved',reference['preserved'],
            '--repeats','2','--runtime-role','diagnostic','--jobs','1','--output',str(capture)]
        for case in CASES:argv+=['--case',case]
        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('original-nine-scenes-both-repeats-observer-off-on',argv,14400,environment)
        audited=output/'original-capabilities-audit.json'
        run('original-complete-capability-audit',py+['Tests/Production/RemainingVessels/capabilities.py',
            '--capture',str(capture/'capabilities.json'),'--output',str(audited)],1800,environment)
        report['actual_capability_controls']=inspect_profile(a.profile,capture/'capabilities.json',audited)
        verify(reference)
        require(reference_inventory()==inventory and source_identity()==report['core_source_identity'] and
                sources()==report['original_capability_source_identity'],'Original reference, compiled core or capability sources changed during capture')
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    new="        report.update(status='captured-and-audited-original-nine-scene-capability-observer-controls-only',actual_processes=36,\n            published_raw_independent_replay_pending=True,complete_class_eligibility_qualified=False,normal_admission_qualified=False,hands_on_ready=False)"
    require(body.count(old)==1,'Conserved native completion anchor differs')
    return body.replace(old,new,1)


if __name__=='__main__':
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux',
            'Actual standard hosted Linux required; no local runtime capture')
    sources();reference_inventory()
    exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
