"""Compose a complete current/original phase after independent hosted input restoration.

The enclosing hosted job must first independently restore the fresh BA38/a13
reference and inspect the sealed C08 SDK/observer, and bind the API-verified scalar
SSIM controls. This component rechecks the actual archives and every decoded byte;
it leaves direct build pairs, native comparisons and matrix acceptance pending.
"""
import json
import os
from pathlib import Path
import sys

from inspect_source_complete_phase import inspect as inspect_closed_phase,api_identity,APPLICATION
import physical_observations as physical

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,load,atomic_json
import source_complete_original_transport as original_transport


def complete_cases(bound,config):
    """A phase-level audit always consumes all 38 cases and both actual repeats."""
    cfg=bound['request'];worker=bound['worker'];mode=cfg['math_profile'];phase=cfg['phase']
    ids=[case['id'] for case in config['cases']]
    require(bound['status']=='bound-source-complete-current-API-source-process-and-raw-export-receipts-only' and
            len(ids)==len(set(ids))==38 and config['frames']==960 and
            cfg['capture_scope']==dict(kind='complete',gate='remaining-stock',cases=ids) and
            worker['cases_requested']==ids and worker['repeats']==2 and worker['frames']==960 and
            worker['actual_processes']==76 and worker['successful_presents']==76*960 and
            set(worker['cases'])=={mode+'-'+phase+'-'+identity for identity in ids} and
            all(len(item['runs'])==2 for item in worker['cases'].values()),
            'Complete original current phase coverage required before physical audit')
    return list(config['cases'])


def bind_original(payload,decoded,archive,profile):
    """Bind the independently restored original bytes to this cell's unchanged raw receipts."""
    manifest=load(payload/'original-stock-audit/transport/download.json')
    run=original_transport.run_identity(manifest['workflow_run'])
    require(manifest['status']=='passed' and manifest['protocol']==original_transport.PROTOCOL and
            manifest['diagnostic_only'] is False and manifest['phase6_complete'] is False and
            manifest['native_admission_qualified'] is False and len(manifest['artifacts'])==4 and
            {item['profile'] for item in manifest['artifacts']}==original_transport.legacy.PROFILES and
            manifest['source_commit']==original_transport.SOURCE and
            run['head_sha']==original_transport.SOURCE,'Exact source-complete original reference required')
    matches=[item for item in manifest['artifacts'] if item['profile']==profile]
    require(len(matches)==1,'Exactly one independently audited original profile binding required')
    item=matches[0];identity=original_transport.legacy.artifact_identity(item['api_artifact'],run,False)
    require(all(item[key]==value for key,value in identity.items()),'Captured original API artifact identity differs')
    restored=load(payload/'reference-audit-restoration/restoration.json')
    binding=restored['original_api_archive_bindings'][profile]
    expected=dict(archive=binding['archive'],archive_sha256=item['sha256'],archive_bytes=item['bytes'],
        decoded_members_sha256=item['decoded_members_sha256'],transport_protocol=original_transport.PROTOCOL,
        original_stock_job_id=next(j['id'] for j in run['stock_jobs']
            if j['name']==original_transport.JOB_PREFIX+profile.replace('-',' ')))
    require(binding==expected,'Original restoration is not bound to the same exact source/API archive')
    members=original_transport.legacy.inspect_archive(archive,decoded,item['sha256'],item['bytes'])
    require(members==item['decoded_members_sha256'],'Every actual original decoded member must retain its API identity')
    return expected|dict(archive=str(archive))


def inspected_inputs(inputs):
    """Retain every actual SDK and observer member inspected earlier in this hosted job."""
    require(inputs['status']=='inspected-immutable-Windows-build-and-observer-bytes-only' and
            inputs['compiled_application_source']==inputs['compiled_observer_source']==APPLICATION and
            inputs['Windows_code_executed_by_auditor'] is False and inputs['phase6_complete'] is False and
            inputs['native_admission_qualified'] is False and inputs['tests']['executed_processes']==28,
            'Actual independently inspected complete current SDK/observer required')
    files={str(Path(inputs['runtime_local'])/name):value for name,value in inputs['runtime_files_sha256'].items()}
    files[inputs['observer_local']]=inputs['observer']['sha256']
    require(all(sha(path)==value for path,value in files.items()),'Independently inspected current input bytes changed')
    return files


