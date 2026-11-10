#!/usr/bin/env python3
"""Independently close published family save/reload projections against every original full phase."""
import argparse
import hashlib
import json
import math
from pathlib import Path,PurePosixPath
from contracts import ROOT,PROFILES,PHASES,load,sha,require,atomic_json
import hosted_family_persistence as family
import verify_published_full_SDK as archive_reader
import final_hosted_class_capabilities as closed

LOCK=ROOT/'Tests/Production/Closeout/family-persistence-published-inputs-v1.lock.json'
CI=PurePosixPath('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')
SOURCE='6cee4bee7e2c258cbfce003184d2b713421cf193'


def full_cells(profiles):
    require(set(profiles)=={p+'/'+q for p in PROFILES for q in PHASES},'Every original family profile and both phases required')
    for key,value in profiles.items():
        profile,phase=key.split('/',1)
        require(value['profile']==profile and value['phase']==phase and value['actual_original_native_processes']==18 and
                value['actual_original_successful_presents']==17280 and value['cases']==family.CASES and value['repeats']==2 and
                value['full_capture_normal_role_and_flags_preserved'] is True and value['original_comparisons_and_raw_member_bindings_verified'] is True,
                'Complete original family cases, repetitions, full frames, unchanged input flags and direct comparison closure required')
    return dict(passed_class_facets=['persistence'],actual_original_native_processes=144,actual_original_successful_presents=138240,
                original_cases=family.CASES,repeats=2,profiles=list(PROFILES),phases=list(PHASES),new_simulator_processes=0,
                historical_capture_or_pending_flags_relabelled=False,**{k:False for k in family.FLAGS})


def source_witnesses(value,prior,source,bodies,guards):
    bindings=value['historical_source_bindings'];expected=prior['report']['guarded_sources_sha256'];witnesses={}
    require(set(bindings)==set(expected),'Every exact original phase-owned source guard must remain represented')
    for original_name,entry in bindings.items():
        relative=family.source_binding.source_relative(original_name)
        name='class-full-SDK-source-witnesses/family-persistence/'+value['profile']+'/'+value['phase']+'/'+relative
        require(entry['relative']==relative and entry['historical_source']==family.matrix.matrix.SOURCE and entry['current_source']==source and
                entry['historical_report_rewritten'] is False and entry['current_file_replaced'] is False and
                hashlib.sha256(bodies[name]).hexdigest()==expected[original_name]==entry['historical_sha256']==closed.gitsha(entry['historical_source'],relative) and
                closed.gitsha(source,relative)==entry['current_sha256'] and
                guards[entry['immutable_historical_witness']]==entry['historical_sha256'] and guards[str(CI/relative)]==entry['current_sha256'],
                'Every exact actual original and current source witness must retain its separate immutable owner')
        witnesses[name]=entry['historical_sha256']
    return witnesses


