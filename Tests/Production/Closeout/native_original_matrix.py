"""Close all eight immutable physical phase reports; retain direct build and other gates.

This component verifies the raw API report ZIPs on hosted runners. It does not
substitute report aggregation for direct comparisons of the captured build pairs.
"""
import math
from pathlib import Path
import re
import shutil
import zipfile
from contracts import ROOT,PROFILES,PHASES,require,sha,load
import audit_native_original_phase as physical
from restore_sdk import unpack

SOURCE='6ca9af318e625e263deed144e62525e3632fb9ee'
RUN=42625357330
JOBS={
 ('Debug-automatic','stock-writer'):129187890123,('Debug-automatic','windows-save-reload'):129187890201,
 ('Debug-sse2','stock-writer'):129187889994,('Debug-sse2','windows-save-reload'):129187890066,
 ('Release-automatic','stock-writer'):129187890028,('Release-automatic','windows-save-reload'):129187890040,
 ('Release-sse2','stock-writer'):129187890338,('Release-sse2','windows-save-reload'):129187890109}
STEPS=(
 'Download only exact native phase runtime provider Mesa and scalar source artifacts',
 'Restore exact compiled CCC bytes with all original unit and discovery evidence',
 'Restore exact separately owned base providers and all controls',
 'Restore exact separately owned Mesa cleanup and every positive and negative control',
 'Retain every original cohort archive and both real audit attempts on GitHub only',
 'Independently restore every original source member with the exact retained retry lineage',
 'Stage exact untouched original Windows application SDK and assets without execution',
 'Restore only the independently proven exact scalar implementation and its unchanged controls',
 'Stage exact independent original Windows renderer DLLs and notices for byte inspection',
 'Independently inspect all real observations and directly compare all76 pairs in matching userspace',
 'Run actions/upload-artifact@v7')


def api_identity(record,profile,phase):
    require((profile,phase) in JOBS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),
        'Exact native physical matrix profile/phase/repository required')
    run=record['run'];jobs=record['jobs'];artifact=record['artifact']
    require(run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1 and
        run['head_branch']=='qualification/native-original-physical-audit-v1' and
        run['path']=='.github/workflows/phase6-native-original-physical-audit.yml' and
        run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False and
        run['status']=='completed' and run['conclusion']=='success','All eight immutable physical phase jobs must finish successfully')
    expected={job_id:'Independently compare original native '+p+' '+q for (p,q),job_id in JOBS.items()}
    expected[129187580614]='readiness'
    require(len(jobs)==9 and {j['id']:j['name'] for j in jobs}==expected and
        all(j['run_id']==RUN and j['head_sha']==SOURCE and j['run_attempt']==1 and
            j['status']=='completed' and j['conclusion']=='success' and 'ubuntu-24.04' in j['labels'] and
            'self-hosted' not in j['labels'] for j in jobs),'Exact complete standard-hosted nine-job physical producer required')
    for job in jobs:
        required=('Preserve every original and added small helper control',
            'Require actual full original retry restoration and complete native retained-byte proofs','Run actions/upload-artifact@v7') if job['name']=='readiness' else STEPS
        for name in required:
            steps=[s for s in job['steps'] if s['name']==name]
            require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success',
                'Actual complete physical producer step required: '+name)
    require(type(artifact['id']) is int and artifact['id']>0 and artifact['expired'] is False and
        artifact['name']=='native-original-physical-'+profile+'-'+phase and
        type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<4*1024**3 and
        re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and
        artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE,
        'Unique exact successful physical phase API artifact required')


