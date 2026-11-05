#!/usr/bin/env python3
"""Seal four complete local VM exports into retained ZIPs; never upload evidence."""
import argparse
import datetime
import json
from pathlib import Path, PureWindowsPath
import re
import shutil
import zipfile

import local_transport as local
import transport
from observations import require,sha


def guest_share(share,path):
    path=local.windows_path(path)
    require(path.drive.casefold()=='o:','Recorded local evidence must come from the dedicated O: project share')
    return share.joinpath(*path.relative_to(PureWindowsPath('O:/')).parts)


def copy_file(source,target):
    require(source.is_file() and not source.is_symlink(),'Actual retained regular local input required: '+str(source))
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    require(sha(source)==sha(target),'Copied local evidence bytes differ')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vm-output',required=True,type=lambda v:Path(v).resolve())
    p.add_argument('--runner-commit',required=True,help='Immutable commit containing the exact LocalVM runner source')
    p.add_argument('--output',required=True,type=lambda v:Path(v).resolve())
    p.add_argument('--profile-entry',action='append',help='All four unique PROFILE=local-job-name entries; defaults to full38-local-PROFILE-v1')
    a=p.parse_args();require(not a.output.exists(),'Fresh local collection output required; replacement forbidden')
    entries={profile:'full38-local-'+profile+'-v1' for profile in transport.PROFILES}
    if a.profile_entry:
        entries={}
        for item in a.profile_entry:
            profile,separator,name=item.partition('=')
            require(separator and profile in transport.PROFILES and profile not in entries and
                    re.fullmatch('[A-Za-z0-9-]+',name),'Unique actual PROFILE=local-job-name entries required')
            entries[profile]=name
        require(set(entries)==transport.PROFILES,'All four complete local profiles required')
    share=a.vm_output/'share';plans={}
    # Preflight every closed profile before creating any collection output.
    for profile,name in entries.items():
        statuses=sorted(share.glob(name+'-status-*.json'))
        require(statuses,'Completed local profile receipt missing: '+profile)
        worker=local.load(statuses[-1]);finished=local.load(share/(name+'-bootstrap-result.json'))
        require(worker['status']=='completed-local-Windows-all38-stock-and-exact-save-reload-candidate' and
                finished['status']=='private-runtime-worker-finished' and finished['actual_worker_exitcode']==0 and
                finished['private_desktop_closed'] is True,'Complete normal local full38 profile required: '+profile)
        cfg=local.load(share/(name+'-request.json'));require(cfg['name']==name and
            cfg['configuration']+'-'+cfg['math_profile']==profile,'Actual local profile request differs')
        exports=guest_share(share,cfg['export']);require(exports.is_dir(),'Closed local worker export missing')
        expected={str(transport.safe(str(PureWindowsPath(n)).replace('\\','/'))):v for n,v in worker['export_files_sha256'].items()}
        require({q.relative_to(exports).as_posix():sha(q) for q in exports.rglob('*') if q.is_file()}==expected,
                'Whole actual closed local worker export differs')
        plans[profile]=(name,cfg,statuses[-1],exports)
    producers={cfg['source_commit'] for _,cfg,_,_ in plans.values()};require(len(producers)==1,'Local profiles have different simulator producers')
    pins=local.source_pins(a.runner_commit)
    preservation=local.load(share/'full38-local-build-preservation-v1.json')
    build_statuses=[p for p in share.glob('full38-local-builds-v1-status-*.json') if sha(p)==preservation['build_job_proof_sha256']]
    require(len(build_statuses)==1,'Exact completed local build status receipt required')
    a.output.mkdir()
    report=dict(status='collecting',protocol=local.PROTOCOL,diagnostic_only=False,source_commit=producers.pop(),
        runner_commit=a.runner_commit,artifacts=[],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        native_admission_qualified=False,phase6_complete=False,storage_policy='Keep evidence local; this command never uploads')
    manifest=a.output/'manifest.json';decoded={}
    try:
        for profile,(name,cfg,status,exports) in sorted(plans.items()):
            target=a.output/'decoded'/profile;target.mkdir(parents=True);decoded[profile]=target
            for source in sorted(exports.rglob('*')):
                if source.is_file():copy_file(source,target/source.relative_to(exports))
            conf=cfg['configuration'];build_info=preservation['configurations'][conf]
            build_source=guest_share(share,build_info['path']);build_target=target/'remaining-stock-repaired-build'
            for n,value in build_info['files_sha256'].items():
                rel=str(transport.safe(n));require(sha(build_source/rel)==value,'Closed preserved local build bytes differ')
                copy_file(build_source/rel,build_target/rel)
            copy_file(exports/'configuration-input-controls.json',build_target/'configuration-input-controls.json')
            metadata=target/'local-vm'
            records=[(share/(name+'-request.json'),'request.json'),(share/(name+'-system-launch.json'),'system-launch.json'),
                (share/(name+'-bootstrap-started.json'),'bootstrap-started.json'),
                (share/(name+'-bootstrap-result.json'),'bootstrap-result.json'),(status,'worker-result.json'),
                (a.vm_output/(name+'-job.json'),'guest-job.json'),(a.vm_output/(name+'-result.json'),'guest-result.json'),
                (a.vm_output/'local-VM-identity-v1.json','vm.json'),
                (share/'full38-local-build-preservation-v1.json','build-preservation.json'),
                (build_statuses[0],'build-status.json')]
            for source,n in records:copy_file(source,metadata/n)
            for n,value in pins.items():
                source=share/'scripts'/n;require(sha(source)==value,'Local executed runner differs from its immutable commit: '+n)
                copy_file(source,metadata/'scripts'/n)
            copy_file(share/'scripts'/('start-'+name+'.py'),metadata/'scripts/start.py')
            archive=a.output/(profile+'.zip')
            with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as stream:
                for source in sorted(target.rglob('*')):
                    if source.is_file():
                        require(not source.is_symlink(),'Local retained evidence may not introduce a symlink')
                        stream.write(source,source.relative_to(target).as_posix())
            report['artifacts'].append(dict(profile=profile,path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive)))
            manifest.write_text(json.dumps(report,indent=2)+'\n')
        candidate=dict(report,status='passed')
        verified=local.inspect_matrix(candidate,a.output,decoded,report['source_commit'])
        require(sum(v['actual_processes'] for v in verified.values())==608,'All608 actual local Windows processes required')
        report.update(status='passed',actual_windows_processes=608,actual_windows_presentations=583680,
            collection_verified_against_all_archive_members=True,full_runtime_comparison_pending=True)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:manifest.write_text(json.dumps(report,indent=2)+'\n')
    print('Retained and verified all four complete local Windows VM archives; no evidence uploaded',flush=True)


if __name__=='__main__':main()
