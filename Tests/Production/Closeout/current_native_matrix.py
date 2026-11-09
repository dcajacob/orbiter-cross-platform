"""Independent current/original physical proof closure; never infer current/native transitively."""
import hashlib
import math
from pathlib import Path
import subprocess
import native_original_matrix as native
from contracts import ROOT,require,sha,load
from audit_current_shader_phase_cli import decode_current
import physical_observations as observations
import inspect_source_complete_shader_phase as capture

SOURCE='dbf5a3c1d78a691af9714ce3b5e4d4312045759f'
RUN=42675771025
JOBS={
 ('Debug','automatic','stock'):129356844398,('Debug','automatic','reload'):129356844776,
 ('Debug','sse2','stock'):129356844514,('Debug','sse2','reload'):129356844505,
 ('Release','automatic','stock'):129356844519,('Release','automatic','reload'):129356844533,
 ('Release','sse2','stock'):129356844436,('Release','sse2','reload'):129356844507}
READINESS=129356593703
STEPS=(
 'Retain the immutable current application source owner',
 'Retain exact actual API ZIPs and source identities without executing Windows code',
 'Retain both real original audit attempts and all four exact source cohort archives',
 'Independently restore every exact original member and both actual audit attempts',
 'Independently inspect all original current SDK observer source and test receipts',
 'Restore only the exact independently proven scalar SSIM controls',
 'Stage exact independent Windows Mesa DLLs and notices for byte inspection',
 'Independently audit all 76 actual current processes direct original pairs and complete repeats',
 'Run actions/upload-artifact@v7')
READY_STEPS=('Verify every original and added helper control','Require the actual positive full retry reference restoration',
 'Retain every actual current capture job and artifact API identity',
 'Independently require all nine successful jobs and all eight exact current API cells','Run actions/upload-artifact@v7')
PHASES={'stock':'stock-writer','reload':'windows-save-reload'}


def api_identity(record,cell):
    require(cell in JOBS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact current physical cell/repository required')
    run=record['run'];jobs=record['jobs'];artifact=record['artifact']
    require(run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1 and
        run['head_branch']=='qualification/current-shader-physical-audit-v1' and run['path']=='.github/workflows/phase6-current-shader-physical-audit.yml' and
        run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False and
        run['status']=='completed' and run['conclusion']=='success','All eight exact current physical phases must finish successfully')
    names={ident:'Independently audit current original '+' '.join(key) for key,ident in JOBS.items()};names[READINESS]='readiness'
    require(len(jobs)==9 and {j['id']:j['name'] for j in jobs}==names and all(j['run_id']==RUN and j['head_sha']==SOURCE and
        j['run_attempt']==1 and j['status']=='completed' and j['conclusion']=='success' and 'ubuntu-24.04' in j['labels'] and
        'self-hosted' not in j['labels'] for j in jobs),'Every exact successful standard-hosted physical job required')
    for job in jobs:
        for name in (READY_STEPS if job['id']==READINESS else STEPS):
            matches=[s for s in job['steps'] if s['name']==name]
            require(len(matches)==1 and matches[0]['status']=='completed' and matches[0]['conclusion']=='success','Actual completed physical step required: '+name)
    require(type(artifact['id']) is int and artifact['id']>0 and artifact['name']=='shader-current-original-physical-'+'-'.join(cell) and
        artifact['expired'] is False and type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<4*1024**3 and
        native.re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and artifact['workflow_run']['id']==RUN and
        artifact['workflow_run']['head_sha']==SOURCE,'Exact successful current physical API artifact required')


def phase_scope(report,cell,config):
    ids={c['id'] for c in config['cases']}
    require(cell in JOBS and len(ids)==38 and config['frames']==960 and
        report['protocol']=='phase6-independent-shader-current-original-physical-phase-v2' and
        report['status']=='passed-current-original-physical-phase-only' and
        (report['configuration'],report['math_profile'],report['phase'])==cell and report['auditor_source']==SOURCE and
        report['compiled_application_source']==report['compiled_observer_source']==capture.APPLICATION and report['collector_source']==capture.CAPTURE and
        report['profiles_required']==4 and report['matrix_cells_required']==8 and
        report['actual_current_processes']==report['actual_captured_current_processes']==report['actual_original_comparisons']==76 and
        report['successful_current_presentations']==76*960 and report['unchanged_budgets']==config['budgets'] and
        report['unchanged_image_ssim_minimum']==config['image_ssim_minimum'],'Complete exact-source current physical scope and unchanged budgets required')
    require(all(report[k] is True for k in ('complete_eight_cell_matrix_pending','direct_current_build_pairs_pending',
        'native_comparisons_pending','serialization_roundtrips_pending','hardware_and_hands_on_pending')) and
        all(report[k] is False for k in ('phase6_complete','native_admission_qualified')),'Phase reports must retain all unfinished acceptance gates')
    require(report['actual_job_id']>0 and report['current_decoded_members_sha256'] and report['guarded_current_input_files_sha256'] and
        report['guarded_sources_sha256'] and report['guarded_independent_receipts_sha256'] and report['actual_scalar_binding'] and
        report['independent_original_retry_proof'] and report['original_retry_reference_comparison']['API_attempts_normalized'] is False and
        report['original_retry_reference_comparison']['old_failed_attempt_relabelled'] is False and
        set(report['cases'])==ids and all(len(c['runs'])==2 and c['repeat']['raw_trace_bytes_identical'] is True and
            c['repeat']['complete_saved_content_identical'] is True and math.isfinite(c['repeat']['ssim']) and
            c['repeat']['ssim']>=config['image_ssim_minimum'] for c in report['cases'].values()),'Every current observation, exact retry lineage and complete repeat required')
    for case in report['cases'].values():
        for run in case['runs']:
            pair=run['direct_original_current'];actual=run['actual_observation']
            require(all(k in actual for k in ('observation','complete_saved_state','actual_class_inputs','actual_simulation_data','system_modules')) and
                pair['complete_saved_content_identical'] is True and pair['actual_clocks_identical_lf'] is True and
                type(pair['ssim']) in (int,float) and math.isfinite(pair['ssim']) and pair['ssim']>=config['image_ssim_minimum'] and
                all(k in pair for k in ('state','camera','detail_calibration_only')),'Every independently observed direct original/current result required')
    return 76


def inspect_phase(record,archive,payload,cell,config):
    api_identity(record,cell);artifact=record['artifact'];archive=Path(archive);payload=Path(payload)
    require(not payload.exists() and archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],
        'Fresh exact API-bound current physical archive required')
    payload.parent.mkdir(parents=True,exist_ok=True)
    with native.zipfile.ZipFile(archive) as zipped:
        require(native.shutil.disk_usage(payload.parent).free>=sum(m.file_size for m in zipped.infolist())+8*1024**3,'Keep the unchanged eight-GiB reserve')
    native.unpack(archive,payload);members=native.physical.original.legacy.inspect_archive(archive,payload,artifact['digest'][7:],artifact['size_in_bytes'])
    path=payload/'current-physical-audits'/('-'.join(cell)+'.json');report=load(path);phase_scope(report,cell,config)
    original=load(payload/'reference-audit-restoration/restoration.json')
    require(sha(payload/'reference-audit-restoration/restoration.json')==report['original_independent_restoration_sha256'] and
        original['original_capture_source']==native.physical.original.SOURCE and
        report['original_binding']['archive_sha256']==original['original_api_archive_bindings'][cell[0]+'-'+cell[1]]['archive_sha256'],
        'Current phase must bind the independently restored original cohort bytes')
    captured=load(payload/'current-physical-download/current/api.json');captured_job=capture.api_identity(captured,cell)
    require(captured_job['id']==report['actual_job_id'] and captured['artifact']['digest']==report['current_api_archive_sha256'] and captured['artifact']['size_in_bytes']==report['current_api_archive_bytes'],
        'Physical report must bind its exact actual current API archive')
    require(native.physical.original.legacy.inspect_archive(archive,payload,artifact['digest'][7:],artifact['size_in_bytes'])==members,
        'Current physical archive or any member changed during inspection')
    return dict(cell=list(cell),api_artifact_id=artifact['id'],api_archive_sha256=artifact['digest'],physical_source=SOURCE,
        physical_report_sha256=sha(path),decoded_members_sha256=members,report=report,qualification_granted=False)


