#!/usr/bin/env python3
"""Project original family persistence from unchanged complete normal-host captures; no recapture."""
import argparse
import os
import shutil
from pathlib import Path
import subprocess
from contracts import ROOT,PROFILES,PHASES,load,sha,require,atomic_json
import native_original_matrix_cli as matrix
import hosted_full_sdk_audit as source_binding
import hosted_capability_reference as original_family

CASES=['remaining_stock_003','remaining_stock_009','remaining_stock_013','remaining_stock_014',
       'remaining_stock_017','remaining_stock_018','remaining_stock_022','remaining_stock_026','remaining_stock_032']
FLAGS=('complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')


def family_cases(config):
    require(CASES==original_family.CASES,'Original nine-family persistence selection differs')
    result=[c for c in config['cases'] if c['id'] in CASES]
    require([c['id'] for c in result]==CASES and len(result)==9 and len(config['cases'])==38 and config['frames']==960,
            'Exact complete source scenes and original nine-family subset required')
    return result


def full_capture(capture,observed,profile,phase,config):
    cases=matrix.matrix.physical.complete_scope(capture,observed,profile,phase,config)
    selected=family_cases(config)
    require(all(c in cases for c in selected),'Family projection must come from the unchanged complete full capture')
    return selected


def process_identity(folder,source,phase,observed):
    receipt=load(folder/'process-receipt.json');invocation=load(folder/'invocation.json')
    actual=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']]
    require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and
            len(actual)==1 and actual[0]['start_ticks']>0 and actual[0]['argv']==invocation['argv'] and
            invocation['collector_producer_commit']==source and invocation['persistence_phase']==phase and
            invocation['runtime_role']=='normal' and Path(invocation['argv'][0]).name=='orbiter-production' and
            observed['lifecycle']==dict(rendered_frames=960,successful_presents=960,context_deleted=True),
            'Original actual normal-host process, immutable source, full frame and clean-exit witness required')
    return dict(pid=actual[0]['pid'],start_ticks=actual[0]['start_ticks'],argv=actual[0]['argv'],
                receipt_sha256=sha(folder/'process-receipt.json'),invocation_sha256=sha(folder/'invocation.json'))


def original_saved_input(native,windows,parent,native_input,windows_input,executed):
    saved=sha(parent/'Scenarios/(Current state).scn')
    require(native_input['saved_input_sha256']==windows_input['saved_input_sha256']==saved and
            sha(native/executed['scenario_entry_point'])==saved and sha(windows/executed['scenario_entry_point'])==saved,
            'Native and Windows reloads must consume the identical exact original Windows parent save')
    return saved


