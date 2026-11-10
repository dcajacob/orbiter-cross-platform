#!/usr/bin/env python3
"""Reproduce every unchanged published capability/observer audit without new simulation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import zipfile
from contracts import ROOT,PROFILES,require,sha,load,atomic_json
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
from inspect_hosted_native_general_api import safe
import hosted_class_capabilities as original
from hosted_native_general_api import source_identity
from hosted_native_retry_reload_reference import bind,verify
from audit_current_shader_phase_cli import compare_reference
from capture_hosted_native_writer import stage_configuration

LOCK=ROOT/'Tests/Production/Closeout/class-capability-published-inputs-v1.lock.json'
RECEIPTS=('reference-api/','reference-audit-restoration/restoration.json','original-stock-audit/transport/download.json',
          'original-stock-audit/independent/writer-audit.json','original-stock-audit/independent/original-persistence-audit.json')


def validate_api(record,profile):
    lock=load(LOCK);require(profile in lock['profiles'],'Exact original published capability profile required');pin=lock['profiles'][profile]
    run=record['run'];jobs=record['jobs'];a=record['artifact']
    require(record['repository']==lock['repository'] and run['id']==lock['run_id'] and run['head_sha']==lock['source'] and
            run['head_branch']==lock['branch'] and run['path']==lock['workflow'] and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success' and run['repository']['private'] is False and
            run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and len(jobs)==5 and
            {str(j['id']):j['name'] for j in jobs}==lock['jobs'] and
            all(j['run_id']==run['id'] and j['head_sha']==lock['source'] and j['status']=='completed' and
                j['conclusion']=='success' and j['labels']==['ubuntu-24.04'] for j in jobs),
            'Complete exact original five-job standard-runner capability producer required')
    require(a['id']==pin['artifact_id'] and a['name']=='original-class-capability-controls-'+profile and not a['expired'] and
            a['size_in_bytes']==pin['archive_bytes'] and a['digest']=='sha256:'+pin['archive_sha256'] and
            a['workflow_run']['id']==run['id'] and a['workflow_run']['head_sha']==lock['source'],
            'Exact immutable published capability ZIP required')
    return lock,pin


def restore_archive(archive,destination,profile,owner):
    destination=Path(destination);owner=Path(owner);require(profile in PROFILES and not destination.exists(),'Fresh complete original capability archive restoration required')
    destination.mkdir(parents=True);files={};materialized={};seen=set()
    prefixes=tuple(name+'/'+profile+'/' for name in ('native-class-capabilities','hosted-native-class-capabilities'))
    with zipfile.ZipFile(archive) as incoming:
        require(len(incoming.infolist())<50000 and sum(i.file_size for i in incoming.infolist())<4*1024**3,'Bounded complete published capability archive required')
        for info in incoming.infolist():
            name=info.filename.rstrip('/') if info.is_dir() else info.filename;safe(name)
            require(name.casefold() not in seen and not stat.S_ISLNK(info.external_attr>>16) and not (info.external_attr>>16)&0o7000,'Duplicate redirected or privileged capability member')
            seen.add(name.casefold())
            if info.is_dir():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);body=incoming.read(info);target.write_bytes(body)
            files[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
            if name.startswith(prefixes):
                actual=owner/'out'/name;actual.parent.mkdir(parents=True,exist_ok=True)
                require(actual.parent.resolve()==actual.parent and not actual.exists() and not actual.is_symlink(),'Published capability restoration cannot replace or redirect a file')
                os.link(target,actual);materialized[str(actual)]=files[name]['sha256']
    required={'native-class-capabilities/'+profile+'/capabilities.json','native-class-capabilities/'+profile+'/capability-probe.so',
              'native-class-capabilities/'+profile+'/observer-build-command.json','hosted-native-class-capabilities/'+profile+'/collection.json',
              'hosted-native-class-capabilities/'+profile+'/original-capabilities-audit.json'}
    require(required<=set(files),'Every original capture observer command and completed audit required')
    require(all(sha(destination/n)==v['sha256'] for n,v in files.items()) and all(sha(p)==v for p,v in materialized.items()),'Every original published member must retain exact bytes')
    return files,materialized


def old_guarded_inputs(values,payload,owner=ROOT):
    owner=Path(owner).resolve();payload=Path(payload).resolve();require(values,'Complete original guarded reference required')
    result={}
    for name,value in values.items():
        actual=Path(name);require(actual.is_absolute() and actual.is_relative_to(owner) and '..' not in actual.parts,'Original reference guard outside its source workspace')
        historical=actual;kind='same-actual-input-or-source'
        if actual.is_relative_to(owner/'out'):
            relative=actual.relative_to(owner/'out').as_posix()
            allowed=relative.startswith(RECEIPTS[0]) or relative in RECEIPTS[1:]
            if allowed and (payload/relative).is_file():historical=payload/relative;kind='exact-published-historical-reference-receipt'
        require(sha(historical)==value,'Original guarded reference/source byte differs: '+name)
        result[name]=dict(path=str(historical),sha256=value,identity=kind)
    require(len(result)==len(values),'Every original guard remains represented')
    return result


def inspect_reference(old,current,payload,source):
    require(old['protocol']=='phase6-hosted-audited-native-reload-retry-reference-v2' and old['collector_source']==source and
            old['status']=='bound-exact-audited-original-parent-saves-only' and len(old['saved_inputs'])==76 and
            old['original_saves_relabelled'] is False and old['native_admission_qualified'] is False and old['phase6_complete'] is False,
            'Actual original capability reference owner/scope required; never relabel to the auditor')
    for field in ('profile','capture','build','preserved','parent_capture_sha256','saved_inputs'):
        require(old[field]==current[field],'Every actual original parent/save/runtime identity must remain identical: '+field)
    for field in ('original_capture_source','original_auditor_source','original_windows_processes'):
        require(old['original'][field]==current['original'][field],'Independently restored original cohort identity differs: '+field)
    comparison=compare_reference(load(payload/'reference-audit-restoration/restoration.json'),load(ROOT/'out/reference-audit-restoration/restoration.json'))
    resolved=old_guarded_inputs(old['guarded_files_sha256'],payload)
    for name,value in old['guarded_files_sha256'].items():
        path=Path(name)
        if path.is_relative_to(ROOT/'Tests'):
            relative=path.relative_to(ROOT).as_posix()
            require(hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+relative])).hexdigest()==value,
                    'Original capability helper source owner differs')
    verify(current)
    return dict(old_reference_owner=source,current_reference_owner=current['collector_source'],
                old_guarded_inputs=resolved,independent_original_retry_comparison=comparison,
                old_API_receipts_preserved=True,old_capture_relabelled=False)


def reproduce_scope(profile,capture,published_audit,replayed_audit):
    require(Path(replayed_audit).read_bytes()==Path(published_audit).read_bytes(),
            'Every original capability/observer audit field must reproduce byte for byte')
    # Preserve the original metadata locations in the original scoped summary.
    computed=original.inspect_profile(profile,Path(capture),Path(published_audit))
    # The producer wrote this new summary as JSON: tuple signatures became arrays.
    # Match that representation without changing either original file or any value.
    return json.loads(json.dumps(computed,allow_nan=False))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=PROFILES,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual independent standard hosted worker required; no local raw audit')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh separate capability publication audit required');a.output.mkdir(parents=True)
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();require(head==os.environ['GITHUB_SHA'],'Actual immutable auditor owner required')
    require(not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=all','--','Tests/Production','.github'],text=True).strip(),'Clean immutable publication auditor and input lock required')
    proof=dict(protocol='phase6-independent-published-original-capability-profile-v1',status='running',auditor_source=head,profile=a.profile,
        actual_auditor_pid=os.getpid(),new_simulator_processes=0,commands=[],complete_class_eligibility_qualified=False,
        normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(a.output/'proof.json',proof)
    def run(label,argv,timeout=1800):
        log=a.output/(label+'.log');item=dict(label=label,argv=list(map(str,argv)));proof['commands'].append(item);started=time.monotonic_ns()
        print('Starting independent '+label,flush=True)
        with log.open('w') as stream:
            child=subprocess.Popen(item['argv'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);item['actual_pid']=child.pid;save()
            try:item['actual_returncode']=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:child.kill();item.update(actual_returncode=child.wait(),timed_out=True);raise
            finally:item.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if item['actual_returncode']:print(log.read_text(errors='replace')[-16000:],flush=True)
        require(item['actual_returncode']==0,'Independent original capability stage failed: '+label)
    save()
    try:
        api=load(a.api);lock,pin=validate_api(api,a.profile);require(a.archive.stat().st_size==pin['archive_bytes'] and sha(a.archive)==pin['archive_sha256'],'Actual published capability ZIP length/digest differs')
        original.sources();inventory=original.reference_inventory();core=source_identity();payload=a.output/'original-artifact'
        files,materialized=restore_archive(a.archive,payload,a.profile,ROOT);atomic_json(a.output/'raw-members.json',files)
        old=ROOT/'out/hosted-native-class-capabilities'/a.profile;capture=ROOT/'out/native-class-capabilities'/a.profile
        collection=load(old/'collection.json');captured=load(capture/'capabilities.json')
        require(collection['protocol']=='phase6-hosted-native-class-capabilities-v1' and collection['status']=='captured-and-audited-original-nine-scene-capability-observer-controls-only' and
                collection['collector_source']==lock['source'] and collection['compiled_runtime_source']==original.COMPILED and
                collection['actual_processes']==36 and collection['profile']==a.profile and collection['phase6_complete'] is False and
                collection['complete_class_eligibility_qualified'] is False and captured['producer_commit']==lock['source'] and
                captured['runtime_owner']==str(ROOT),'Complete unchanged original capability capture/source scope required')
        require(collection['original_capability_source_identity']==original.sources() and
                collection['core_source_identity']['collector_source']==lock['source'] and
                {k:v for k,v in collection['core_source_identity'].items() if k!='collector_source'}=={k:v for k,v in core.items() if k!='collector_source'},
                'Every original capability comparator and complete compiled core identity must remain unchanged')
        for item in collection['commands']:
            require(item['actual_returncode']==0 and item['actual_pid']>0 and not item.get('timed_out') and sha(old/(item['label']+'.log'))==item['log_sha256'],'Actual original command/process/log receipt differs')
        require((payload/'phase6-hosted-native'/a.profile/'build.json').read_bytes()==(ROOT/'out/phase6-hosted-native'/a.profile/'build.json').read_bytes(),'Original retained runtime package manifest differs')
        current=bind(a.profile);binding=inspect_reference(collection['unchanged_original_reference'],current,payload,lock['source'])
        py=[sys.executable,'-B']
        run('stock-data',py+['Tests/Production/prepare_native_data.py','--archive','out/data-cache/production-stock-data-v1.zip','--destination','out/native-stock-data','--group','all'])
        run('planet-data',py+['Tests/Production/prepare_hosted_data.py','--lock','Tests/Production/standard-planets.lock.json','--archive','out/planet-cache/Orbiter2016.zip','--destination','out/native-stock-planets'])
        run('base-assets',py+['Tests/Production/NativeScene/prepare.py','--delta-glider','--shuttle-a','--data','out/native-stock-data','--planets','out/native-stock-planets','--destination','out/native-stock-base-assets'])
        run('test-font',py+['Tests/Production/CockpitUI/prepare_fonts.py','--assets','out/native-stock-base-assets'])
        stage_configuration(ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'out/native-stock-base-assets')
        run('complete-stock-assets',py+['Tests/Production/Atlantis/stage_assets.py','--base-assets','out/native-stock-base-assets','--output','out/native-stock-assets'])
        for name in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json'):
            require((ROOT/'out/native-stock-assets'/name).read_bytes()==(payload/'native-stock-assets'/name).read_bytes(),'Every original staged capability asset manifest must reproduce exactly')
        audited=a.output/'original-capabilities-audit.json'
        run('unchanged-complete-original-capability-audit',py+['Tests/Production/RemainingVessels/capabilities.py','--capture',str(capture/'capabilities.json'),'--output',str(audited)])
        scoped=reproduce_scope(a.profile,capture/'capabilities.json',old/'original-capabilities-audit.json',audited)
        require(scoped==collection['actual_capability_controls'],'Complete original nine-scene/repeat/off-on scope differs')
        require(inspect_reference(collection['unchanged_original_reference'],current,payload,lock['source'])==binding and
                original.reference_inventory()==inventory and source_identity()==core and original.sources()==collection['original_capability_source_identity'] and
                all(sha(payload/n)==v['sha256'] for n,v in files.items()) and all(sha(path)==value for path,value in materialized.items()),
                'An original source/API/reference/observer/member/runtime byte changed during independent replay')
        atomic_json(a.output/'original-reference-bindings.json',binding)
        proof.update(status='verified-published-original-nine-scene-capability-and-observer-profile-only',original_source=lock['source'],
            original_run_id=lock['run_id'],original_job_id=pin['job_id'],original_artifact_id=pin['artifact_id'],original_archive_bytes=pin['archive_bytes'],
            original_archive_sha256=pin['archive_sha256'],source_api_sha256=sha(a.api),actual_raw_members=len(files),actual_raw_decoded_bytes=sum(v['bytes'] for v in files.values()),
            original_capability_audit_reproduced_byte_identically=True,original_capability_audit_sha256=sha(audited),original_collection_sha256=sha(old/'collection.json'),
            original_reference_bindings_sha256=sha(a.output/'original-reference-bindings.json'),raw_members_sha256=sha(a.output/'raw-members.json'),
            actual_original_capability_processes=36,original_facets=scoped,all_original_published_members_unchanged=True,
            other_profiles_and_formal_class_facets_pending=True)
    except BaseException as error:proof.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(proof['status'])


if __name__=='__main__':main()