def source_proof(report,source):
    """Re-read each named source from its actual immutable owner, without editing reports."""
    for path,value in report['guarded_sources_sha256'].items():
        p=Path(path)
        relative=p.relative_to(ROOT).as_posix() if p.is_absolute() else p.as_posix()
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'Canonical guarded source path required')
        data=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+relative])
        require(hashlib.sha256(data).hexdigest()==value,'Physical report source differs from its immutable owner: '+relative)


def aggregate(proofs,config):
    require(len(proofs)==8 and {tuple(p['cell']) for p in proofs}==set(JOBS) and
        len({p['api_artifact_id'] for p in proofs})==8,'All eight unique current physical phase artifacts required')
    for proof in proofs:
        require(proof['physical_source']==SOURCE and proof['decoded_members_sha256'] and proof['qualification_granted'] is False,'Independently decoded current phase proof required')
        phase_scope(proof['report'],tuple(proof['cell']),config)
    return dict(status='passed-eight-current-original-physical-phases-only',physical_source=SOURCE,physical_run_id=RUN,
        actual_current_processes=608,actual_direct_original_current_pairs=608,
        phase_artifacts={'-'.join(p['cell']):dict(artifact_id=p['api_artifact_id'],archive_sha256=p['api_archive_sha256'],
            report_sha256=p['physical_report_sha256']) for p in proofs},qualification_granted=False,phase6_complete=False)


def bind_raw(cell,proof,payload=None,decode=True):
    base=ROOT/'out/current-matrix-current-inputs'/('-'.join(cell));api_file=base/'api.json';archive=base/'producer.zip';api=load(api_file)
    capture.api_identity(api,cell);payload=Path(payload) if payload else ROOT/'out/current-matrix-current-payload'/('-'.join(cell))
    if decode:decode_current(api,archive,payload,cell)
    report=proof['report'];members=native.physical.original.legacy.inspect_archive(archive,payload,api['artifact']['digest'][7:],api['artifact']['size_in_bytes'])
    require(members==report['current_decoded_members_sha256'] and api['artifact']['digest']==report['current_api_archive_sha256'] and
        api['artifact']['size_in_bytes']==report['current_api_archive_bytes'],'Every actual current raw member must equal the independent physical proof')
    export=payload/'current-stock-exports'/('-'.join(cell));share=payload/'current-stock-requests'/('-'.join(cell))
    request=load(share/'request.json');worker=load(share/'worker-result.json')
    require((request['configuration'],request['math_profile'],request['phase'])==cell and request['source_commit']==capture.APPLICATION and
        worker['actual_processes']==76 and worker['successful_presents']==76*960 and
        set(worker['cases'])=={cell[1]+'-'+cell[2]+'-'+k for k in report['cases']},'Exact complete raw current profile required')
    return export/(cell[1]+'-'+cell[2]),dict(api_sha256=sha(api_file),archive_sha256=sha(archive),payload=str(payload),
        decoded_members_sha256=members),request,worker
