#!/usr/bin/env python3
"""Reproduce original published class lifetime audits on a separate hosted worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import stat
import time
import zipfile
from hosted_native_package import ROOT,require,sha,load
from inspect_hosted_native_general_api import safe
import hosted_class_lifetimes as original
from hosted_native_general_api import source_identity
from capture_hosted_native_writer import stage_configuration

LOCK=ROOT/'Tests/Production/Closeout/class-lifetime-inputs-v1.lock.json'


def validate_api(record,profile):
    lock=load(LOCK);require(profile in lock['profiles'],'Explicit already-completed class profile required')
    pin=lock['profiles'][profile];run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==lock['repository'] and run['id']==lock['run_id'] and run['head_sha']==lock['source'] and
            run['head_branch']==lock['branch'] and run['path']==lock['workflow'] and run['run_attempt']==1 and
            run['status'] in ('queued','in_progress','completed'),
            'Exact original source-bound class run required; its overall state is preserved')
    require(len(jobs)==len(lock['jobs'])==5 and len({j['id'] for j in jobs})==5,'Complete actual original class job roster required')
    for job in jobs:
        require(str(job['id']) in lock['jobs'] and job['name']==lock['jobs'][str(job['id'])] and
                job['run_id']==run['id'] and job['head_sha']==run['head_sha'] and
                job['labels']==['ubuntu-24.04'],'Exact actual standard-hosted class producer required')
    for job_id in (lock['readiness_job_id'],pin['job_id']):
        selected=next(j for j in jobs if j['id']==job_id)
        require(selected['status']=='completed' and selected['conclusion']=='success',
                'Only an actually completed successful selected profile and readiness may be audited')
    require(artifact['id']==pin['artifact_id'] and artifact['name']=='original-class-lifetime-renewal-'+profile and
            artifact['expired'] is False and artifact['size_in_bytes']==pin['archive_bytes'] and
            artifact['digest']=='sha256:'+pin['archive_sha256'] and artifact['workflow_run']['id']==run['id'] and
            artifact['workflow_run']['head_sha']==run['head_sha'],'Exact immutable published class artifact required')
    return lock,pin


def verify_capture_sources(family,paused,source):
    require(family['producer_commit']==source and family['runtime_owner']==str(ROOT),
            'Actual original family producer and owning root must never be relabelled')
    for relative in ('Tests/Production/RemainingVessels/paused_attachments.py',
                     'Tests/Production/Closeout/hosted_class_lifetimes.py'):
        body=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+relative])
        require(paused['guarded_files_sha256'].get(str(ROOT/relative))==hashlib.sha256(body).hexdigest(),
                'Original paused producer must bind its actual original collector and hosted controller')
    # The original paused record has no producer_commit field. Its original guarded
    # collector/controller bytes and exact completed source-bound GitHub job bind it.
    return dict(family_producer=source,paused_producer_binding='actual-completed-source-bound-job-and-original-guarded-collector-controller')


def restore_archive(archive,destination,profile,owner):
    archive=Path(archive);destination=Path(destination);owner=Path(owner)
    require(not destination.exists(),'Fresh published class member restoration required');destination.mkdir(parents=True)
    prefixes=tuple(name+'/'+profile+'/' for name in ('native-class-lifetimes','native-class-paused','hosted-native-class-lifetimes'))
    files={};seen=set();materialized={}
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist()
        require(len(entries)<50000 and sum(i.file_size for i in entries)<4*1024**3,'Bounded complete class archive required')
        for item in entries:
            name=item.filename.rstrip('/') if item.is_dir() else item.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and
                    not (item.external_attr>>16)&0o7000,'Duplicate redirected or privileged class member')
            seen.add(name.casefold())
            if item.is_dir():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            body=incoming.read(item);target.write_bytes(body)
            files[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
            if name.startswith(prefixes):
                actual=owner/'out'/name;actual.parent.mkdir(parents=True,exist_ok=True)
                require(actual.parent.resolve()==actual.parent and not actual.exists() and not actual.is_symlink(),
                        'Published class restoration would replace or redirect evidence')
                os.link(target,actual);materialized[str(actual)]=files[name]['sha256']
    required={'native-class-lifetimes/'+profile+'/lifetimes.json','native-class-paused/'+profile+'/verification.json',
              'hosted-native-class-lifetimes/'+profile+'/collection.json'}
    require(required<=set(files),'Complete actual active paused and collection records required')
    require(all(sha(destination/n)==v['sha256'] for n,v in files.items()) and
            all(sha(p)==v for p,v in materialized.items()),'Every actual decoded class member must match')
    return files,materialized


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual independent standard hosted worker required; no local audit')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh separate class publication audit required')
    a.output.mkdir(parents=True)
    report=dict(protocol='phase6-independent-published-original-class-profile-v1',status='running',profile=a.profile,
                auditor_source=os.environ['GITHUB_SHA'],actual_auditor_pid=os.getpid(),commands=[],
                new_simulator_processes=0,qualification_granted=False,complete_class_eligibility_qualified=False,
                normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():(a.output/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label,argv,timeout=1200):
        log=a.output/(label+'.log');item=dict(label=label,argv=list(map(str,argv)))
        report['commands'].append(item);started=time.monotonic_ns()
        print('Starting independent '+label,flush=True)
        with log.open('w') as stream:
            child=subprocess.Popen(item['argv'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            item['actual_pid']=child.pid;save()
            try:item['actual_returncode']=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                child.kill();item.update(actual_returncode=child.wait(),timed_out=True);raise
            finally:item.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if item['actual_returncode']:print(log.read_text(errors='replace')[-16000:],flush=True)
        require(item['actual_returncode']==0,'Independent class input/audit stage failed: '+label)
    try:
        record=load(a.api);lock,pin=validate_api(record,a.profile)
        require(a.archive.stat().st_size==pin['archive_bytes'] and sha(a.archive)==pin['archive_sha256'],
                'Actual original class archive digest or length differs')
        original.conserved_sources()
        core=source_identity();report['auditor_core_source_identity']=core
        payload=a.output/'original-artifact';files,materialized=restore_archive(a.archive,payload,a.profile,ROOT)
        report.update(original_run_id=lock['run_id'],original_job_id=pin['job_id'],original_source=lock['source'],
                      original_artifact_id=pin['artifact_id'],original_archive_sha256=pin['archive_sha256'],
                      original_archive_bytes=pin['archive_bytes'],actual_raw_members=len(files),
                      actual_raw_decoded_bytes=sum(i['bytes'] for i in files.values()),source_api_sha256=sha(a.api),
                      original_producer_run_status=record['run']['status'],original_producer_run_conclusion=record['run']['conclusion'])
        (a.output/'raw-members.json').write_text(json.dumps(files,indent=2)+'\n');save()
        old=ROOT/'out/hosted-native-class-lifetimes'/a.profile;collection=load(old/'collection.json')
        family=ROOT/'out/native-class-lifetimes'/a.profile;paused=ROOT/'out/native-class-paused'/a.profile
        require(collection['protocol']=='phase6-hosted-native-class-lifetimes-v1' and
                collection['status']=='captured-and-audited-original-family-and-paused-lifetime-facets-only' and
                collection['collector_source']==lock['source'] and collection['compiled_runtime_source']==original.COMPILED and
                collection['profile']==a.profile and collection['actual_processes']==8 and collection['phase6_complete'] is False and
                collection['complete_class_eligibility_qualified'] is False,'Complete original scoped class collection required')
        require(collection['core_source_identity']['collector_source']==lock['source'] and
                {k:v for k,v in collection['core_source_identity'].items() if k!='collector_source'}==
                {k:v for k,v in core.items() if k!='collector_source'},'Exact complete 623-file core and original API identity required')
        require(collection['original_class_source_identity']==original.conserved_sources(),'Original class collector/auditor bodies differ')
        report['original_capture_source_bindings']=verify_capture_sources(
            load(family/'lifetimes.json'),load(paused/'verification.json'),lock['source'])
        for item in collection['commands']:
            require(item['actual_returncode']==0 and item['actual_pid']>0 and not item.get('timed_out') and
                    sha(old/(item['label']+'.log'))==item['log_sha256'],'Original process and log receipt differs')
        require((payload/'phase6-hosted-native'/a.profile/'build.json').read_bytes()==
                (ROOT/'out/phase6-hosted-native'/a.profile/'build.json').read_bytes(),'Original independently restored package manifest differs')
        py=[sys.executable,'-B']
        run('stock-data',py+['Tests/Production/prepare_native_data.py','--archive','out/data-cache/production-stock-data-v1.zip',
                            '--destination','out/native-stock-data','--group','all'])
        run('planet-data',py+['Tests/Production/prepare_hosted_data.py','--lock','Tests/Production/standard-planets.lock.json',
                             '--archive','out/planet-cache/Orbiter2016.zip','--destination','out/native-stock-planets'])
        run('base-assets',py+['Tests/Production/NativeScene/prepare.py','--delta-glider','--shuttle-a','--data','out/native-stock-data',
                             '--planets','out/native-stock-planets','--destination','out/native-stock-base-assets'])
        run('test-font',py+['Tests/Production/CockpitUI/prepare_fonts.py','--assets','out/native-stock-base-assets'])
        stage_configuration(ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'out/native-stock-base-assets')
        run('complete-stock-assets',py+['Tests/Production/Atlantis/stage_assets.py','--base-assets','out/native-stock-base-assets','--output','out/native-stock-assets'])
        for name in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json'):
            require((ROOT/'out/native-stock-assets'/name).read_bytes()==(payload/'native-stock-assets'/name).read_bytes(),
                    'Every independently restored original resource manifest byte must match: '+name)
        for name in original.CONSERVED:
            script=ROOT/name
            require(script.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',lock['source']+':'+name]),
                    'Original published class collector/auditor changed')
        new_family=a.output/'independent-family-lifetimes.json';new_paused=a.output/'independent-paused-lifetimes.json'
        run('unchanged-original-family-audit',py+['Tests/Production/RemainingVessels/lifetimes.py','--capture',str(family/'lifetimes.json'),'--output',str(new_family)])
        run('unchanged-original-paused-audit',py+['Tests/Production/Closeout/class_eligibility.py','--paused-capture',str(paused/'verification.json'),'--output',str(new_paused)])
        require(new_family.read_bytes()==(old/'independent-family-lifetimes.json').read_bytes() and
                new_paused.read_bytes()==(old/'independent-paused-lifetimes.json').read_bytes(),
                'Every original active and paused audit field must reproduce byte for byte')
        scoped=original.inspect_profile(a.profile,family/'lifetimes.json',old/'independent-family-lifetimes.json',
                                        paused/'verification.json',old/'independent-paused-lifetimes.json')
        require(scoped==collection['actual_lifetime_facets'],'Actual original complete profile facets differ')
        require(all(sha(payload/n)==v['sha256'] for n,v in files.items()) and all(sha(p)==v for p,v in materialized.items()),
                'An original published member changed during independent audit')
        require(source_identity()==core and original.conserved_sources()==collection['original_class_source_identity'],
                'Actual owning source changed during independent class audit')
        report.update(status='verified-published-original-family-and-paused-profile-only',
                      original_facets=scoped,active_worlds=140,paused_worlds=20,real_F5_reloads=19,
                      actual_original_simulator_processes=8,all_original_input_and_raw_bytes_unchanged=True,
                      original_active_and_paused_audits_reproduced_byte_identically=True,
                      original_family_audit_sha256=sha(new_family),original_paused_audit_sha256=sha(new_paused),
                      raw_members_sha256=sha(a.output/'raw-members.json'),original_collection_sha256=sha(old/'collection.json'),
                      other_profiles_and_complete_class_facets_pending=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
