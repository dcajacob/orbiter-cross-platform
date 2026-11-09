#!/usr/bin/env python3
"""Hosted-only independent all-eight current/native/original stock and direct-current-build closure."""
import argparse
import json
import os
from pathlib import Path
import native_original_matrix_cli as previous
import current_native_matrix as matrix
from contracts import ROOT,require,sha,load,atomic_json

PAIRS={(m,p) for m in ('automatic','sse2') for p in ('stock','reload')}
BRANCH='qualification/current-native-matrix-v3'
WORKFLOW='.github/workflows/phase6-current-native-matrix.yml'
PAIR_STEPS=('Independently restore all original raw members and both real attempts',
 'Restore only the independently proven scalar and unchanged controls',
 'Directly compare every current native and current Debug Release pair','Run actions/upload-artifact@v7')


def plan():
    result=previous.plan()
    result.update(current_physical_source=matrix.SOURCE,current_physical_run_id=matrix.RUN,
        current_physical_jobs={str(j):'Independently audit current original '+' '.join(c) for c,j in matrix.JOBS.items()},
        current_capture_source=matrix.capture.CAPTURE,current_capture_run=matrix.capture.RUN,
        current_cells=[list(c) for c in sorted(matrix.JOBS)],current_phases=['stock','reload'])
    return result


def context():
    head=previous.context()
    for path in ('Tests/Production/RemainingStockPersistence/audit.py',
        'Tests/Production/CurrentWindows/Hosted/physical_observations.py',
        'Tests/Production/CurrentWindows/Hosted/audit_source_complete_shader_phase.py',
        'Tests/Production/CurrentWindows/Hosted/inspect_source_complete_shader_phase.py'):
        require((ROOT/path).read_bytes()==previous.subprocess.check_output(['git','-C',str(ROOT),'show',matrix.SOURCE+':'+path]),
            'Original current/native physical comparison source changed: '+path)
    return head


def phase_proofs(config):
    native_proofs,native_summary,guards=previous.phase_proofs(config)
    current=[]
    for cell in sorted(matrix.JOBS):
        base=ROOT/'out/current-matrix-phase-inputs'/('-'.join(cell));payload=ROOT/'out/current-matrix-phase-payload'/('-'.join(cell))
        proof=matrix.inspect_phase(load(base/'api.json'),base/'producer.zip',payload,cell,config)
        matrix.source_proof(proof['report'],matrix.SOURCE);current.append(proof)
        guards.update({str(base/'api.json'):sha(base/'api.json'),str(base/'producer.zip'):sha(base/'producer.zip')})
        guards.update({str(payload/n):v for n,v in proof['decoded_members_sha256'].items()})
    for proof in native_proofs:matrix.source_proof(proof['report'],matrix.native.SOURCE)
    return current,native_proofs,dict(current=matrix.aggregate(current,config),native= native_summary),guards


def partial(output,head):
    output=Path(output).resolve()
    require(output.is_relative_to(ROOT/'out/current-native-matrix-results') and not output.exists(),'Fresh separate current/native matrix partial report required')
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(protocol='phase6-direct-current-native-and-current-build-phase-v1',status='running',auditor_source=head,cases={},
        qualification_granted=False,phase6_complete=False,native_admission_qualified=False,
        other_class_lifetime_full157_and_hardware_gates_pending=True)
    atomic_json(output,result);return result


