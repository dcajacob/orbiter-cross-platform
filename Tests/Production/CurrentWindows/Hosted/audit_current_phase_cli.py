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
from inspect_source_complete_phase import api_identity
from audit_source_complete_phase import inspect
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
    restored=load(ROOT/'out/reference-audit-restoration/restoration.json')
    require(restored['protocol']=='phase6-source-complete-original-reference-restoration-v2' and
            restored['status']=='restored-exact-independently-audited-original-cohort-only' and
            restored['restorer_source']==head and restored['original_windows_processes']==608 and
            restored['original_saves_relabelled'] is False and restored['current_or_native_qualification_granted'] is False and
            restored['phase6_complete'] is False and restored['native_admission_qualified'] is False,
            'Actual same-auditor complete independent original restoration required')
    captured=load(payload/'reference-audit-restoration/restoration.json')
    for key in ('original_capture_source','original_auditor_source','original_audit_run_id','original_audit_artifact_id',
                'original_audit_archive_sha256','original_transport_sha256','original_writer_audit_sha256','original_cohort_audit_sha256'):
        require(captured[key]==restored[key],'Current and independently restored full original reference differ: '+key)
    original=ROOT/'out/original-stock-audit/transport'/profile
    archive=Path(restored['original_api_archive_bindings'][profile]['archive'])
    guarded={str(path):sha(path) for path in (a.api,a.input_inspection,a.ssim_api,
        ROOT/'out/reference-audit-restoration/restoration.json')}
    try:
        result=inspect(payload,current,a.archive,cell,inputs,reader,config,original,archive,a.mesa,a.output)
        require(result['status']=='passed-current-original-physical-phase-only','Complete actual physical phase audit required')
        require(scalar_binding(a.ssim_api,a.ssim_archive,reader,head,reference)==binding and
                all(sha(path)==value for path,value in guarded.items()),
                'Proven scalar archive/executable/controls, API or independent input receipts changed during audit')
        result.update(auditor_source=head,actual_scalar_binding=binding,guarded_independent_receipts_sha256=guarded,
            original_independent_restoration_sha256=guarded[str(ROOT/'out/reference-audit-restoration/restoration.json')],
            independent_current_input_inspection_sha256=guarded[str(a.input_inspection)])
        atomic_json(a.output,result)
    except BaseException as error:
        if a.output.is_file():
            result=load(a.output);result.update(status='failed',wrapper_error=str(error));atomic_json(a.output,result)
        raise
    print(json.dumps({key:result[key] for key in ('status','configuration','math_profile','phase','actual_current_processes','actual_original_comparisons')}))


if __name__=='__main__':main()