def inspect(payload,api,archive,cell,inputs,reader,config,original,original_archive,mesa_root,output):
    """Audit 76 real current observations and their direct original pairs; retain partial results."""
    require(os.environ.get('GITHUB_ACTIONS')=='true' and sys.platform=='linux',
            'Complete physical artifact audits stay on standard hosted Linux runners')
    payload=Path(payload);archive=Path(archive);original=Path(original);original_archive=Path(original_archive)
    output=Path(output).resolve()
    protected=[payload,original,Path(inputs['runtime_local']),Path(inputs['observer_local']).parent,Path(mesa_root)]
    require(not output.exists() and all(not output.is_relative_to(path.resolve()) for path in protected),
            'Fresh independent report must be outside every protected input root')
    result=dict(protocol='phase6-independent-source-complete-current-original-physical-phase-v1',status='running',
        configuration=cell[0],math_profile=cell[1],phase=cell[2],profiles_required=4,matrix_cells_required=8,
        cases={},actual_current_processes=0,actual_original_comparisons=0,compiled_application_source=APPLICATION,
        compiled_observer_source=APPLICATION,collector_source='46168cd076a07fda53599c1de8bbc6200852322b',
        complete_eight_cell_matrix_pending=True,direct_current_build_pairs_pending=True,
        native_comparisons_pending=True,serialization_roundtrips_pending=True,
        hardware_and_hands_on_pending=True,phase6_complete=False,native_admission_qualified=False)
    def save():atomic_json(output,result)
    save()
    try:
        api_identity(api,cell)
        require(config==reader.native.settings(reader.protocols.V2),'Every unchanged full-scene clock/physics/image budget required')
        current_members=original_transport.legacy.inspect_archive(archive,payload,api['artifact']['digest'][7:],api['artifact']['size_in_bytes'])
        bound=inspect_closed_phase(payload,api,cell,inputs,config);cases=complete_cases(bound,config)
        cfg=bound['request'];worker=bound['worker'];profile=cell[0]+'-'+cell[1]
        original_binding=bind_original(payload,original,original_archive,profile)
        current_inputs=inspected_inputs(inputs)
        mesa,imports=reader.original_audit.independent_mesa(Path(mesa_root),original_transport.SOURCE)
        source_guards=reader.original_audit.verifier_inputs()|{
            name:sha(ROOT/name) for name in ('Tests/Production/CurrentWindows/Hosted/audit_source_complete_phase.py',
                'Tests/Production/CurrentWindows/Hosted/physical_observations.py','Tests/Production/CurrentWindows/stock.py')}
        result.update(actual_job_id=bound['job_id'],actual_captured_current_processes=bound['actual_processes'],
            current_api_archive_sha256=api['artifact']['digest'],
            current_api_archive_bytes=api['artifact']['size_in_bytes'],original_binding=original_binding,
            guarded_sources_sha256=source_guards,unchanged_budgets=config['budgets'],
            unchanged_image_ssim_minimum=config['image_ssim_minimum'])
        export=Path(bound['export']);mode=cfg['math_profile'];phase=cfg['phase']
        reference=original/('remaining-stock-repaired' if phase=='stock' else 'remaining-stock-persistence')
        for case in cases:
            recorded=worker['cases'][mode+'-'+phase+'-'+case['id']];runs=[];folders=[]
            for repeat,record in enumerate(recorded['runs'],1):
                name=case['id']+'-'+str(repeat);folder=export/(mode+'-'+phase)/name;folders.append(folder)
                result.update(active_case=case['id'],active_repeat=repeat);save()
                observation=physical.inspect_run_record(folder,case,repeat,record,cfg,inputs,config,reader,mesa,imports,
                    original/'remaining-stock-repaired',original_binding['decoded_members_sha256'])
                require(observation['actual_simulation_data']==worker['actual_simulation_data'],
                        'Every actual current staged data witness must equal the complete original locks')
                run=dict(actual_observation=observation,direct_original_current=None);runs.append(run)
                result['actual_current_processes']+=1
                result['cases'][case['id']]=dict(runs=runs);save()
                run['direct_original_current']=physical.compare_windows_pair(reference/name,folder,reader,config)
                result['actual_original_comparisons']+=1;save()
            result['cases'][case['id']]['repeat']=physical.inspect_repeat(folders[0],folders[1],recorded,reader,config);save()
        require(len(result['cases'])==38 and result['actual_current_processes']==result['actual_original_comparisons']==76,
                'Every original current process and direct original comparison required')
        require(original_transport.legacy.inspect_archive(archive,payload,api['artifact']['digest'][7:],api['artifact']['size_in_bytes'])==current_members and
                bind_original(payload,original,original_archive,profile)==original_binding and
                inspected_inputs(inputs)==current_inputs and reader.original_audit.verifier_inputs()|{
                    name:sha(ROOT/name) for name in ('Tests/Production/CurrentWindows/Hosted/audit_source_complete_phase.py',
                    'Tests/Production/CurrentWindows/Hosted/physical_observations.py','Tests/Production/CurrentWindows/stock.py')}==source_guards and
                reader.original_audit.independent_mesa(Path(mesa_root),original_transport.SOURCE)==(mesa,imports),
                'Current/original raw archives, every decoded member, SDK/observer, Mesa or owning reader changed during audit')
        result.update(status='passed-current-original-physical-phase-only',guarded_current_input_files_sha256=current_inputs,
            current_decoded_members_sha256=current_members,successful_current_presentations=76*960)
    except BaseException as error:
        result.update(status='failed',error=str(error));raise
    finally:save()
    return result
