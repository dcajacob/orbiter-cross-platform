#!/usr/bin/env python3
"""Exercise real closed VM receipts and reject altered/partial local provenance."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

import local_transport as local
import transport
from observations import require,sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def rejects(name,action,reason,controls):
    try:action()
    except (ValueError,KeyError,TypeError,zipfile.BadZipFile) as error:
        require(reason in str(error),'Wrong local provenance rejection for '+name+': '+str(error))
        controls.append(dict(control=name,reason=str(error)))
    else:raise ValueError('Altered/partial local provenance accepted: '+name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vm-output',required=True,type=lambda v:Path(v).resolve())
    p.add_argument('--output',required=True,type=lambda v:Path(v).resolve())
    a=p.parse_args();require(not a.output.exists(),'Fresh local provenance controls output required')
    source=a.vm_output;share=source/'share';name='docked-local-Debug-sse2-NTFS-v2'
    worker=sorted(share.glob(name+'-status-*.json'))[-1]
    inputs={target:path for path,target in [
        (share/(name+'-request.json'),'request.json'),(share/(name+'-system-launch.json'),'system-launch.json'),
        (share/(name+'-bootstrap-started.json'),'bootstrap-started.json'),
        (share/(name+'-bootstrap-result.json'),'bootstrap-result.json'),(worker,'worker-result.json'),
        (source/(name+'-job.json'),'guest-job.json'),(source/(name+'-result.json'),'guest-result.json'),
        (source/'local-VM-identity-v1.json','vm.json')]}
    protected={str(p):sha(p) for p in inputs.values()};pins={}
    for filename in (*local.RUNNERS,'docked_local_runtime_worker_v3.py'):
        path=share/'scripts'/filename;protected[str(path)]=sha(path);pins[filename]=sha(path)
    entry=share/'scripts'/('start-'+name+'.py');protected[str(entry)]=sha(entry)
    source_files={str(HERE/n):sha(HERE/n) for n in ('local_transport.py','transport.py','LocalTransport.Test.py')}
    report=dict(status='failed',controls=[],protected_input_sha256=protected,source_sha256=source_files,
        native_admission_qualified=False,phase6_complete=False,
        scope='Real closed Debug SSE2 eight-process local docked diagnostic receipt-chain and exact archive byte controls. Parent path fixtures use retained real diagnostic bytes but execute no simulator. This does not qualify any complete full38 profile or local transport matrix.')
    try:
        with tempfile.TemporaryDirectory(prefix='phase6-local-provenance-controls-',dir=ROOT/'out') as temp:
            root=Path(temp);decoded=root/'decoded';metadata=decoded/'local-vm';(metadata/'scripts').mkdir(parents=True)
            for target,path in inputs.items():shutil.copy2(path,metadata/target)
            for filename in pins:shutil.copy2(share/'scripts'/filename,metadata/'scripts'/filename)
            shutil.copy2(entry,metadata/'scripts/start.py')
            cfg,closed,vm=local.receipt_chain(decoded,'Debug-sse2',pins)
            require(closed['actual_processes']==8 and closed['status']=='completed-local-original-docked-physical-clock-diagnostic',
                    'Actual closed original local diagnostic positive changed')
            report['real_receipt_positive']=dict(source=cfg['source_commit'],profile='Debug-sse2',actual_previously_observed_processes=8,
                domain_uuid=vm['domain_uuid'],normal_worker_pid=local.load(metadata/'bootstrap-result.json')['actual_worker_pid'])
            pristine={p:p.read_bytes() for p in metadata.rglob('*') if p.is_file()}
            def restore():
                for p,body in pristine.items():p.write_bytes(body)
            def change(filename,mutate):
                path=metadata/filename;value=local.load(path);mutate(value);dump(path,value)
            def coherent_request(mutate):
                change('request.json',mutate);digest=sha(metadata/'request.json')
                for filename in ('system-launch.json','bootstrap-started.json','bootstrap-result.json','worker-result.json'):
                    change(filename,lambda value:value.update(request_sha256=digest))
                change('guest-result.json',lambda value:value.update(**{'out-data':base64.b64encode(
                    json.dumps(local.load(metadata/'system-launch.json')).encode()).decode()}))
            mutations=[
                ('request_bytes_changed',lambda:(metadata/'request.json').write_bytes(pristine[metadata/'request.json']+b' '),'request binding'),
                ('wrong_profile',lambda:change('request.json',lambda d:d.update(math_profile='automatic')),'request profile'),
                ('worker_failed',lambda:change('bootstrap-result.json',lambda d:d.update(actual_worker_exitcode=1)),'finish normally'),
                ('worker_pid_replaced',lambda:change('bootstrap-started.json',lambda d:d.update(actual_worker_pid=1)),'finish normally'),
                ('boolean_worker_pid',lambda:change('bootstrap-started.json',lambda d:d.update(actual_worker_pid=True)),'finish normally'),
                ('private_desktop_left_open',lambda:change('bootstrap-result.json',lambda d:d.update(private_desktop_closed=False)),'finish normally'),
                ('desktop_switched',lambda:change('bootstrap-started.json',lambda d:d.update(no_desktop_switch=False)),'bootstrap desktop'),
                ('bootstrap_session_zero',lambda:change('bootstrap-started.json',lambda d:d['context'].update(session=0)),'bootstrap desktop'),
                ('worker_session_zero',lambda:change('worker-result.json',lambda d:d['desktop_context'].update(session=0)),'worker context'),
                ('cloud_compute_claim',lambda:change('worker-result.json',lambda d:d.update(cloud_builds_used=True)),'qualification flags'),
                ('premature_admission',lambda:change('worker-result.json',lambda d:d.update(native_admission_qualified=True)),'qualification flags'),
                ('changed_worker_source',lambda:change('worker-result.json',lambda d:d.update(source='0'*40)),'qualification flags'),
                ('changed_worker_profile',lambda:change('worker-result.json',lambda d:d.update(math_profile='automatic')),'qualification flags'),
                ('different_guest_domain',lambda:change('guest-job.json',lambda d:d.update(domain='other')),'VM identity'),
                ('non_Windows_guest',lambda:change('vm.json',lambda d:d.update(guest_os_id='linux')),'VM identity'),
                ('malformed_VM_uuid',lambda:change('vm.json',lambda d:d.update(domain_uuid='wrong')),'VM identity'),
                ('nonterminal_guest_agent',lambda:change('guest-result.json',lambda d:d.update(exited=False)),'terminal guest-agent'),
                ('different_guest_agent_stdout',lambda:change('guest-result.json',lambda d:d.update(**{'out-data':base64.b64encode(b'{}').decode()})),'terminal guest-agent'),
                ('unrecorded_entry_code',lambda:(metadata/'scripts/start.py').write_bytes(b'print("changed")\n'),'entry script'),
                ('changed_runner_body',lambda:(metadata/'scripts/win_local_process_v1.py').write_bytes(b'# changed\n'),'runner bytes'),
                ('coherent_zero_session',lambda:coherent_request(lambda d:d.update(active_session=0)),'Normal local VM session'),
                ('coherent_wrong_worker_hash',lambda:coherent_request(lambda d:d.update(worker_sha256='0'*64)),'trusted source: worker'),
                ('coherent_unbound_script_directory',lambda:coherent_request(lambda d:d.update(worker_script='C:/other/docked_local_runtime_worker_v3.py')),'trusted source: worker'),
                ('coherent_bootstrap_role_substitution',lambda:coherent_request(lambda d:d.update(
                    bootstrap_script='O:/scripts/system_user_launcher_v1.py',bootstrap_sha256=pins['system_user_launcher_v1.py'])),'trusted source: bootstrap'),
                ('coherent_entry_path_injection',lambda:coherent_request(lambda d:d.update(name="bad'name")),'Normal local VM session'),
                ('UNC_guest_entry_path',lambda:change('guest-job.json',lambda d:d.update(guest_script=r'\\server\share\start.py')),'absolute local Windows volume'),
            ]
            for control,mutate,reason in mutations:
                restore();mutate();rejects(control,lambda:local.receipt_chain(decoded,'Debug-sse2',pins),reason,report['controls'])
            restore();local.receipt_chain(decoded,'Debug-sse2',pins)
            rejects('real_diagnostic_as_full38',lambda:local.inspect_profile(decoded,'Debug-sse2',cfg['source_commit'],pins,{}),
                    'Complete local full38 producer/runner',report['controls'])
            profiles=transport.PROFILES
            manifest=dict(status='passed',protocol=local.PROTOCOL,diagnostic_only=False,source_commit=cfg['source_commit'],
                runner_commit='0'*40,native_admission_qualified=False,phase6_complete=False,artifacts=[dict(profile=p,path=p+'.zip',sha256='0'*64,bytes=1) for p in sorted(profiles)])
            for control,mutate in [
                ('missing_profile',lambda d:d['artifacts'].pop()),
                ('duplicate_profile',lambda d:d['artifacts'].__setitem__(1,copy.deepcopy(d['artifacts'][0]))),
                ('diagnostic_transport',lambda d:d.update(diagnostic_only=True)),
                ('unfinished_transport',lambda d:d.update(status='running')),
                ('Github_identity_as_local',lambda d:d.update(workflow_run={'id':1})),
            ]:
                damaged=copy.deepcopy(manifest);mutate(damaged)
                rejects(control,lambda:local.inspect_matrix(damaged,root,{p:decoded for p in profiles},cfg['source_commit']),
                        'Complete four-profile local VM transport',report['controls'])
            archive=root/'real-receipts.zip'
            with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
                for path in sorted(decoded.rglob('*')):
                    if path.is_file():z.write(path,path.relative_to(decoded).as_posix())
            inventory=transport.inspect_archive(archive,decoded,sha(archive),archive.stat().st_size)
            report['real_archive_positive']=dict(bytes=archive.stat().st_size,sha256=sha(archive),members=len(inventory))
            rejects('wrong_local_archive_digest',lambda:transport.inspect_archive(archive,decoded,'0'*64,archive.stat().st_size),
                    'ZIP bytes/hash/size',report['controls'])
            # Exact parent/build suffix mapping over real retained saved/clock bytes;
            # this fixture is intentionally not a complete simulator capture.
            parent=root/'parents';case=parent/'remaining-stock-repaired/remaining_stock_001-1';case.mkdir(parents=True)
            source_run=share/(name+'-evidence/docked_ISS-1-writer')
            (case/'clock.csv').write_bytes((source_run/'pause-clock.csv').read_bytes())
            (case/'Scenarios').mkdir();(case/'Scenarios/(Current state).scn').write_bytes((source_run/'Scenarios/PausedResult.scn').read_bytes())
            case2=case.with_name('remaining_stock_001-2');shutil.copytree(case,case2)
            parent_file=parent/'remaining-stock-repaired/capture.json';dump(parent_file,{'path_fixture_only':True})
            build=parent/'remaining-stock-repaired-build';build.mkdir();dump(build/'build.json',{'path_fixture_only':True})
            records={'cases':{'remaining_stock_001':{'runs':[{'files_sha256':{'clock.csv':sha(case/'clock.csv')}},
                                                          {'files_sha256':{'clock.csv':sha(case2/'clock.csv')}}]}}}
            windows={'remaining-stock-repaired':r'C:\OrbiterPhase6\Runs\Full38-Test\remaining-stock-repaired',
                     'remaining-stock-repaired-build':r'C:\OrbiterPhase6\build\full38-Release-v1'}
            expected={'remaining-stock-repaired/capture.json':sha(parent_file),'remaining-stock-repaired-build/build.json':sha(build/'build.json')}
            for repeat in (1,2):
                folder='remaining-stock-repaired/remaining_stock_001-'+str(repeat)
                for n in ('clock.csv','Scenarios/(Current state).scn'):expected[folder+'/'+n]=sha(parent/folder/n)
            guarded={str(PureWindowsPath(windows[n.split('/')[0]])/PureWindowsPath(n.split('/',1)[1])):v for n,v in expected.items()}
            guard_report={'guarded_parent_files_sha256':guarded}
            require(transport.parent_guards(parent,guard_report,records,windows)==expected,'Explicit actual local build/capture path mapping failed')
            legacy={str(PureWindowsPath('C:/legacy/out')/PureWindowsPath(n)):v for n,v in expected.items()}
            require(transport.parent_guards(parent,{'guarded_parent_files_sha256':legacy},records)==expected,
                    'Existing one-root GitHub artifact parent mapping changed')
            report['parent_path_positive']=dict(files=len(expected),fixture_only=True,actual_source_byte_files=4)
            for control,damaged in [
                ('changed_local_parent_root',dict(windows,**{'remaining-stock-repaired':r'C:\different'})),
                ('ambiguous_nested_local_roots',dict(windows,**{'remaining-stock-repaired-build':windows['remaining-stock-repaired']+'\\build'})),
                ('missing_local_build_root',{'remaining-stock-repaired':windows['remaining-stock-repaired']}),
            ]:
                reason='exact root' if control=='changed_local_parent_root' else 'Distinct local' if control=='ambiguous_nested_local_roots' else 'Complete explicit'
                rejects(control,lambda:transport.parent_guards(parent,guard_report,records,damaged),reason,report['controls'])
            missing=copy.deepcopy(guard_report);missing['guarded_parent_files_sha256'].pop(next(iter(guarded)))
            rejects('omitted_local_parent_guard',lambda:transport.parent_guards(parent,missing,records,windows),'guard closure',report['controls'])
            incomplete=root/'incomplete-collection'
            child=subprocess.run([sys.executable,'-B',str(HERE/'collect_local.py'),'--vm-output',str(source),
                '--runner-commit','0'*40,'--output',str(incomplete)],capture_output=True,text=True)
            require(child.returncode!=0 and not incomplete.exists(),
                    'Incomplete actual local matrix was sealed or created a collection output')
            report['controls'].append(dict(control='actual_incomplete_matrix_collection_refused',
                reason='Real collector CLI rejected the unfinished/missing profiles before creating output; no simulator or VM was launched'))
        require(all(sha(Path(n))==v for n,v in protected.items()) and all(sha(Path(n))==v for n,v in source_files.items()),
                'Actual local receipts or source changed during controls')
        report.update(status='passed-local-VM-receipt-and-path-controls',owning_inputs_unchanged=True,
                      complete_full38_positive_matrix_available=False)
    except BaseException as error:report['error']=str(error);raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);dump(a.output,report)
    print(len(report['controls']),'altered/partial local provenance controls rejected; actual eight-process receipt chain retained',flush=True)


if __name__=='__main__':main()