def phase_scope(report,profile,phase,config):
    ids={case['id'] for case in config['cases']};native=report['independent_native_observations'];original=report['independent_original_observations']
    producer=physical.writers.SOURCE if phase=='stock-writer' else physical.reloads.SOURCE
    require((profile,phase) in JOBS and len(ids)==38 and config['frames']==960 and
        report['protocol']=='phase6-independent-native-original-complete-physical-phase-v1' and
        report['status']=='passed-one-complete-native-original-physical-phase-only' and
        report['profile']==profile and report['phase']==phase and report['auditor_source']==SOURCE and
        report['native_source']==producer and report['compiled_runtime_source']==physical.writers.RUNTIME and
        report['required_profiles']==4 and report['required_phases']==2 and report['required_cases']==38 and
        report['required_repeats']==2 and report['required_frames']==960 and
        report['actual_native_processes']==report['actual_direct_original_native_pairs']==76 and
        report['successful_native_presentations']==76*960 and report['unchanged_budgets']==config['budgets'] and
        report['unchanged_image_ssim_minimum']==config['image_ssim_minimum'],
        'Complete exact-source physical phase scope and unchanged comparison budgets required')
    require(all(report[name] is False for name in ('qualification_granted','phase6_complete','native_admission_qualified')) and
        all(report[name] is True for name in ('complete_four_profile_two_phase_matrix_pending',
            'direct_native_and_original_build_pairs_pending','current_native_comparisons_pending',
            'other_class_lifetime_full157_and_hardware_gates_pending')),
        'A phase report must preserve every uncompleted matrix/build/current/hardware acceptance gate')
    require(native['status']=='audited-native-phase-only' and native['profile']==profile and native['phase']==phase and
        native['source_producer']==producer and native['runtime_source']==physical.writers.RUNTIME and native['runtime_role']=='normal' and
        native['observer_delay_ms']==120 and native['actual_processes']==76 and native['actual_presentations']==76*960 and
        native['owning_bytes_unchanged'] is True and native['diagnostic_only'] is False and
        native['phase6_complete'] is False and native['native_admission_qualified'] is False and
        set(native['cases'])==ids and all(len(c['runs'])==2 for c in native['cases'].values()),
        'Every independently recomputed actual native observation required')
    require(original['producer_commit']==physical.original.SOURCE and
        set(original['stock']['cases'])==set(original['reload']['cases'])==ids and
        original['reload']['actual_processes']==76 and
        all(len(original[part]['cases'][case]['runs'])==2 for part in ('stock','reload') for case in ids),
        'Both original Windows observation phases and repetitions required')
    require(set(report['cases'])==ids and all(len(c['runs'])==2 for c in report['cases'].values()),
        'Every direct original/native case must retain both complete comparisons')
    for case in report['cases'].values():
        for run in case['runs']:
            pair=run['direct_original_native'];value=pair['ssim']
            require(pair['complete_saved_content_identical'] is True and pair['actual_clocks_identical_lf'] is True and
                type(value) in (int,float) and math.isfinite(value) and value>=config['image_ssim_minimum'] and
                all(name in pair for name in ('state','camera','detail_calibration_only')) and
                'actual_field_changes' in run['original_windows_roundtrip'],
                'Actual complete saved content, clocks, full-frame, state/camera/detail and serialization results required')
    require(set(report['original_api_bindings'])==set(PROFILES) and report['guarded_sources_sha256'] and
        report['guarded_runtime_and_preserved_original_inputs_sha256'] and report['native_decoded_tree_sha256'] and
        report['raw_native_proof']['archive_sha256']==report['native_API_archive_sha256'].removeprefix('sha256:'),
        'Original matrix and exact raw native/API/source/runtime guards required')
    return 76