def selected_file_closure(profile,phase,case,repeat,observed,raw,original_members,config,reader):
    folder=case+'-'+str(repeat);native_prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload'
    windows_prefix='remaining-stock-repaired' if phase=='stock-writer' else 'remaining-stock-persistence'
    native_root=CI/'out'/native_prefix/profile;windows_root=CI/'out/original-stock-audit/transport'/profile/windows_prefix
    # The immutable native reader records every flat process output. Nested private
    # assets remain bound by the complete raw tree; exact derived inputs are checked separately.
    checked=raw['raw_proof']['checked_retained_members_sha256'];base=native_prefix+'/'+profile+'/'+folder+'/'
    native_files={str(native_root/folder/PurePosixPath(name).relative_to(base)):digest for name,digest in checked.items()
        if name.startswith(base) and len(PurePosixPath(name).relative_to(base).parts)==1}
    require(native_files and all(raw['files_sha256'][PurePosixPath(name).relative_to(native_root).as_posix()]==digest for name,digest in native_files.items()),
            'Every source-owned actual native process output must match the complete raw tree')
    executed=observed['executed_case'];prefix='Flights/'+executed.get('recording_directory','')+'/'
    recordings=[name for name in config['recording_files_sha256_lf'] if executed['playback_vessels'] and name.startswith(prefix)]
    names=[*reader.windows.shared.TRACES,'stock-clock.csv','stock-vessel-complete.txt','scene.csv','scene.rgba','scene-summary.json','camera.csv',
        'renderer-info.json','graphics-lifecycle.json','renderer-modules.txt','invocation.json','mesa-bindings.json','math-profile.txt',
        'console.txt','Orbiter.log','Orbiter.cfg','process-result.json','reference-variant.json','actual-data-inputs.json',
        executed['scenario_entry_point'],*recordings,*[item['target'] for item in config['delivery_repairs']],
        'stock-step-clock.csv',reader.protocols.MARKER,reader.windows.configuration_input.SNAPSHOT]
    if windows_prefix+'/'+folder+'/process-timing.json' in original_members:names.append('process-timing.json')
    if phase=='windows-save-reload':names.extend(('Scenarios/(Current state).scn','persistence-input.json'))
    windows_files={str(windows_root/folder/name):original_members[windows_prefix+'/'+folder+'/'+name] for name in names}
    return native_files|windows_files