def audit(mode,phase):
    require(mode in ('automatic','sse2') and phase in PHASES and os.environ.get('NATIVE_PHASE')==phase,
            'One exact declared retained persistence math/phase cohort required')
    head=matrix.context();sources=source_binding.original_sources()
    output=ROOT/'out/class-family-persistence-audits'/(mode+'-'+phase+'.json')
    require(not output.exists(),'Fresh separate family persistence projection required');output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(protocol='phase6-original-family-persistence-from-complete-normal-captures-v1',status='running',
        auditor_source=head,math_profile=mode,phase=phase,profiles={},actual_original_native_processes=0,
        actual_direct_original_native_pairs=0,new_simulator_processes=0,original_capture_flags_rewritten=False,
        full_class_persistence_facet_pending=True,**{k:False for k in FLAGS})
    def save():atomic_json(output,report)
    save()
    try:
        collector=matrix.matrix.physical.writers if phase=='stock-writer' else matrix.matrix.physical.reloads
        reader=matrix.matrix.physical.persistence.bind_owner(ROOT,collector.SOURCE);config=reader.native.settings(reader.protocols.V2)
        selected=family_cases(config);proofs,aggregate,guards=matrix.phase_proofs(config);index={(p['profile'],p['phase']):p for p in proofs}
        reference,reference_guards,restored=matrix.independent_reference(head);guards.update(reference_guards)
        original_bindings=matrix.matrix.physical.original_bindings()
        original_ssim=reader.windows.image_ssim;scalar_api=ROOT/'out/native-matrix-scalar/api.json';scalar_archive=ROOT/'out/native-matrix-scalar/producer.zip'
        scalar=matrix.scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim);reader.native.shared.image_ssim=reader.windows.image_ssim
        report.update(complete_prior_physical_phase_aggregation=aggregate,original_full_reference=reference,
            original_raw_API_bindings=original_bindings,original_sources_sha256=sources,actual_scalar_binding=scalar,
            unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum'],
            exact_original_required_cases=CASES,original_frames=960,original_repeats=2)
        save();raw={}
        for configuration in ('Debug','Release'):
            profile=configuration+'-'+mode;proof=index[(profile,phase)]
            decoded,bound=matrix.bind_raw(profile,phase,proof)
            prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload'
            native=ROOT/'out'/prefix/profile
            require(not native.exists() and shutil.disk_usage(native.parent if native.parent.exists() else ROOT/'out').free>=sum(v.stat().st_size for v in decoded.rglob('*') if v.is_file())+8*1024**3,
                    'Fresh exact original-path native copy must retain the unchanged eight-GiB reserve')
            native.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(decoded,native)
            matrix.matrix.physical.bound_native_tree(Path(bound['payload']),native,profile,phase);raw[profile]=(native,bound)
            capture=load(native/'capture.json');observed=proof['report']['independent_native_observations']
            require(full_capture(capture,observed,profile,phase,config)==selected,'Original full source scope changed')
            historical,historical_guards=source_binding.bind_historical_sources(proof['report']['guarded_sources_sha256'],
                ROOT/'out/class-full-SDK-source-witnesses/family-persistence'/profile/phase,head);guards.update(historical_guards)
            prior=load(ROOT/'out/native-matrix-phase-payload'/(profile+'-'+phase)/'reference-audit-restoration/restoration.json')
            windows_root=ROOT/'out/original-stock-audit/transport'/profile
            windows=windows_root/('remaining-stock-repaired' if phase=='stock-writer' else 'remaining-stock-persistence')
            parent=windows_root/'remaining-stock-repaired';windows_capture=load(windows/'capture.json')
            cells={};record=dict(status='running',profile=profile,phase=phase,raw_native_binding=bound,
                full_capture_sha256=sha(native/'capture.json'),captured_runtime_role=capture['runtime_role'],captured_diagnostic_only=capture['diagnostic_only'],
                prior_physical_phase_artifact_id=proof['api_artifact_id'],prior_physical_report_sha256=proof['physical_report_sha256'],
                historical_source_bindings=historical,unchanged_original_reference=matrix.compare_reference(prior,restored),cases=cells)
            report['profiles'][profile]=record;save();identities=set()
            for case in selected:
                rows=[];cells[case['id']]=rows
                for repeat in (1,2):
                    name=case['id']+'-'+str(repeat);left=native/name;right=windows/name;ws=parent/name
                    captured=capture['cases'][case['id']]['runs'][repeat-1];previous=observed['cases'][case['id']]['runs'][repeat-1]
                    identity=process_identity(left,capture['producer_commit'],phase,previous)
                    token=(identity['pid'],identity['start_ticks']);require(token not in identities,'One actual process credited to multiple selected persistence runs');identities.add(token)
                    checked={}
                    for leaf,digest in captured['files_sha256'].items():
                        require(sha(left/leaf)==digest==bound['files_sha256'][name+'/'+leaf],'Selected native byte differs from exact complete raw API member')
                        checked[str(left/leaf)]=digest
                    win_record=windows_capture['cases'][case['id']]['runs'][repeat-1]
                    prefix='remaining-stock-repaired' if phase=='stock-writer' else 'remaining-stock-persistence'
                    for leaf,digest in win_record['files_sha256'].items():
                        require(sha(right/leaf)==digest==restored['original_api_archive_bindings'][profile]['decoded_members_sha256'][prefix+'/'+name+'/'+leaf],
                                'Selected original Windows byte differs from its exact original raw API member')
                        checked[str(right/leaf)]=digest
                    saved=reader.inspect_save(left,reader.protocol())
                    require(saved==captured['saved_state']==previous['saved_state'] and
                            load(left/'persistence-input.json')==captured['persistence_input']==previous['persistence_input'],
                            'Actual complete native saved content or original persistence descriptor differs')
                    saved_input=None
                    if phase=='stock-writer':require(captured['executed_case']==previous['executed_case']==case,'Original stock scene was substituted')
                    else:
                        saved_input=original_saved_input(left,right,ws,captured['persistence_input'],load(right/'persistence-input.json'),captured['executed_case'])
                        derived,provenance=reader.derived_case(case,config,left/captured['executed_case']['scenario_entry_point'],saved_input)
                        require(derived==captured['executed_case']==previous['executed_case'] and
                                all(captured['persistence_input'][k]==v for k,v in provenance.items()),'Original derived input, full vessel roster or provenance differs')
                    pair=matrix.matrix.physical.persistence.compare_pair(right,left,reader,config)
                    calibration=matrix.matrix.physical.persistence.serialization_calibration(ws,windows_root/'remaining-stock-persistence'/name,reader)
                    require(dict(direct_original_native=pair,original_windows_roundtrip=calibration)==proof['report']['cases'][case['id']]['runs'][repeat-1],
                            'Reexecuted unchanged persistence comparisons must reproduce the complete original physical report exactly')
                    rows.append(dict(repeat=repeat,actual_original_native_process=identity,original_full_observation=previous,
                        complete_saved_state=saved,exact_original_windows_save_input_sha256=saved_input,
                        direct_original_native=pair,original_windows_roundtrip=calibration,files_sha256=checked))
                    report['actual_original_native_processes']+=1;report['actual_direct_original_native_pairs']+=1;save()
            require(len(identities)==18 and set(cells)==set(CASES) and all(len(v)==2 for v in cells.values()),'Every original family case and both actual repetitions required')
            require(matrix.bind_raw(profile,phase,proof,Path(bound['payload']),decode=False)[1]==bound and
                    matrix.matrix.physical.bound_native_tree(Path(bound['payload']),native,profile,phase)==proof['report']['native_decoded_tree_sha256'],
                    'Complete raw observations or original canonical paths changed during persistence projection')
            record.update(status='passed-one-profile-original-family-persistence-projection-only',actual_original_native_processes=18,actual_original_successful_presents=17280,original_full_capture_role_and_flags_preserved=True);save()
        require(set(report['profiles'])=={c+'-'+mode for c in ('Debug','Release')} and report['actual_original_native_processes']==report['actual_direct_original_native_pairs']==36,
                'Both source-bound native configuration cohorts and all36 selected original processes required')
        require(source_binding.original_sources()==sources and matrix.matrix.complete_phase_matrix(proofs,config)==aggregate and
                matrix.independent_reference(head)==(reference,reference_guards,restored) and matrix.matrix.physical.original_bindings()==original_bindings and
                matrix.scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim)==scalar and all(sha(path)==digest for path,digest in guards.items()),
                'Original sources, all physical APIs/member proofs, scalar, raw inputs or original retry guards changed')
        report.update(status='passed-two-profile-original-family-persistence-projection-only',guarded_inputs_sha256=guards,
            all_original_comparisons_reproduced_exactly=True,actual_original_successful_presents=34560,
            complete_raw_and_source_witnesses_kept_on_GitHub=True,full_original_capture_flags_unchanged=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status']+' '+mode+' '+phase)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True);p.add_argument('--phase',choices=PHASES,required=True);a=p.parse_args();audit(a.math_profile,a.phase)