def inspect_phase(record,archive,payload,profile,phase,config):
    """Independently decode every proof ZIP member, keeping the exact source report intact."""
    api_identity(record,profile,phase);artifact=record['artifact'];archive=Path(archive);payload=Path(payload)
    require(not payload.exists() and archive.stat().st_size==artifact['size_in_bytes'] and
        'sha256:'+sha(archive)==artifact['digest'],'Fresh exact API-bound physical report ZIP required')
    payload.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        require(shutil.disk_usage(payload.parent).free>=sum(m.file_size for m in source.infolist())+8*1024**3,
            'Physical matrix decode must preserve the unchanged eight-GiB reserve')
    unpack(archive,payload)
    members=physical.original.legacy.inspect_archive(archive,payload,artifact['digest'][7:],artifact['size_in_bytes'])
    cell=profile+'-'+phase;path=payload/'native-original-physical-audits'/(cell+'.json');report=load(path)
    phase_scope(report,profile,phase,config)
    bootstrap=load(payload/'native-original-bootstrap'/cell/'collection.json')
    require(bootstrap['protocol']=='phase6-hosted-native-original-physical-bootstrap-v1' and
        bootstrap['status']=='audited-one-complete-retained-native-original-physical-phase-only' and
        bootstrap['profile']==profile and bootstrap['collector_source']==SOURCE and
        bootstrap['compiled_runtime_source']==physical.writers.RUNTIME and bootstrap['simulator_executed'] is False and
        bootstrap['actual_native_processes']==bootstrap['actual_direct_original_native_pairs']==76 and
        bootstrap['physical_report_sha256']==sha(path) and bootstrap['phase6_complete'] is False and
        bootstrap['native_admission_qualified'] is False,'Actual completed source-bound no-recapture bootstrap must bind the exact report')
    require(physical.original.legacy.inspect_archive(archive,payload,artifact['digest'][7:],artifact['size_in_bytes'])==members,
        'Physical matrix report archive or any decoded member changed during inspection')
    return dict(protocol='phase6-verified-complete-native-original-physical-phase-artifact-v1',
        profile=profile,phase=phase,api_artifact_id=artifact['id'],api_archive_sha256=artifact['digest'],
        physical_source=SOURCE,physical_report_sha256=sha(path),decoded_members_sha256=members,report=report,
        full_matrix_and_direct_build_gates_pending=True,qualification_granted=False)


def complete_phase_matrix(proofs,config):
    require(type(proofs) is list and len(proofs)==8,'All eight independent physical phase proofs required')
    keys=set();artifact_ids=set();counts=0
    for proof in proofs:
        key=(proof['profile'],proof['phase'])
        require(key in JOBS and key not in keys and proof['api_artifact_id'] not in artifact_ids and
            proof['protocol']=='phase6-verified-complete-native-original-physical-phase-artifact-v1' and
            proof['physical_source']==SOURCE and proof['decoded_members_sha256'] and
            proof['full_matrix_and_direct_build_gates_pending'] is True and proof['qualification_granted'] is False,
            'Unique independently API/member-verified physical source proofs required')
        keys.add(key);artifact_ids.add(proof['api_artifact_id']);counts+=phase_scope(proof['report'],*key,config)
    require(keys==set(JOBS) and counts==608,'Complete four-profile two-phase 608-comparison closure required')
    return dict(protocol='phase6-complete-native-original-physical-phase-aggregation-v1',
        status='passed-eight-complete-native-original-physical-phase-aggregation-only',physical_source=SOURCE,
        physical_run_id=RUN,actual_native_processes=608,actual_direct_original_native_pairs=608,
        direct_native_and_original_build_pairs_pending=True,current_native_comparisons_pending=True,
        other_class_lifetime_full157_and_hardware_gates_pending=True,qualification_granted=False,phase6_complete=False,
        phase_artifacts={p['profile']+'/'+p['phase']:dict(artifact_id=p['api_artifact_id'],archive_sha256=p['api_archive_sha256'],
            physical_report_sha256=p['physical_report_sha256']) for p in proofs})


def compare_build_pair(left,right,reader,config):
    """Execute the original direct Debug/Release loop's exact numerical and full-frame comparisons."""
    similarity=reader.windows.image_ssim((Path(left)/'scene.rgba').read_bytes(),(Path(right)/'scene.rgba').read_bytes(),1280,720)
    require(math.isfinite(similarity) and similarity>=config['image_ssim_minimum'],'Direct build full-frame budget failed')
    return dict(state=reader.original_audit.compare_state(left,right,config),camera=reader.original_audit.camera_comparison(left,right,config),
        ssim=similarity,detail_calibration_only=reader.original_audit.detail_calibration(left,right))