def reload_input(current,native,current_record,native_record,supplied,*,reader,case,config,original_parent):
    """Independently require each complete owning schema and the same exact original save."""
    current=Path(current);native=Path(native);original_parent=Path(original_parent);expected=supplied['sha256']
    current_input=current/current_record['executed_case']['scenario_entry_point']
    native_input=native/native_record['executed_case']['scenario_entry_point']
    parent=load(original_parent/'capture.json');parent_run=original_parent/supplied['parent_run']
    parent_save=parent_run/'Scenarios/(Current state).scn'
    require(supplied['parent_producer_commit']==parent['producer_commit']==matrix.native.physical.original.SOURCE and
        supplied['parent_capture_sha256']==sha(original_parent/'capture.json') and
        sha(parent_save)==sha(current_input)==sha(native_input)==expected,
        'Direct reloads must consume the same actual API-bound original saved bytes')
    derived,provenance=reader.derived_case(case,config,parent_save,expected)
    checked=reader.windows.inspect_artifacts(parent_run,case,config)
    native_provenance=provenance|dict(parent_capture_sha256=sha(original_parent/'capture.json'),parent_run=supplied['parent_run'],
        parent_finalized_clock=checked['matched_clock_observation'],parent_producer_commit=parent['producer_commit'],
        parent_startup_configuration=checked['configuration_input'],parent_source_variant_protocol='remaining-stock-repaired-sources-v4')
    require(current_record['executed_case']==native_record['executed_case']==derived and
        current_record['persistence_input']==provenance and native_record['persistence_input']==native_provenance,
        'Complete current derivation and all six native original-parent witnesses must retain their owning schemas')
    return dict(original_save_sha256=expected,actual_staged_inputs_identical=True,original_parent_run=supplied['parent_run'],
        original_parent_capture_sha256=supplied['parent_capture_sha256'],current_derivation=provenance,native_derivation=native_provenance,
        owning_receipts_preserved_without_rewriting=True)


