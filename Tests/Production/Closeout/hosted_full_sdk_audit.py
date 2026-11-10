#!/usr/bin/env python3
"""Independently re-read every full original/native SDK variant without any new simulator."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from contracts import ROOT,PROFILES,require,sha,load,atomic_json
import native_original_matrix_cli as matrix_cli
from hosted_class_capabilities import reference_inventory
import hosted_capability_reference as reference

MATRIX_SOURCE='6206633c6ddc8b8e89af45fd1dd94b2e548f1450'


def original_sources():
    result=reference.sources()
    for name in ('native_original_matrix.py','native_original_matrix_cli.py','audit_native_original_cli.py','audit_native_original_phase.py'):
        relative='Tests/Production/Closeout/'+name;path=ROOT/relative
        require(path.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',MATRIX_SOURCE+':'+relative]),
                'Complete prior physical source/API/member/capacity guards changed: '+name)
        result[relative]=sha(path)
    return result


def source_relative(name):
    path=Path(name)
    if path.is_absolute():
        roots=(ROOT,Path('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform'))
        matches=[path.relative_to(parent) for parent in roots if path.is_relative_to(parent)]
        require(matches and all(p==matches[0] for p in matches),'Historical source outside its actual repository workspace')
        path=matches[0]
    require(path.parts and path.parts[0]=='Tests' and '..' not in path.parts and ':' not in str(path) and
            '\\' not in str(path) and path.suffix=='.py','Canonical tracked historical Python source required')
    return path.as_posix()


def bind_historical_sources(recorded,destination,current_source):
    historical_source=matrix_cli.matrix.SOURCE
    require(current_source==subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'Actual immutable current source owner required separately from historical sources')
    destination=Path(destination).resolve()
    require(recorded and not destination.exists() and destination.is_relative_to(ROOT/'out/class-full-SDK-source-witnesses'),
            'Fresh separate historical source witness required')
    destination.mkdir(parents=True);bindings={};guards={}
    for original_name,expected in recorded.items():
        relative=source_relative(original_name)
        old=subprocess.check_output(['git','-C',str(ROOT),'show',historical_source+':'+relative])
        require(hashlib.sha256(old).hexdigest()==expected,'Historical source differs from its exact immutable physical producer: '+original_name)
        snapshot=destination/relative;snapshot.parent.mkdir(parents=True,exist_ok=True)
        if snapshot.exists():require(snapshot.read_bytes()==old,'Aliased historical source snapshots differ')
        else:snapshot.write_bytes(old)
        current=ROOT/relative;new=subprocess.check_output(['git','-C',str(ROOT),'show',current_source+':'+relative])
        require(current.read_bytes()==new,'Actual current source differs from its separate immutable auditor owner: '+relative)
        require(sha(snapshot)==expected,'Actual historical source witness differs from recorded original bytes')
        bindings[original_name]=dict(relative=relative,historical_source=historical_source,historical_sha256=expected,
            immutable_historical_witness=str(snapshot),current_source=current_source,current_sha256=sha(current),
            historical_and_current_versions_identical=(old==new),historical_report_rewritten=False,current_file_replaced=False)
        guards[str(snapshot)]=expected;guards[str(current)]=sha(current)
    require(len(bindings)==len(recorded),'Every original relative and absolute source guard must remain represented')
    return bindings,guards


def compare_initial(native,original,case,budgets,families):
    expected=reference.capabilities.expected_population(case,original)
    actual=reference.capabilities.compare_capabilities(native,original,expected,budgets)
    left=reference.initial_signatures(Path(native)/'stock-vessel-state.csv',case['declared_vessels'],families)
    right=reference.initial_signatures(Path(original)/'stock-vessel-state.csv',case['declared_vessels'],families)
    require(left==right,'Actual full seventeen-field initial signatures differ')
    return actual,left,right


def coverage(profile,cases,native_signatures,original_signatures,inventory):
    expected={c['id'] for c in load(ROOT/'Tests/Production/RemainingStock/cases.json')['cases']}
    require(profile in PROFILES and len(expected)==38 and set(cases)==expected and
            all(len(runs)==2 and [r['repeat'] for r in runs]==[1,2] and
                all(r['all_17_fields_exact'] is True and r['original_port_budgets_unchanged'] is True and
                    r['actual_capabilities'] for r in runs) for runs in cases.values()),
            'All thirty-eight complete scenes and both actual SDK comparisons required')
    wanted={tuple(row) for row in inventory['profiles'][profile]['unique_signatures']}
    require(len(wanted)==22 and native_signatures==original_signatures==wanted,
            'Every actual full original SDK variant including all payload mass combinations required')
    supplemental={tuple(row) for row in inventory['full_17_field_variants_not_in_original_nine_cases']}
    require(len(supplemental)==5 and supplemental<=native_signatures and
            inventory['proposed_native_cases']==reference.CASES and inventory['fields']==list(reference.FIELDS),
            'All additional original mass variants and original nine-scene controls remain required')
    return dict(profile=profile,actual_initial_pairs=76,complete_scenes=38,repeats=2,full_17_field_signatures=sorted(wanted),
                additional_full_variants_observed=sorted(supplemental),all_original_17_fields_exact=True,
                docking_geometry_budget=0,attachment_budgets_unchanged=True,new_simulator_processes=0,
                original_nine_scene_144_process_controls_pending=True,complete_class_eligibility_qualified=False,
                normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)


def audit(mode):
    require(mode in ('automatic','sse2'),'Exact complete original math cohort required')
    head=matrix_cli.context();sources=original_sources();inventory=reference_inventory()
    output=ROOT/'out/class-full-SDK-variant-audits'/(mode+'.json')
    require(not output.exists(),'Fresh independent full SDK variant report required');output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(protocol='phase6-independent-full-original-native-initial-SDK-and-ports-v1',status='running',auditor_source=head,
                math_profile=mode,profiles={},actual_initial_pairs=0,new_simulator_processes=0,
                all_22_full_17_field_variants_pending=True,original_nine_scene_144_process_controls_pending=True,
                complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(output,report)
    save()
    try:
        reader=matrix_cli.matrix.physical.persistence.bind_owner(ROOT,matrix_cli.matrix.physical.writers.SOURCE)
        config=reader.native.settings(reader.protocols.V2)
        proofs,aggregate,guards=matrix_cli.phase_proofs(config);index={(p['profile'],p['phase']):p for p in proofs}
        original,reference_guards,restored=matrix_cli.independent_reference(head)
        bindings=matrix_cli.matrix.physical.original_bindings();guards.update(reference_guards)
        inventory_path=ROOT/'out/class-capability-inventory/reference/inventory.json';guards[str(inventory_path)]=sha(inventory_path)
        require(len(inventory['reference_files_sha256'])==612 and all(sha(path)==value for path,value in inventory['reference_files_sha256'].items()),
                'Every original SDK descriptor and parent must equal the independently published complete reference inventory')
        guards.update(inventory['reference_files_sha256']);families={row[0] for row in inventory['unique_signatures']}
        report.update(original_full_reference=original,original_raw_API_bindings=bindings,
                      complete_prior_physical_phase_aggregation=aggregate,original_sources_sha256=sources,
                      original_exact_comparison_fields=list(reference.FIELDS),unchanged_attachment_budgets=config['budgets'],
                      unchanged_docking_geometry_budget=0,inventory_sha256=sha(inventory_path))
        save();raw={}
        for configuration in ('Debug','Release'):
            profile=configuration+'-'+mode;selected=index[(profile,'stock-writer')]
            native,bound=matrix_cli.bind_raw(profile,'stock-writer',selected);raw[profile]=(native,bound)
            capture=load(native/'capture.json')
            cases=matrix_cli.matrix.physical.complete_scope(capture,selected['report']['independent_native_observations'],profile,'stock-writer',config)
            historical_bindings,historical_guards=bind_historical_sources(selected['report']['guarded_sources_sha256'],
                ROOT/'out/class-full-SDK-source-witnesses'/profile,head)
            guards.update(historical_guards)
            report.setdefault('historical_source_bindings',{})[profile]=historical_bindings;save()
            prior=load(ROOT/'out/native-matrix-phase-payload'/(profile+'-stock-writer')/'reference-audit-restoration/restoration.json')
            reference_comparison=matrix_cli.compare_reference(prior,restored)
            actual={};native_signatures=set();original_signatures=set()
            record=dict(status='running',raw_native_binding=bound,prior_physical_phase_artifact_id=selected['api_artifact_id'],
                        prior_physical_report_sha256=selected['physical_report_sha256'],unchanged_original_reference=reference_comparison,
                        capture_sha256=sha(native/'capture.json'),captured_normal_role=capture['runtime_role'],
                        captured_diagnostic_only=capture['diagnostic_only'],cases=actual)
            report['profiles'][profile]=record;save()
            windows=ROOT/'out/original-stock-audit/transport'/profile/'remaining-stock-repaired'
            original_members=restored['original_api_archive_bindings'][profile]['decoded_members_sha256']
            for case in cases:
                runs=[];actual[case['id']]=runs
                for repeat in (1,2):
                    name=case['id']+'-'+str(repeat);left=native/name;right=windows/name
                    checked={}
                    for filename in ('stock-vessel-state.csv','stock-vessel-docks.csv','stock-vessel-attachments.csv'):
                        expected_original=original_members['remaining-stock-repaired/'+name+'/'+filename]
                        require(sha(right/filename)==expected_original and
                                sha(left/filename)==bound['files_sha256'][name+'/'+filename],
                                'Actual native/original full SDK or port file differs from its immutable API-decoded member')
                        checked[str(left/filename)]=sha(left/filename);checked[str(right/filename)]=expected_original
                    caps,one,two=compare_initial(left,right,case,config['budgets'],families)
                    native_signatures.update(one);original_signatures.update(two)
                    runs.append(dict(repeat=repeat,actual_capabilities=caps,all_17_fields_exact=True,
                                     original_port_budgets_unchanged=True,files_sha256=checked))
                    report['actual_initial_pairs']+=1;save()
            summary=coverage(profile,actual,native_signatures,original_signatures,inventory)
            record.update(status='passed-full-original-native-initial-SDK-and-ports-only',coverage=summary)
            require(matrix_cli.bind_raw(profile,'stock-writer',selected,Path(bound['payload']),decode=False)[1]==bound,
                    'Actual retained native raw observations changed during independent SDK audit');save()
        require(set(report['profiles'])=={c+'-'+mode for c in ('Debug','Release')} and report['actual_initial_pairs']==152 and
                all(r['status']=='passed-full-original-native-initial-SDK-and-ports-only' for r in report['profiles'].values()),
                'Both complete native/original configuration cohorts and all152 actual initial pairs required')
        require(original_sources()==sources and reference_inventory()==inventory and
                matrix_cli.matrix.complete_phase_matrix(proofs,config)==aggregate and
                matrix_cli.independent_reference(head)==(original,reference_guards,restored) and
                matrix_cli.matrix.physical.original_bindings()==bindings and all(sha(path)==value for path,value in guards.items()),
                'Original source/API/ZIP/member/reference/inventory observations changed during independent SDK audit')
        report.update(status='passed-two-profile-full-original-native-initial-SDK-and-ports-only',
                      all_22_full_17_field_variants_pending=False,all_22_full_17_field_variants_replayed=True,all_historical_source_guards_verified_at_original_commit=True,
                      all_current_sources_separately_verified_at_auditor_commit=True,guarded_inputs_sha256=guards)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status']+' '+mode+' actual initial pairs '+str(report['actual_initial_pairs']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    audit(p.parse_args().math_profile)
