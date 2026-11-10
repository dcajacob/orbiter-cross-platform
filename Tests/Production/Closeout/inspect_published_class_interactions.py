#!/usr/bin/env python3
"""Independently replay complete published original interaction audits without a new simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from contracts import ROOT,PROFILES,require,sha,load,atomic_json
from inspect_hosted_native_general_api import safe
import hosted_class_interactions as original
import inspect_published_class_capabilities as reference
from hosted_native_general_api import source_identity
from hosted_native_retry_reload_reference import bind,verify
from capture_hosted_native_writer import stage_configuration

LOCK=ROOT/'Tests/Production/Closeout/class-interaction-published-inputs-v1.lock.json'


def validate_api(record,profile):
    lock=load(LOCK);require(profile in lock['profiles'],'Only a completed explicitly pinned original interaction profile may be replayed')
    pin=lock['profiles'][profile];run=record['run'];jobs=record['jobs'];artifact=record['artifact']
    require(record['repository']==lock['repository'] and run['repository']['private'] is False and
        run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['id']==lock['run_id'] and
        run['head_sha']==lock['source'] and run['head_branch']==lock['branch'] and run['path']==lock['workflow'] and
        run['run_attempt']==1 and run['status'] in ('queued','in_progress','completed'),
        'Exact original public interaction source/run required; other profile state is preserved')
    require(len(jobs)==5 and len({j['id'] for j in jobs})==5 and {str(j['id']):j['name'] for j in jobs}==lock['jobs'] and
        all(j['run_id']==run['id'] and j['head_sha']==lock['source'] and j['labels']==['ubuntu-24.04'] for j in jobs),
        'Complete original five-job standard hosted interaction roster required')
    for job_id in (lock['readiness_job_id'],pin['job_id']):
        selected=next(j for j in jobs if j['id']==job_id)
        require(selected['status']=='completed' and selected['conclusion']=='success','Selected original interaction profile and readiness must both be complete')
    require(artifact['id']==pin['artifact_id'] and artifact['name']=='original-class-interaction-controls-'+profile and
        artifact['expired'] is False and artifact['size_in_bytes']==pin['archive_bytes'] and
        artifact['digest']=='sha256:'+pin['archive_sha256'] and artifact['workflow_run']['id']==run['id'] and
        artifact['workflow_run']['head_sha']==lock['source'],'Exact closed original interaction artifact/API identity required')
    return lock,pin


def verify_members(destination,files):
    destination=Path(destination);checked={}
    for name,value in files.items():
        path=destination/name;require(path.resolve()==path and path.is_file() and not path.is_symlink(),'Original member path or regular-file identity changed')
        before=path.stat();key=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
        if key not in checked:
            checked[key]=sha(path);after=path.stat()
            require((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)==key,'Member changed during exact byte verification')
        require(before.st_size==value['bytes'] and checked[key]==value['sha256'],'An original logical member byte changed')
    return len(checked)


def restore_archive(archive,destination,profile,owner):
    destination=Path(destination);owner=Path(owner);store=destination.with_name(destination.name+'-content-store')
    require(profile in PROFILES and not destination.exists() and not store.exists(),'Fresh separate complete interaction restoration required')
    destination.mkdir(parents=True);store.mkdir();files={};materialized={};seen=set();unique={}
    prefixes=tuple(n+'/'+profile+'/' for n in ('native-class-interactions','hosted-native-class-interactions'))
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist()
        require(len(entries)<500000 and sum(v.file_size for v in entries)<64*1024**3,
                'Complete fixed interaction archive exceeds bounded metadata/member scope')
        for item in entries:
            name=item.filename.rstrip('/') if item.is_dir() else item.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,
                    'Duplicate redirected or privileged interaction member')
            seen.add(name.casefold())
            if item.is_dir():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            require(target.parent.resolve()==target.parent and not target.exists() and not target.is_symlink(),'Interaction member restoration cannot overwrite or redirect')
            checksum=hashlib.sha256();count=0
            with tempfile.NamedTemporaryFile(prefix='incoming-',dir=store,delete=False) as temp:
                scratch=Path(temp.name)
                with incoming.open(item) as source:
                    while body:=source.read(1024*1024):
                        temp.write(body);checksum.update(body);count+=len(body)
                require(count==item.file_size,'Complete original compressed member must be read and CRC checked')
            digest=checksum.hexdigest();content=store/digest
            if digest in unique:
                require(content.is_file() and content.stat().st_size==count,'Duplicate content identity differs');scratch.unlink()
            else:
                require(not content.exists(),'Fresh content-addressed original member required');scratch.rename(content);unique[digest]=count
            os.link(content,target);files[name]=dict(sha256=digest,bytes=count)
            if name.startswith(prefixes):
                actual=owner/'out'/name;actual.parent.mkdir(parents=True,exist_ok=True)
                require(actual.parent.resolve()==actual.parent and not actual.exists() and not actual.is_symlink(),'Original interaction evidence cannot be overwritten or redirected')
                os.link(target,actual);materialized[str(actual)]=files[name]
    required={'hosted-native-class-interactions/'+profile+'/collection.json','hosted-native-class-interactions/'+profile+'/original-population.csv'}
    require(required<=set(files),'Original complete collection/population witnesses required')
    for name in original.load(original.LOCK)['selected_plans']:
        stem=Path(name).stem
        require('native-class-interactions/'+profile+'/'+stem+'/interactions.json' in files and
                'hosted-native-class-interactions/'+profile+'/'+stem+'-audit.json' in files,'All five original capture and audit scopes required')
    require(verify_members(destination,files)==len(unique),'Every original logical member must match')
    verify_members(owner/'out',{Path(p).relative_to(owner/'out').as_posix():v for p,v in materialized.items()})
    return files,materialized,dict(unique_file_contents=len(unique),unique_materialized_bytes=sum(unique.values()),
        complete_logical_bytes=sum(v['bytes'] for v in files.values()),all_logical_members_retained=True,
        duplicate_file_contents_shared_by_hardlink=True,raw_content_or_capture_records_rewritten=False)


def bind_original_population(payload,profile):
    pin=load(original.LOCK)['original_population'];source=ROOT/pin['published_path'];target=Path(pin['historical_path'])
    witness=payload/'hosted-native-class-interactions'/profile/'original-population.csv'
    require(sha(source)==sha(witness)==pin['sha256'],'Complete original published Windows population table must remain exact')
    if not target.exists():
        require(not target.is_symlink() and target.is_absolute() and target==Path(pin['historical_path']),
                'Only the exact unchanged plan spelling can be bound')
        subprocess.run(['sudo','-n','install','-D','-m','0644',str(source),str(target)],check=True)
    result=original.bind_population_bytes(source,target,pin['sha256'])
    require(sha(witness)==result['sha256'],'Original population witness changed during binding');return result


def inspect_x11_capture(old,profile,capture,files):
    x11=load(old/'x11.json');collection=load(old/'collection.json')
    require(x11==collection['original_X11_backend'] and x11['source']==collection['collector_source'] and
        x11['candidate_version']=='2:21.1.22-1ubuntu1.3' and x11['executable']=='/usr/bin/Xvfb' and
        x11['executable_sha256']=='4adf27968d6f78f329f88beb71cbd3d181fa2018850a95ae3716afae2ae236c9' and
        x11['original_packages_and_versions_unchanged'] is True and x11['simulator_processes']==0,
        'Original verified private X11 provider/preflight lineage required; no new X11 is executed')
    result=[]
    for repeat in (1,2):
        folder=capture/'rms-six-joint-x11-v1'/('rms-six-joint-and-stow-'+str(repeat))/'compositor'
        invocation=load(folder/'invocation.json');receipt=load(folder/'process-receipt.json');argv=invocation['argv']
        require(argv[0]==x11['executable'] and invocation['executable_sha256']==x11['executable_sha256'] and
                argv[1:]==['-displayfd','1','-screen','0','1920x1080x24','-nolisten','tcp','-auth',argv[-1]] and
                receipt['terminal'] is True and receipt['actual_collector_pid']>0 and receipt['actual_returncode'] in (0,-15) and
                receipt['owned_process_identities'][0]['argv']==argv,'Original private no-network X11 invocation/clean receipt required')
        result.append(dict(invocation_sha256=sha(folder/'invocation.json'),receipt_sha256=sha(folder/'process-receipt.json'),
                           actual_original_Xvfb_pid=receipt['actual_collector_pid']))
    return dict(original_provider=x11,original_backends=result,new_X11_processes=0)


def reproduce_profile(profile,capture,old,output,source,run):
    _,flows=original.conserved_sources();audits=[];metadata={};receipts=[]
    for name in load(original.LOCK)['selected_plans']:
        plan=original.PLAN_DIR/name;manifest=capture/plan.stem/'interactions.json';published=old/(plan.stem+'-audit.json');audited=output/(plan.stem+'-audit.json')
        data=load(manifest)
        require(data['producer_commit']==source and data['runtime_owner']==str(ROOT) and data['plan']==str(plan) and
                data['guarded_files_sha256'][str(plan)]==sha(plan),'Original interaction producer/plan/runtime owner must never be relabelled')
        run('unchanged-original-'+plan.stem,[sys.executable,'-B','Tests/Production/RemainingVessels/interactions.py',
            '--capture',str(manifest),'--output',str(audited)])
        require(audited.read_bytes()==published.read_bytes(),'Every original interaction audit field must reproduce byte for byte')
        audit=load(audited);audits.append(audit);metadata[str(manifest)]=sha(manifest);metadata[str(published)]=sha(published)
        for flow in load(plan)['flows']:
            for repeat,actual in enumerate(audit['flows'][flow['id']],1):
                folder=capture/plan.stem/(flow['id']+'-'+str(repeat));receipt=load(folder/'process-receipt.json')
                own=[p for p in receipt['owned_process_identities'] if p['pid']==receipt['actual_collector_pid']]
                require(len(own)==1 and own[0]['start_ticks']>0 and own[0]['argv']==load(folder/'invocation.json')['argv'] and
                        actual['actual_pid']==own[0]['pid'],'Every original simulator PID/start/argv must remain represented')
                receipts.append(dict(flow=flow['id'],repeat=repeat,pid=own[0]['pid'],start_ticks=own[0]['start_ticks']))
    require(len(receipts)==len({(p['pid'],p['start_ticks']) for p in receipts})==18,'Every actual original simulator identity must be unique')
    scoped=original.profile_coverage(profile,audits,flows);scoped['metadata_sha256']=metadata
    require(scoped==load(old/'collection.json')['actual_original_interactions'],'Complete unchanged nine-flow/two-repeat scope differs')
    return scoped,receipts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=PROFILES,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual separate standard hosted runner required; no local bulk audit')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();require(head==os.environ['GITHUB_SHA'],'Actual immutable auditor source required')
    require(not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=all','--','Tests/Production','.github'],text=True).strip(),'Clean immutable interaction auditor source required')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh separate original interaction replay required');a.output.mkdir(parents=True)
    proof=dict(protocol='phase6-independent-published-original-interaction-profile-v1',status='running',auditor_source=head,
        profile=a.profile,actual_auditor_pid=os.getpid(),commands=[],new_simulator_processes=0,complete_class_eligibility_qualified=False,
        normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(a.output/'proof.json',proof)
    def run(label,argv,timeout=2400):
        log=a.output/(label+'.log');item=dict(label=label,argv=list(map(str,argv)));proof['commands'].append(item);started=time.monotonic_ns()
        print('Starting independent '+label,flush=True)
        with log.open('w') as stream:
            child=subprocess.Popen(item['argv'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);item['actual_pid']=child.pid;save()
            try:item['actual_returncode']=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:child.kill();item.update(actual_returncode=child.wait(),timed_out=True);raise
            finally:item.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if item['actual_returncode']:print(log.read_text(errors='replace')[-16000:],flush=True)
        require(item['actual_returncode']==0,'Independent unchanged interaction stage failed: '+label)
    save()
    try:
        api=load(a.api);lock,pin=validate_api(api,a.profile);require(a.archive.stat().st_size==pin['archive_bytes'] and sha(a.archive)==pin['archive_sha256'],
            'Complete streamed original interaction ZIP length/digest differs')
        conserved,flows=original.conserved_sources();core=source_identity();payload=a.output/'original-artifact'
        files,materialized,storage=restore_archive(a.archive,payload,a.profile,ROOT);atomic_json(a.output/'raw-members.json',files)
        old=ROOT/'out/hosted-native-class-interactions'/a.profile;capture=ROOT/'out/native-class-interactions'/a.profile;collection=load(old/'collection.json')
        require(collection['protocol']=='phase6-hosted-native-class-interactions-v1' and collection['status']=='captured-and-audited-original-nine-flow-interactions-only' and
                collection['collector_source']==lock['source'] and collection['compiled_runtime_source']==original.COMPILED and
                collection['actual_processes']==18 and collection['profile']==a.profile and collection['phase6_complete'] is False and
                collection['complete_class_eligibility_qualified'] is False and collection['original_interaction_source_identity']==conserved,
                'Complete exact original interaction collection/source scope required')
        require(collection['core_source_identity']['collector_source']==lock['source'] and
                {k:v for k,v in collection['core_source_identity'].items() if k!='collector_source'}=={k:v for k,v in core.items() if k!='collector_source'},
                'Every original complete 623-file compiled core identity must remain equal')
        for item in collection['commands']:
            require(item['actual_pid']>0 and item['actual_returncode']==0 and not item.get('timed_out') and
                    sha(old/(item['label']+'.log'))==item['log_sha256'],'Every original process and command log receipt required')
        require((payload/'phase6-hosted-native'/a.profile/'build.json').read_bytes()==(ROOT/'out/phase6-hosted-native'/a.profile/'build.json').read_bytes(),
                'Original complete retained runtime package manifest differs')
        current=bind(a.profile);binding=reference.inspect_reference(collection['unchanged_original_reference'],current,payload,lock['source'])
        population=bind_original_population(payload,a.profile);x11=inspect_x11_capture(old,a.profile,capture,files)
        py=[sys.executable,'-B']
        for label,argv in [
            ('stock-data',py+['Tests/Production/prepare_native_data.py','--archive','out/data-cache/production-stock-data-v1.zip','--destination','out/native-stock-data','--group','all']),
            ('planet-data',py+['Tests/Production/prepare_hosted_data.py','--lock','Tests/Production/standard-planets.lock.json','--archive','out/planet-cache/Orbiter2016.zip','--destination','out/native-stock-planets']),
            ('base-assets',py+['Tests/Production/NativeScene/prepare.py','--delta-glider','--shuttle-a','--data','out/native-stock-data','--planets','out/native-stock-planets','--destination','out/native-stock-base-assets']),
            ('test-font',py+['Tests/Production/CockpitUI/prepare_fonts.py','--assets','out/native-stock-base-assets'])]:run(label,argv)
        stage_configuration(ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'out/native-stock-base-assets')
        run('complete-stock-assets',py+['Tests/Production/Atlantis/stage_assets.py','--base-assets','out/native-stock-base-assets','--output','out/native-stock-assets'])
        for name in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json'):
            require((ROOT/'out/native-stock-assets'/name).read_bytes()==(payload/'native-stock-assets'/name).read_bytes(),'Original global asset manifest must reproduce exactly')
        scoped,simulators=reproduce_profile(a.profile,capture,old,a.output,lock['source'],run)
        require(reference.inspect_reference(collection['unchanged_original_reference'],current,payload,lock['source'])==binding and
                original.conserved_sources()[0]==conserved and source_identity()==core and
                sha(population['source'])==sha(population['target'])==population['sha256'] and
                sha(a.archive)==pin['archive_sha256'] and verify_members(payload,files)==storage['unique_file_contents'] and
                verify_members(ROOT/'out',{Path(path).relative_to(ROOT/'out').as_posix():value for path,value in materialized.items()})>0,
                'Every original source/reference/archive/asset/member must remain byte-identical through replay completion')
        atomic_json(a.output/'original-reference-bindings.json',binding);atomic_json(a.output/'original-X11-bindings.json',x11)
        proof.update(status='verified-published-original-nine-flow-interaction-profile-only',original_source=lock['source'],
            original_run_id=lock['run_id'],original_job_id=pin['job_id'],original_artifact_id=pin['artifact_id'],original_archive_bytes=pin['archive_bytes'],
            original_archive_sha256=pin['archive_sha256'],source_api_sha256=sha(a.api),actual_raw_members=len(files),
            actual_raw_decoded_bytes=sum(v['bytes'] for v in files.values()),complete_original_storage=storage,
            all_five_original_interaction_audits_reproduced_byte_identically=True,original_collection_sha256=sha(old/'collection.json'),
            original_reference_bindings_sha256=sha(a.output/'original-reference-bindings.json'),original_X11_bindings_sha256=sha(a.output/'original-X11-bindings.json'),
            raw_members_sha256=sha(a.output/'raw-members.json'),original_facets=scoped,actual_original_simulator_identities=simulators,
            actual_original_interaction_processes=18,original_audit_sha256={name:sha(a.output/(Path(name).stem+'-audit.json')) for name in load(original.LOCK)['selected_plans']},
            all_original_logical_members_and_input_guards_unchanged=True,other_profiles_and_formal_class_facets_pending=True)
    except BaseException as error:proof.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(proof['status'])

if __name__=='__main__':main()
