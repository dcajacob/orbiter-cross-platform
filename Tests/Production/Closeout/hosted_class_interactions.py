#!/usr/bin/env python3
"""Run unchanged original interaction plans in retained hosted runtime packages; wider gates stay open."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from hosted_native_package import ROOT,load,sha,require
from contracts import atomic_json,PROFILES
from checklist import requirements
from capture_hosted_native_writer import package_inventory
from hosted_compositor_runtime import original_packages_unchanged
import capture_hosted_native_writer_runtime as runtime_writer

LOCK=ROOT/'Tests/Production/Closeout/class-interaction-original-source-v1.lock.json'
PLAN_DIR=ROOT/'Tests/Production/RemainingVessels/Interactions'
COMPILED='ccc02c8a34bd1f227624d8778a141e8736ae8111'


def conserved_sources():
    lock=load(LOCK);require(lock['compiled_runtime_source']==COMPILED,'Exact original compiled interaction runtime required')
    for relative,value in lock['source_sha256'].items():
        body=(ROOT/relative).read_bytes()
        require(body==subprocess.check_output(['git','-C',str(ROOT),'show',COMPILED+':'+relative]) and
                hashlib.sha256(body).hexdigest()==value,'Original interaction source/plan changed: '+relative)
    flows={}
    for name in lock['selected_plans']:
        plan=load(PLAN_DIR/name);require(plan['schema']==1 and plan['protocol']=='remaining-stock-original-input-interactions-v1','Exact original interaction plan required')
        for flow in plan['flows']:
            require(flow['id'] not in flows,'Duplicate original interaction flow');flows[flow['id']]=flow
    require(set(flows)==set(lock['required_flows']) and len(flows)==9 and
            {family for flow in flows.values() for family in flow['families']}==set(requirements()['class-eligibility']['families']),
            'All nine complete original flows and eleven families required')
    launch=flows['atlantis-original-launch-staging'];rms=flows['rms-six-joint-and-stow']
    require(launch['frames']==2304 and launch['fixed_step']==.015625 and rms['frames']==240 and rms['window_system']=='x11' and
            launch['original_population']==dict(path=lock['original_population']['historical_path'],sha256=lock['original_population']['sha256']),
            'Original canonical-clock launch/private X11/population binding must remain exact')
    return lock,flows


def bind_population_bytes(source,target,expected):
    source=Path(source);target=Path(target)
    require(source.is_file() and not source.is_symlink() and sha(source)==expected,'Exact published original population table required')
    require(not target.is_symlink(),'Historical spelling must not redirect to another file')
    if target.exists():require(target.is_file() and sha(target)==expected,'Existing historical-spelling population bytes differ; no overwrite')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(source.read_bytes())
    require(sha(source)==sha(target)==expected,'Original population bytes changed during binding')
    return dict(source=str(source),target=str(target),sha256=expected,historical_capture_relabelled=False)


def bind_population(output):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux',
            'Historical-spelling table binding is allowed only inside the ephemeral hosted container')
    lock,_=conserved_sources();pin=lock['original_population'];source=ROOT/pin['published_path'];target=Path(pin['historical_path'])
    record=bind_population_bytes(source,target,pin['sha256']);copy=output/'original-population.csv'
    require(not copy.exists(),'Fresh separately preserved population witness required');copy.write_bytes(source.read_bytes())
    record.update(protocol='phase6-identical-published-original-population-path-binding-v1',source_commit='ba38a7efccb5f770e87add95f5e966aa40270756',
                  profile='Debug-sse2',witness=str(copy),witness_sha256=sha(copy),old_local_capture_reconstructed=False,
                  scope='Only identical published CSV bytes are bound at the unchanged plan path; no old capture metadata or identity is invented.')
    atomic_json(output/'original-population-binding.json',record);return record


def candidate_version(body):
    found=re.findall(r'^\s*Candidate:\s*(\S+)\s*$',body,re.M)
    require(len(found)==1 and re.fullmatch(r'[0-9][A-Za-z0-9.+:~_-]*',found[0]) is not None,
            'One exact signed dated-archive Xvfb candidate required')
    return found[0]


def install_x11(output,run,required_version=None):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux','No local X11 package installation')
    before=package_inventory(subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True))
    policy=subprocess.check_output(['apt-cache','policy','xvfb'],text=True);(output/'xvfb-policy.txt').write_text(policy);version=candidate_version(policy)
    if required_version is not None:require(required_version==version,'Xvfb candidate differs from the actual completed readiness job')
    run('supply-declared-original-X11-backend',['apt-get','install','-y','--no-install-recommends','--no-upgrade','xvfb='+version],1200)
    body=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True);actual=package_inventory(body)
    additions=original_packages_unchanged(before,actual);(output/'x11-system-packages.txt').write_text(body)
    executable=Path(shutil.which('Xvfb') or '/missing-original-Xvfb');require(executable.is_file(),'Original private X11 backend unavailable')
    owner=subprocess.check_output(['dpkg-query','-S',str(executable)],text=True).strip()
    require(owner=='xvfb: '+str(executable) and actual.get('xvfb',actual.get('xvfb:amd64'))==version,'Actual private X11 package ownership/version differs')
    helper=Path(__file__);head=os.environ['GITHUB_SHA']
    require(helper.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',head+':'+helper.relative_to(ROOT).as_posix()]),'Immutable X11 provisioner source differs')
    record=dict(protocol='phase6-original-private-X11-backend-v1',status='installed-declared-private-X11-backend-only',source=head,
                helper_sha256=sha(helper),candidate_version=version,executable=str(executable),executable_sha256=sha(executable),
                package_owner=owner,policy_sha256=sha(output/'xvfb-policy.txt'),inventory_after=actual,actual_added_packages=additions,
                original_packages_and_versions_unchanged=True,snapshot='20261109T212432Z',simulator_processes=0,phase6_complete=False)
    verify_x11(record);atomic_json(output/'x11.json',record);return record


def verify_x11(record):
    require(record['source']==os.environ['GITHUB_SHA'] and record['helper_sha256']==sha(Path(__file__)) and
            sha(record['executable'])==record['executable_sha256'] and record['original_packages_and_versions_unchanged'] is True and
            record['simulator_processes']==0 and record['phase6_complete'] is False,'Actual declared X11 source/provider changed')
    actual=package_inventory(subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True))
    original_packages_unchanged(record['inventory_after'],actual)


def userspace_only():
    import hosted_class_userspace as original
    original.main();output=ROOT/'out/class-interaction-x11-readiness';require(not output.exists(),'Fresh X11 readiness proof required');output.mkdir()
    commands=[]
    def run(label,argv,timeout):
        log=output/(label+'.log');started=time.monotonic_ns()
        with log.open('w') as stream:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            try:code=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:child.kill();child.wait();raise
        commands.append(dict(label=label,argv=argv,actual_pid=child.pid,actual_returncode=code,elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log)))
        atomic_json(output/'commands.json',commands)
        if code:print(log.read_text(errors='replace')[-12000:],flush=True)
        require(code==0,'Declared X11 readiness installation failed')
    install_x11(output,run);conserved_sources();print('verified-original-package-inventory-and-declared-X11-backend-only')


def profile_coverage(profile,audits,flows):
    require(profile in PROFILES and len(audits)==5,'Every original plan scope required')
    seen={};identities=set();runtime=set();presents=0
    for audit in audits:
        require(audit['status']=='audited-selected-original-input-interactions-only' and audit['runtime_identity']['profile']==profile and
                audit['runtime_identity']['runtime_source_commit']==COMPILED and audit['runtime_identity']['sanitizer_linked'] is True and
                audit['actual_processes']==len(audit['flows'])*2 and audit['owning_bytes_unchanged'] is True and
                audit['diagnostic_only'] is True and audit['native_admission_qualified'] is False and audit['phase6_complete'] is False,
                'Complete unchanged original interaction audit required')
        runtime.add(audit['runtime_identity']['runtime_source_commit'])
        for name,runs in audit['flows'].items():
            require(name in flows and name not in seen and len(runs)==2,'Duplicate missing or incomplete original interaction flow')
            for actual in runs:
                require(actual['actual_pid']>0 and actual['actual_exitcode']==0 and
                        actual['lifecycle']==dict(rendered_frames=flows[name]['frames'],successful_presents=flows[name]['frames'],context_deleted=True) and
                        [v['check'] for v in actual['assertions']]==flows[name]['checks'],
                        'Every original frame, context and outcome assertion required')
                require(actual['actual_pid'] not in identities,'One simulator credited to multiple interaction cells')
                identities.add(actual['actual_pid']);presents+=actual['lifecycle']['successful_presents']
            seen[name]=runs
    require(set(seen)==set(flows) and runtime=={COMPILED} and len(identities)==18,'All nine flows/two repetitions and eighteen actual processes required')
    return dict(profile=profile,flows=list(seen),actual_processes=18,successful_presents=presents,runtime_source=COMPILED,
                published_raw_independent_replay_pending=True,complete_class_eligibility_qualified=False,normal_admission_qualified=False,
                phase6_complete=False,hands_on_ready=False)


def inspect_profile(profile,output,capture):
    _,flows=conserved_sources();audits=[];sources={}
    for name in load(LOCK)['selected_plans']:
        plan=PLAN_DIR/name;path=capture/plan.stem/'interactions.json';audit_path=output/(plan.stem+'-audit.json')
        data=load(path);audit=load(audit_path)
        require(data['plan']==str(plan) and data['producer_commit']==os.environ['GITHUB_SHA'] and
                audit['capture_sha256']==sha(path) and data['guarded_files_sha256'][str(plan)]==sha(plan),
                'Original interaction plan/capture/source binding differs')
        for flow in load(plan)['flows']:
            for repeat,run in enumerate(audit['flows'][flow['id']],1):
                folder=capture/plan.stem/(flow['id']+'-'+str(repeat));receipt=load(folder/'process-receipt.json')
                actual=[p for p in receipt['owned_process_identities'] if p['pid']==receipt['actual_collector_pid']]
                require(len(actual)==1 and actual[0]['start_ticks']>0 and actual[0]['argv']==load(folder/'invocation.json')['argv'] and
                        receipt['actual_collector_pid']==run['actual_pid'],'Actual simulator PID/start/invocation identity required')
        audits.append(audit);sources[str(path)]=sha(path);sources[str(audit_path)]=sha(audit_path)
    result=profile_coverage(profile,audits,flows);result['metadata_sha256']=sources;return result


def prepared_body():
    body=runtime_writer.prepared_body()
    changes=[("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-interactions-v1'"),
             ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-interactions'"),
             ("ROOT/'out/native-writer-container.json'","ROOT/'out/native-interaction-container.json'")]
    for before,after in changes:
        require(body.count(before)==(2 if 'container.json' in before else 1),'Conserved original runtime setup anchor differs');body=body.replace(before,after)
    anchor='        from hosted_native_runtime_dependencies import install as install_native_runtime,verify as verify_native_runtime'
    require(body.count(anchor)==1,'Original native runtime installer anchor differs')
    body=body.replace(anchor,"        from hosted_class_interactions import install_x11,verify_x11\n        require(os.environ.get('ORBITER_XVFB_VERSION'),'Exact completed X11 readiness version required')\n        report['original_X11_backend']=install_x11(output,run,os.environ['ORBITER_XVFB_VERSION']);save()\n"+anchor,1)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r'''
        from hosted_native_general_api import source_identity
        from hosted_class_interactions import conserved_sources,bind_population,inspect_profile,PLAN_DIR,LOCK
        from hosted_native_retry_reload_reference import bind,verify
        report['core_source_identity']=source_identity();report['original_interaction_source_identity']=conserved_sources()[0]
        reference=bind(a.profile);report['unchanged_original_reference']=reference
        population=bind_population(output);report['original_population_binding']=population;save()
        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-class-interactions'/a.profile
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        for name in load(LOCK)['selected_plans']:
            plan=PLAN_DIR/name;flows=load(plan)['flows']
            argv=py+['Tests/Production/RemainingVessels/native.py','--interaction-plan',str(plan),'--owner',str(ROOT),
                '--build',str(build/'engine'),'--build-record',str(build/'build.json'),
                '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
                '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
                '--gtk-build-record',str(providers/'libdecor-candidate/build.json'),
                '--repeats','2','--runtime-role','diagnostic','--jobs','1','--output',str(capture/plan.stem)]
            for case in sorted({f['case'] for f in flows}):argv+=['--case',case]
            for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
            argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
            run('original-complete-'+plan.stem,argv,14400,environment)
            run('original-independent-'+plan.stem,py+['Tests/Production/RemainingVessels/interactions.py',
                '--capture',str(capture/plan.stem/'interactions.json'),'--output',str(output/(plan.stem+'-audit.json'))],1800,environment)
        report['actual_original_interactions']=inspect_profile(a.profile,output,capture)
        verify(reference);verify_x11(report['original_X11_backend'])
        require(source_identity()==report['core_source_identity'] and conserved_sources()[0]==report['original_interaction_source_identity'] and
                sha(population['source'])==sha(population['target'])==sha(population['witness'])==population['sha256'],
                'Original sources, complete reference, X11 provider or population changed during capture')
'''.lstrip('\n')
    body=body[:start]+replacement+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    new="        report.update(status='captured-and-audited-original-nine-flow-interactions-only',actual_processes=18,\n            published_raw_independent_replay_pending=True,complete_class_eligibility_qualified=False,normal_admission_qualified=False,hands_on_ready=False)"
    require(body.count(old)==1,'Original complete writer completion anchor differs');return body.replace(old,new,1)


def main():
    if '--source-preflight' in sys.argv:
        p=argparse.ArgumentParser();p.add_argument('--source-preflight',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
        lock,flows=conserved_sources();require(not a.output.exists(),'Fresh interaction source preflight required')
        atomic_json(a.output,dict(status='verified-unchanged-nine-flow-original-interaction-scope-only',original_source_lock=lock,
            flows=flows,profiles=list(PROFILES),expected_actual_processes=72,expected_successful_presents=sum(f['frames'] for f in flows.values())*2*4,
            new_simulator_processes=0,complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False));return
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted Linux required; no local capture')
    conserved_sources()
    if '--userspace-only' in sys.argv:userspace_only();return
    exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})

if __name__=='__main__':main()