def execution_identity(mode,phase,case,current,native,current_record,native_record,current_observation,native_observation,
                       *,reader,config,original_parent=None,supplied=None):
    """Compare implementation semantics while retaining both exact source-defined receipts."""
    require((mode,phase) in PAIRS,'Known complete execution profile required')
    implementation='sse2' if mode=='sse2' else 'fma3'
    native_math='amd-6121d02-'+implementation
    require(current_record['actual_math']==current_observation['actual_math']==implementation and
        native_record['actual_math']==native_observation['actual_math']==native_math,
        'Each actual math identifier must equal its exact independently audited owning implementation')
    require(current_record['executed_case']==native_record['executed_case']==native_observation['executed_case'] and
        native_record['persistence_input']==native_observation['persistence_input'],
        'Every raw native scene/provenance witness must equal its complete independent physical observation')
    saved=None;stock=None
    if phase=='stock':
        require(current_record['executed_case']==case and current_record['persistence_input'] is None,
            'Unchanged current stock scene with no reload derivation required')
        native_path=Path(native)/case['scenario_entry_point'];current_path=Path(current)/case['scenario_entry_point']
        expected=dict(protocol=reader.protocol()['protocol'],phase='stock-writer',original_parent_case=case,
            stock_input_sha256=sha(native_path),original_scenarios_and_scripts_unchanged=True,native_admission_qualified=False,phase6_complete=False)
        require(native_record['persistence_input']==expected and
            matrix.hashlib.sha256(current_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==
            matrix.hashlib.sha256(native_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==case['sha256_lf'],
            'Both stock inputs must retain the original frozen scene and the complete native owning descriptor')
        stock=dict(current_input_sha256=sha(current_path),native_input_sha256=sha(native_path),
            frozen_scene_sha256_lf=case['sha256_lf'],current_descriptor=None,native_descriptor=expected)
    else:
        require(supplied is not None and original_parent is not None,'Actual complete independently restored original parent required')
        saved=reload_input(current,native,current_record,native_record,supplied,
            reader=reader,case=case,config=config,original_parent=original_parent)
    return dict(current_actual_math=current_record['actual_math'],native_actual_math=native_record['actual_math'],
        source_defined_implementation=implementation,owning_identifiers_preserved_without_rewriting=True,
        stock_inputs=stock,exact_saved_input=saved)


def direct_pairs(mode,phase,output):
    require((mode,phase) in PAIRS,'Exact complete direct current/native build phase required');head=context();result=partial(output,head)
    result.update(math_profile=mode,phase=phase,required_cases=38,required_repeats=2,required_frames=960,
        actual_current_native_pairs=0,actual_current_build_pairs=0,full_four_pair_aggregation_pending=True)
    def save():atomic_json(output,result)
    save()
    try:
        native_phase=matrix.PHASES[phase];owner=matrix.native.physical.writers.SOURCE if phase=='stock' else matrix.native.physical.reloads.SOURCE
        reader=matrix.native.physical.persistence.bind_owner(ROOT,owner);config=reader.native.settings(reader.protocols.V2)
        current_proofs,native_proofs,aggregates,guards=phase_proofs(config)
        ci={tuple(p['cell']):p for p in current_proofs};ni={(p['profile'],p['phase']):p for p in native_proofs}
        reference,reference_guards,restored=previous.independent_reference(head);guards.update(reference_guards)
        scalar_api=ROOT/'out/native-matrix-scalar/api.json';scalar_archive=ROOT/'out/native-matrix-scalar/producer.zip'
        original_ssim=reader.windows.image_ssim;scalar=previous.scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim)
        reader.native.shared.image_ssim=reader.windows.image_ssim
        source_guards=matrix.native.physical.guarded_sources(reader)
        current={};native={};bindings={};requests={};workers={};native_captures={};reference_comparisons={}
        for configuration in ('Debug','Release'):
            profile=configuration+'-'+mode;cell=(configuration,mode,phase);cproof=ci[cell];nproof=ni[(profile,native_phase)]
            current[profile],cb,requests[profile],workers[profile]=matrix.bind_raw(cell,cproof)
            native[profile],nb=previous.bind_raw(profile,native_phase,nproof)
            bindings[profile]=dict(current=cb,native=nb);native_captures[profile]=load(native[profile]/'capture.json')
            original=cproof['report']['original_binding'];other=nproof['report']['original_api_bindings'][profile]
            require(all(original[k]==other[k]==restored['original_api_archive_bindings'][profile][k] for k in
                ('archive_sha256','archive_bytes','decoded_members_sha256','original_stock_job_id','transport_protocol')),
                'Current and native must bind the same independently restored original source/member cohort')
            reference_comparisons[profile]={}
            for cohort,base in [('current',ROOT/'out/current-matrix-phase-payload'/('-'.join(cell))),
                ('native',ROOT/'out/native-matrix-phase-payload'/(profile+'-'+native_phase))]:
                reference_comparisons[profile][cohort]=previous.compare_reference(load(base/'reference-audit-restoration/restoration.json'),restored)
        result.update(complete_phase_aggregation=aggregates,original_reference=reference,original_retry_reference_comparisons=reference_comparisons,
            actual_scalar_binding=scalar,raw_observation_bindings=bindings,guarded_sources_sha256=source_guards,
            guarded_phase_and_reference_inputs_sha256=guards,unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum'])
        save()
        for case in config['cases']:
            runs=[];result['cases'][case['id']]=dict(runs=runs)
            for repeat in (1,2):
                result.update(active_case=case['id'],active_repeat=repeat);save();name=case['id']+'-'+str(repeat);observed=dict(current_native={})
                runs.append(observed)
                for configuration in ('Debug','Release'):
                    profile=configuration+'-'+mode;cell=(configuration,mode,phase)
                    current_record=workers[profile]['cases'][mode+'-'+phase+'-'+case['id']]['runs'][repeat-1]
                    native_record=native_captures[profile]['cases'][case['id']]['runs'][repeat-1]
                    actual=ci[cell]['report']['cases'][case['id']]['runs'][repeat-1]['actual_observation']['observation']
                    nactual=ni[(profile,native_phase)]['report']['independent_native_observations']['cases'][case['id']]['runs'][repeat-1]
                    parent=ROOT/'out/original-stock-audit/transport'/profile/'remaining-stock-repaired'
                    supplied=None
                    if phase=='reload':
                        supplied,parent_save=matrix.observations.paired_input(parent,case,repeat,requests[profile],
                            restored['original_api_archive_bindings'][profile]['decoded_members_sha256'],reader)
                    identity=execution_identity(mode,phase,case,current[profile]/name,native[profile]/name,
                        current_record,native_record,actual,nactual,reader=reader,config=config,original_parent=parent,supplied=supplied)
                    same_input=identity['exact_saved_input']
                    pair=matrix.native.physical.persistence.compare_pair(current[profile]/name,native[profile]/name,reader,config)
                    observed['current_native'][configuration]=dict(comparison=pair,exact_saved_input=same_input,execution_identity=identity)
                    result['actual_current_native_pairs']+=1;save()
                require(workers['Debug-'+mode]['cases'][mode+'-'+phase+'-'+case['id']]['runs'][repeat-1]['actual_math']==
                    workers['Release-'+mode]['cases'][mode+'-'+phase+'-'+case['id']]['runs'][repeat-1]['actual_math'],
                    'Current Debug/Release actual CRT modes differ')
                observed['current_build']=matrix.observations.compare_windows_pair(current['Debug-'+mode]/name,current['Release-'+mode]/name,reader,config)
                result['actual_current_build_pairs']+=1;save()
        require(len(result['cases'])==38 and result['actual_current_native_pairs']==152 and result['actual_current_build_pairs']==76,
            'Every direct current/native and current Debug/Release pair required; no transitive or subset credit')
        for configuration in ('Debug','Release'):
            profile=configuration+'-'+mode;cell=(configuration,mode,phase)
            require(matrix.bind_raw(cell,ci[cell],Path(bindings[profile]['current']['payload']),decode=False)[1]==bindings[profile]['current'] and
                previous.bind_raw(profile,native_phase,ni[(profile,native_phase)],Path(bindings[profile]['native']['payload']),decode=False)[1]==bindings[profile]['native'],
                'Any actual raw current/native member changed during comparison')
        require(previous.independent_reference(head)==(reference,reference_guards,restored) and
            previous.scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim)==scalar and
            matrix.native.physical.guarded_sources(reader)==source_guards and
            all(sha(p)==v for p,v in (guards|source_guards).items()),'Physical/source/scalar/original raw input changed during direct comparisons')
        result.update(status='passed-one-complete-direct-current-native-and-current-build-phase-only')
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:save()
    return result


def pair_api(record,head,run_id,mode,phase):
    require((mode,phase) in PAIRS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact current/native direct pair API required')
    run=record['run'];jobs=record['jobs'];artifact=record['artifact']
    require(run['id']==run_id and run['head_sha']==head and run['run_attempt']==1 and run['head_branch']==BRANCH and run['path']==WORKFLOW and
        run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False,
        'Actual same-source/run direct pair producer required; preserve actual overall run status while final job is active')
    names={'Direct current native builds '+m+' '+p for m,p in PAIRS};selected=[j for j in jobs if j['name'] in names|{'readiness'}]
    require(len(jobs)==6 and len(selected)==5 and {j['name'] for j in selected}==names|{'readiness'} and
        all(j['run_id']==run_id and j['head_sha']==head and j['run_attempt']==1 and j['status']=='completed' and
            j['conclusion']=='success' and 'ubuntu-24.04' in j['labels'] and 'self-hosted' not in j['labels'] for j in selected),
        'All four exact successful direct comparison jobs and readiness required')
    for job in selected:
        for name in (('Require all actual current and native physical phases','Verify exact pinned artifact download retries without weakening byte guards') if job['name']=='readiness' else PAIR_STEPS):
            steps=[s for s in job['steps'] if s['name']==name]
            require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','Actual direct comparison step required: '+name)
    require(artifact['name']=='current-native-direct-build-'+mode+'-'+phase and type(artifact['id']) is int and artifact['id']>0 and
        artifact['expired'] is False and type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<4*1024**3 and
        matrix.native.re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==head,
        'Exact successful same-source current/native direct comparison artifact required')


def pair_scope(report,mode,phase,head,aggregates,config):
    require(report['protocol']=='phase6-direct-current-native-and-current-build-phase-v1' and
        report['status']=='passed-one-complete-direct-current-native-and-current-build-phase-only' and
        report['auditor_source']==head and (report['math_profile'],report['phase'])==(mode,phase) and
        report['required_cases']==38 and report['required_repeats']==2 and report['required_frames']==960 and
        report['actual_current_native_pairs']==152 and report['actual_current_build_pairs']==76 and
        report['complete_phase_aggregation']==aggregates and report['unchanged_budgets']==config['budgets'] and
        report['unchanged_image_ssim_minimum']==config['image_ssim_minimum'] and
        set(report['cases'])=={c['id'] for c in config['cases']} and all(len(c['runs'])==2 for c in report['cases'].values()) and
        all(report[k] is False for k in ('qualification_granted','phase6_complete','native_admission_qualified')) and
        report['other_class_lifetime_full157_and_hardware_gates_pending'] is True and report['full_four_pair_aggregation_pending'] is True and
        report['guarded_sources_sha256'] and report['guarded_phase_and_reference_inputs_sha256'] and report['actual_scalar_binding'] and
        report['original_reference'] and set(report['raw_observation_bindings'])=={'Debug-'+mode,'Release-'+mode} and
        set(report['original_retry_reference_comparisons'])=={'Debug-'+mode,'Release-'+mode},
        'Complete exact-source current/native and current-build direct comparison phase required')
    for profile,cohorts in report['original_retry_reference_comparisons'].items():
        require(set(cohorts)=={'current','native'} and all(v['API_attempts_normalized'] is False and v['old_failed_attempt_relabelled'] is False for v in cohorts.values()),
            'Both exact original retry identities must be preserved without normalization or relabeling')
    for case in report['cases'].values():
        for run in case['runs']:
            require(set(run)=={'current_native','current_build'} and set(run['current_native'])=={'Debug','Release'},'Every independent direct comparison required')
            for selected in [run['current_build'],*[v['comparison'] for v in run['current_native'].values()]]:
                require(selected['complete_saved_content_identical'] is True and selected['actual_clocks_identical_lf'] is True and
                    type(selected['ssim']) in (int,float) and matrix.math.isfinite(selected['ssim']) and selected['ssim']>=config['image_ssim_minimum'] and
                    all(k in selected for k in ('state','camera','detail_calibration_only')),'Every complete actual direct full-frame/state/clock/saved-content result required')
            for value in run['current_native'].values():
                identity=value['execution_identity'];implementation='sse2' if mode=='sse2' else 'fma3'
                require(identity['current_actual_math']==identity['source_defined_implementation']==implementation and
                    identity['native_actual_math']=='amd-6121d02-'+implementation and identity['owning_identifiers_preserved_without_rewriting'] is True and
                    identity['exact_saved_input']==value['exact_saved_input'],
                    'Both source-defined actual implementation identifiers and input proofs must be preserved')
                same=value['exact_saved_input']
                require((phase=='stock' and same is None) or (phase=='reload' and same['actual_staged_inputs_identical'] is True and
                    matrix.native.re.fullmatch('[0-9a-f]{64}',same['original_save_sha256']) and same['original_parent_run'] and
                    matrix.native.re.fullmatch('[0-9a-f]{64}',same['original_parent_capture_sha256'])),'Both actual current/native reload inputs must preserve exact original-save identity')


def final_matrix(output):
    head=context();result=partial(output,head);result['protocol']='phase6-independent-complete-current-native-stock-matrix-v1'
    def save():atomic_json(output,result)
    try:
        reader=matrix.native.physical.persistence.bind_owner(ROOT,matrix.native.physical.writers.SOURCE);config=reader.native.settings(reader.protocols.V2)
        current,native,aggregates,guards=phase_proofs(config);sources=matrix.native.physical.guarded_sources(reader);guards.update(sources)
        result.update(complete_phase_aggregation=aggregates,guarded_sources_sha256=sources,direct_comparison_phases={});save()
        ids=set()
        for mode,phase in sorted(PAIRS):
            label=mode+'-'+phase;base=ROOT/'out/current-matrix-pair-inputs'/label;api=load(base/'api.json');pair_api(api,head,int(os.environ['GITHUB_RUN_ID']),mode,phase)
            a=api['artifact'];archive=base/'producer.zip';payload=ROOT/'out/current-matrix-pair-payload'/label
            require(a['id'] not in ids and archive.stat().st_size==a['size_in_bytes'] and 'sha256:'+sha(archive)==a['digest'],'Unique exact pair archive required');ids.add(a['id'])
            payload.parent.mkdir(parents=True,exist_ok=True)
            with matrix.native.zipfile.ZipFile(archive) as zipped:
                require(matrix.native.shutil.disk_usage(payload.parent).free>=sum(m.file_size for m in zipped.infolist())+8*1024**3,'Preserve unchanged capacity reserve')
            matrix.native.unpack(archive,payload);members=matrix.native.physical.original.legacy.inspect_archive(archive,payload,a['digest'][7:],a['size_in_bytes'])
            path=payload/'current-native-matrix-results'/(label+'.json');report=load(path);pair_scope(report,mode,phase,head,aggregates,config)
            matrix.source_proof(report,head)
            guards.update({str(base/'api.json'):sha(base/'api.json'),str(archive):sha(archive),**{str(payload/n):v for n,v in members.items()}})
            result['direct_comparison_phases'][label]=dict(artifact_id=a['id'],archive_sha256=a['digest'],report_sha256=sha(path),actual_current_native_pairs=152,actual_current_build_pairs=76);save()
        require(len(ids)==4 and all(sha(p)==v for p,v in guards.items()),'Every phase/pair ZIP and decoded member must remain unchanged')
        result.update(status='passed-complete-current-original-native-stock-physical-and-direct-current-build-subset-only',
            actual_current_processes=608,actual_native_processes=608,actual_direct_original_current_pairs=608,
            actual_direct_original_native_pairs=608,actual_current_native_pairs=608,actual_current_build_pairs=304,guarded_inputs_sha256=guards)
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:save()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',action='store_true');p.add_argument('--check-readiness',action='store_true');p.add_argument('--final',action='store_true')
    p.add_argument('--math-profile',choices=('automatic','sse2'));p.add_argument('--phase',choices=('stock','reload'));a=p.parse_args()
    if a.plan:print(json.dumps(plan()));return
    if a.check_readiness:
        context();records=load(ROOT/'out/current-matrix-readiness.json');require(len(records)==8,'All eight actual current phase API artifacts required')
        for r in records:matrix.api_identity(r['api'],tuple(r['cell']))
        require({tuple(r['cell']) for r in records}==set(matrix.JOBS),'Complete actual current physical readiness required')
        old=load(ROOT/'out/native-matrix-readiness.json');require(len(old)==8,'All eight actual native physical phase API artifacts required')
        for r in old:matrix.native.api_identity(r['api'],r['profile'],r['phase'])
        require({(r['profile'],r['phase']) for r in old}==set(matrix.native.JOBS),'Complete actual native physical readiness required')
        print('All sixteen exact current/original/native physical phase APIs ready; no qualification granted');return
    if a.final:r=final_matrix(ROOT/'out/current-native-matrix-results/current-native-matrix.json')
    else:r=direct_pairs(a.math_profile,a.phase,ROOT/'out/current-native-matrix-results'/(str(a.math_profile)+'-'+str(a.phase)+'.json'))
    print(json.dumps({k:r[k] for k in ('status','phase6_complete','native_admission_qualified')}))


if __name__=='__main__':main()
