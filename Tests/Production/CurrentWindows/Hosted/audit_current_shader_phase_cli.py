#!/usr/bin/env python3
"""Run one complete immutable current/original physical phase on a standard hosted runner."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/Closeout'),
              str(ROOT/'Tests/Production/RemainingStockPersistence')]
from contracts import require,sha,load,atomic_json
from restore_sdk import unpack
from inspect_source_complete_shader_phase import api_identity
from audit_source_complete_shader_phase import inspect
from source_complete_shader_provider import reference_receipts
import retry_reference_proof as retry_proof
import source_complete_original_transport as transport
import restore_hosted_ssim as scalar
from ssim_kernel import bind
from observations import bind_owner


def decode_current(api,archive,target,cell):
    api_identity(api,cell);artifact=api['artifact']
    require(not target.exists() and archive.stat().st_size==artifact['size_in_bytes'] and
            'sha256:'+sha(archive)==artifact['digest'],'Fresh exact current API archive destination required')
    with zipfile.ZipFile(archive) as source:
        require(shutil.disk_usage(target.parent).free>=sum(item.file_size for item in source.infolist())+8*1024**3,
                'Current audit decode must preserve the unchanged capacity reserve')
    unpack(archive,target)
    return transport.legacy.inspect_archive(archive,target,artifact['digest'][7:],artifact['size_in_bytes'])


def scalar_binding(api_path,archive,reader,head,reference=None):
    """Use only the previously independently proven, immutable scalar implementation."""
    api=load(api_path);scalar.validate_api(api)
    base=ROOT/'out/hosted-ssim-restoration';record=load(base/'restoration.json')
    require(record['protocol']=='phase6-hosted-verified-scalar-restoration-v1' and
            record['status']=='restored-verified-scalar-arithmetic-controls-only' and
            record['original_producer_source']==scalar.SOURCE and record['original_run_id']==scalar.RUN and
            record['original_artifact_id']==13639682979 and record['original_api_archive_sha256']==scalar.DIGEST and
            record['restorer_source']==head and record['source_api_sha256']==sha(api_path) and
            record['masks'] is False and record['rescaling'] is False and record['budgets_changed'] is False and
            record['phase6_complete'] is False and record['native_admission_qualified'] is False,
            'Actual same-owner API-verified scalar restoration required')
    members=transport.legacy.inspect_archive(archive,base/'source-artifact',scalar.DIGEST,3935729)
    verification=ROOT/'out/hosted-ssim-controls/verification.json'
    require(sha(verification)==members['hosted-ssim-controls/verification.json'],
            'Scalar verification bytes differ from their exact independently proven API archive')
    fast,binding=bind(verification,sha(verification),reference or reader.windows.image_ssim)
    reader.windows.image_ssim=fast
    return dict(original_source=scalar.SOURCE,original_api_archive_sha256=scalar.DIGEST,
                verification_sha256=sha(verification),binding=binding,source_api_sha256=sha(api_path))


def independent_reference(head):
    """Re-read both real audit attempts and all retained successful/failed source members."""
    names={
        'reference_transport':'original-stock-audit/transport/download.json',
        'reference_audit':'original-stock-audit/independent/writer-audit.json',
        'reference_persistence_audit':'original-stock-audit/independent/original-persistence-audit.json',
        'reference_restoration':'reference-audit-restoration/restoration.json'}
    out=ROOT/'out'
    cfg=dict(roles=dict(runner=dict(commit=head)),reference_retry_inputs=retry_proof.inventory(out),
        **{name:dict(path=str(out/relative),sha256=sha(out/relative)) for name,relative in names.items()})
    proof=reference_receipts(cfg)
    guarded=retry_proof.guarded(cfg)|{value['path']:value['sha256'] for value in (cfg[name] for name in names)}
    return proof,guarded,load(cfg['reference_restoration']['path'])


def compare_reference(captured,restored):
    """Compare stable facts after each side's raw API/ZIP/log proof is independently checked.

    Each independently verified side keeps its own API serialization and exact known
    raw-log transport representation. Neither is replaced with the other's bytes.
    """
    for key in ('original_capture_source','original_auditor_source','original_audit_run_id','original_audit_artifact_id',
                'original_audit_archive_sha256','original_transport_sha256','original_writer_audit_sha256',
                'original_cohort_audit_sha256','successful_audit_decoded_members_sha256'):
        require(captured[key]==restored[key],'Current and independently restored full original reference differ: '+key)
    left=captured['audit_retry_lineage'];right=restored['audit_retry_lineage']
    require(set(left)==set(right),'Current and independently restored retry proof fields differ')
    for key in set(left)-{'first_attempt_api_sha256','first_job_log_transport'}:
        require(left[key]==right[key],'Independently verified original retry identity differs: '+key)
    return dict(captured_audit_retry_lineage=left,independent_audit_retry_lineage=right,
        raw_API_and_log_transport_identities_preserved=True,API_attempts_normalized=False,
        old_failed_attempt_relabelled=False,qualification_granted=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','input-inspection','ssim-api','ssim-archive','mesa','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    p.add_argument('--phase',choices=('stock','reload'),required=True);a=p.parse_args()
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform' and
            os.environ.get('ImageOS')=='ubuntu24','Actual standard hosted Ubuntu24 audit required')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(head==os.environ['GITHUB_SHA'],'Actual independent auditor source owner differs')
    cell=(a.configuration,a.math_profile,a.phase);profile=a.configuration+'-'+a.math_profile
    payload=ROOT/'out/current-physical-source'/('-'.join(cell));payload.parent.mkdir(parents=True,exist_ok=True)
    current=load(a.api);decode_current(current,a.archive,payload,cell)
    inputs=load(a.input_inspection);reader=bind_owner(ROOT,head);config=reader.native.settings(reader.protocols.V2)
    reference=reader.windows.image_ssim
    binding=scalar_binding(a.ssim_api,a.ssim_archive,reader,head,reference)
    reference_proof,reference_guards,restored=independent_reference(head)
    captured=load(payload/'reference-audit-restoration/restoration.json')
    reference_comparison=compare_reference(captured,restored)
    original=ROOT/'out/original-stock-audit/transport'/profile
    archive=Path(restored['original_api_archive_bindings'][profile]['archive'])
    guarded=reference_guards|{str(path):sha(path) for path in (a.api,a.input_inspection,a.ssim_api)}
    try:
        result=inspect(payload,current,a.archive,cell,inputs,reader,config,original,archive,a.mesa,a.output)
        require(result['status']=='passed-current-original-physical-phase-only','Complete actual physical phase audit required')
        require(scalar_binding(a.ssim_api,a.ssim_archive,reader,head,reference)==binding and
                independent_reference(head)==(reference_proof,reference_guards,restored) and
                compare_reference(captured,restored)==reference_comparison and
                all(sha(path)==value for path,value in guarded.items()),
                'Proven scalar archive/executable/controls, API or independent input receipts changed during audit')
        result.update(auditor_source=head,actual_scalar_binding=binding,guarded_independent_receipts_sha256=guarded,
            independent_original_retry_proof=reference_proof,original_retry_reference_comparison=reference_comparison,
            original_independent_restoration_sha256=guarded[str(ROOT/'out/reference-audit-restoration/restoration.json')],
            independent_current_input_inspection_sha256=guarded[str(a.input_inspection)])
        atomic_json(a.output,result)
    except BaseException as error:
        if a.output.is_file():
            result=load(a.output);result.update(status='failed',wrapper_error=str(error));atomic_json(a.output,result)
        raise
    print(json.dumps({key:result[key] for key in ('status','configuration','math_profile','phase','actual_current_processes','actual_original_comparisons')}))


if __name__=='__main__':main()