def summarize(record,cell,bodies,prior_index,config):
    mode,phase=cell.split('/',1);source=record['run']['head_sha'];name='class-family-persistence-audits/'+mode+'-'+phase+'.json';report=json.loads(bodies[name])
    require(source==SOURCE and report['protocol']=='phase6-original-family-persistence-from-complete-normal-captures-v1' and
            report['status']=='passed-two-profile-original-family-persistence-projection-only' and report['auditor_source']==source and
            report['math_profile']==mode and report['phase']==phase and report['actual_original_native_processes']==report['actual_direct_original_native_pairs']==36 and
            report['actual_original_successful_presents']==34560 and report['new_simulator_processes']==0 and report['original_capture_flags_rewritten'] is False and
            report['full_class_persistence_facet_pending'] is True and report['all_original_comparisons_reproduced_exactly'] is True and
            report['complete_raw_and_source_witnesses_kept_on_GitHub'] is True and report['full_original_capture_flags_unchanged'] is True and
            report['exact_original_required_cases']==family.CASES and report['original_frames']==960 and report['original_repeats']==2 and
            report['complete_prior_physical_phase_aggregation']==family.matrix.matrix.complete_phase_matrix(list(prior_index.values()),config) and
            all(report[k] is False for k in family.FLAGS),'Complete original no-recapture family persistence source/scope required')
    closed.controls(bodies,'family-persistence-controls.json',source,380)
    relative='Tests/Production/Closeout/hosted_family_persistence.py'
    require(sha(ROOT/relative)==closed.gitsha(source,relative) and report['original_sources_sha256']==family.source_binding.original_sources() and
            report['unchanged_budgets']==config['budgets'] and report['unchanged_image_ssim_minimum']==config['image_ssim_minimum'],
            'Exact original persistence/physical comparators and their immutable replay owner and budgets required')
    require(set(report['profiles'])=={c+'-'+mode for c in ('Debug','Release')},'Both native configuration profiles required')
    collector=family.matrix.matrix.physical.writers if phase=='stock-writer' else family.matrix.matrix.physical.reloads
    reader=family.matrix.matrix.physical.persistence.bind_owner(ROOT,collector.SOURCE)
    result={};witnesses={}
    for profile,value in report['profiles'].items():
        prior=prior_index[(profile,phase)];old=prior['report'];raw=value['raw_native_binding'];collector=family.matrix.matrix.physical.writers if phase=='stock-writer' else family.matrix.matrix.physical.reloads
        api=json.loads(bodies['native-matrix-native-inputs/'+profile+'-'+phase+'/api.json']);collector.validate_api(api,profile)
        require(value['status']=='passed-one-profile-original-family-persistence-projection-only' and value['profile']==profile and value['phase']==phase and
                value['captured_runtime_role']=='normal' and value['captured_diagnostic_only'] is False and value['original_full_capture_role_and_flags_preserved'] is True and
                value['actual_original_native_processes']==18 and value['actual_original_successful_presents']==17280 and
                value['prior_physical_phase_artifact_id']==prior['api_artifact_id'] and value['prior_physical_report_sha256']==prior['physical_report_sha256'] and
                value['full_capture_sha256']==old['independent_native_observations']['capture_sha256'] and
                raw['raw_proof']==old['raw_native_proof'] and raw['files_sha256']==old['native_decoded_tree_sha256'] and
                raw['archive_sha256']==api['artifact']['digest'].removeprefix('sha256:') and
                raw['api_sha256']==hashlib.sha256(bodies['native-matrix-native-inputs/'+profile+'-'+phase+'/api.json']).hexdigest() and
                report['original_raw_API_bindings']==old['original_api_bindings'] and
                all(report['actual_scalar_binding'][key]==old['actual_scalar_binding'][key] for key in ('original_source','original_api_archive_sha256','verification_sha256')) and
                report['actual_scalar_binding']['source_api_sha256']==hashlib.sha256(bodies['native-matrix-scalar/api.json']).hexdigest(),
                'Every actual complete raw/native/reference source and independently published full physical phase must remain identical')
        require(value['unchanged_original_reference']['raw_API_and_log_transport_identities_preserved'] is True and
                value['unchanged_original_reference']['API_attempts_normalized'] is False and
                value['unchanged_original_reference']['old_failed_attempt_relabelled'] is False,'Original successful/failed reference API and raw log identities must remain distinct')
        witnesses.update(source_witnesses(value,prior,source,bodies,report['guarded_inputs_sha256']))
        require(set(value['cases'])==set(family.CASES),'Every original family case required')
        native_prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload'
        windows_prefix='remaining-stock-repaired' if phase=='stock-writer' else 'remaining-stock-persistence'
        native_root=CI/'out'/native_prefix/profile;windows_root=CI/'out/original-stock-audit/transport'/profile/windows_prefix
        original_members=report['original_raw_API_bindings'][profile]['decoded_members_sha256'];identities=set()
        for case,runs in value['cases'].items():
            require(len(runs)==2 and [r['repeat'] for r in runs]==[1,2],'Both actual family repetitions required')
            for repeat,run in enumerate(runs,1):
                observed=old['independent_native_observations']['cases'][case]['runs'][repeat-1];prior_pair=old['cases'][case]['runs'][repeat-1];identity=run['actual_original_native_process']
                folder=case+'-'+str(repeat);token=(identity['pid'],identity['start_ticks'])
                require(identity['pid']>0 and identity['start_ticks']>0 and token not in identities and identity['argv'] and
                        PurePosixPath(identity['argv'][0]).name=='orbiter-production' and run['original_full_observation']==observed and
                        observed['lifecycle']==dict(rendered_frames=960,successful_presents=960,context_deleted=True) and
                        run['complete_saved_state']==observed['saved_state'] and
                        run['direct_original_native']==prior_pair['direct_original_native'] and
                        run['original_windows_roundtrip']==prior_pair['original_windows_roundtrip'],
                        'Every actual process/start/full observation/complete serialization/direct comparison must match its original physical proof')
                identities.add(token)
                require(identity['receipt_sha256']==raw['files_sha256'][folder+'/process-receipt.json'] and
                        identity['invocation_sha256']==raw['files_sha256'][folder+'/invocation.json'],'Actual original process/OS argv receipts must remain bound')
                require(run['files_sha256']==selected_file_closure(profile,phase,case,repeat,observed,raw,original_members,config,reader),
                        'Every source-owned original/native process output and derived-input file must retain its exact complete archive-member digest')
                pair=run['direct_original_native'];require(pair['complete_saved_content_identical'] is True and pair['actual_clocks_identical_lf'] is True and
                        math.isfinite(pair['ssim']) and pair['ssim']>=config['image_ssim_minimum'],'Original complete saved content, clocks and full-frame tolerance must remain unchanged')
                saved=run['exact_original_windows_save_input_sha256']
                if phase=='stock-writer':require(saved is None,'Stock input must retain its original phase without relabelling')
                else:
                    expected=original_members['remaining-stock-repaired/'+folder+'/Scenarios/(Current state).scn'];entry=observed['executed_case']['scenario_entry_point']
                    require(saved==expected==observed['persistence_input']['saved_input_sha256']==raw['files_sha256'][folder+'/'+entry]==original_members[windows_prefix+'/'+folder+'/'+entry],
                            'Every actual native and Windows reload must consume the same exact original Windows parent save')
        require(len(identities)==18,'Every actual selected normal-host process must remain distinct')
        result[profile+'/'+phase]=dict(profile=profile,phase=phase,actual_original_native_processes=18,actual_original_successful_presents=17280,
            cases=family.CASES,repeats=2,full_capture_normal_role_and_flags_preserved=True,original_comparisons_and_raw_member_bindings_verified=True,
            raw_native_artifact_id=api['artifact']['id'],raw_native_archive_sha256=raw['archive_sha256'],full_capture_sha256=value['full_capture_sha256'],
            physical_phase_artifact_id=prior['api_artifact_id'],physical_report_sha256=prior['physical_report_sha256'],
            exact_original_source_guard_count=len(value['historical_source_bindings']))
    return dict(profiles=result,published_source_witnesses_sha256=witnesses,full_report_sha256=hashlib.sha256(bodies[name]).hexdigest(),source_controls_passed=380)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();head=family.matrix.context()
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out'),'Fresh separate hosted persistence publication proof required');a.output.mkdir(parents=True)
    reader=family.matrix.matrix.physical.persistence.bind_owner(ROOT,family.matrix.matrix.physical.writers.SOURCE);config=reader.native.settings(reader.protocols.V2)
    priors,aggregate,guards=family.matrix.phase_proofs(config);prior_index={(v['profile'],v['phase']):v for v in priors}
    lock=load(LOCK);profiles={};inputs={};witnesses={}
    for cell,pin in lock['cells'].items():
        mode,phase=cell.split('/',1);base=ROOT/'out/family-persistence-published'/mode/phase;api=load(base/'api.json');closed.validate_api(api,pin)
        archive=base/'producer.zip';require(archive.stat().st_size==pin['archive_bytes'] and sha(archive)==pin['archive_sha256'],'Exact complete published family persistence ZIP required')
        members,bodies=archive_reader.inspect_members(archive);summary=summarize(api,cell,bodies,prior_index,config)
        require(not set(profiles)&set(summary['profiles']),'One original family profile/phase credited more than once');profiles.update(summary['profiles']);witnesses.update(summary['published_source_witnesses_sha256'])
        inputs[cell]=dict(source=pin['source'],run_id=pin['run_id'],artifact_id=pin['artifact_id'],archive_bytes=pin['archive_bytes'],archive_sha256=pin['archive_sha256'],api_sha256=sha(base/'api.json'),members_sha256=members,full_report_sha256=summary['full_report_sha256'])
        require(sha(archive)==pin['archive_sha256'],'Published source-witness archive changed during inspection')
    facet=full_cells(profiles)
    require(family.matrix.matrix.complete_phase_matrix(priors,config)==aggregate and all(sha(p)==d for p,d in guards.items()),'Every exact original full phase/API/member guard must remain intact')
    report=dict(protocol='phase6-independent-published-original-family-persistence-facet-v1',status='verified-four-profile-original-family-persistence-facet-only',auditor_source=head,
        persistence_facet=facet,profiles=profiles,inputs=inputs,published_source_witnesses_sha256=witnesses,complete_original_physical_phase_aggregation=aggregate,
        input_lock_sha256=sha(LOCK),all_original_complete_capture_flags_preserved=True,new_simulator_processes=0,**{k:False for k in family.FLAGS})
    atomic_json(a.output/'proof.json',report);print(report['status'])


if __name__=='__main__':main()
