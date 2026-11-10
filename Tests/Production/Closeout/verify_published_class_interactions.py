#!/usr/bin/env python3
"""Verify independently published interaction audits and complete member witnesses on hosted runners."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path,PurePosixPath
import subprocess
import sys
from contracts import ROOT,PROFILES,load,sha,require,atomic_json
import final_hosted_class_capabilities as closed
import inspect_published_class_interactions as replay

LOCK=ROOT/'Tests/Production/Closeout/class-interaction-publication-inputs-v1.lock.json'
CI=PurePosixPath('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')
sys.path.insert(0,str(ROOT/'Tests/Production/RemainingVessels'))
from interactions import OPS
FLAGS=('complete_class_eligibility_qualified','normal_admission_qualified','phase6_complete','hands_on_ready')


def verify_manifest(raw,proof):
    require(raw and len(raw)==proof['actual_raw_members'],'Every actual original logical member must remain represented')
    seen=set();unique={}
    for name,value in raw.items():
        replay.safe(name);require(name.casefold() not in seen,'Duplicate original member alias');seen.add(name.casefold())
        require(set(value)=={'sha256','bytes'} and isinstance(value['bytes'],int) and value['bytes']>=0 and
                isinstance(value['sha256'],str) and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256']),
                'Exact finite original member length and SHA-256 required')
        require(value['sha256'] not in unique or unique[value['sha256']]==value['bytes'],'Shared original content has inconsistent byte length')
        unique[value['sha256']]=value['bytes']
    storage=proof['complete_original_storage'];total=sum(v['bytes'] for v in raw.values())
    require(total==proof['actual_raw_decoded_bytes']==storage['complete_logical_bytes'] and
            len(unique)==storage['unique_file_contents'] and sum(unique.values())==storage['unique_materialized_bytes'] and
            storage['all_logical_members_retained'] is True and storage['duplicate_file_contents_shared_by_hardlink'] is True and
            storage['raw_content_or_capture_records_rewritten'] is False,'Complete lossless original member/storage closure differs')
    return dict(logical_members=len(raw),logical_bytes=total,unique_contents=len(unique),unique_bytes=sum(unique.values()))


def witness(raw,name,digest,expected_bytes=None):
    replay.safe(name);require(name in raw and raw[name]['sha256']==digest,'Actual original published member SHA-256 differs: '+name)
    if expected_bytes is not None:require(raw[name]['bytes']==expected_bytes,'Actual complete original member byte length differs: '+name)


def manifest_payload(bodies,members,expected_sha256):
    # The immutable producer uploaded one file, so its published ZIP root is the basename.
    # Do not rewrite the original capture, witness ZIP, or expected digest to fit a new path.
    require(set(bodies)==set(members)=={'raw-members.json'},'Exact original single-file witness ZIP layout required')
    body=bodies['raw-members.json']
    require(members['raw-members.json']==hashlib.sha256(body).hexdigest()==expected_sha256,
            'Exact original raw-member witness byte digest required')
    return json.loads(body)


def inspect_profile(profile,meta_bodies,meta_members,raw_bodies,raw_members,pins):
    source=pins['metadata']['source'];prefix='interaction-independent/'+profile+'/'
    for relative in ('Tests/Production/Closeout/inspect_published_class_interactions.py','Tests/Production/Closeout/download_published_class_interactions.py','Tests/Production/Closeout/hosted_class_interactions.py'):
        require(sha(ROOT/relative)==closed.gitsha(source,relative),'Exact immutable original replay/scope helper implementation required')
    proof=json.loads(meta_bodies[prefix+'proof.json']);raw=manifest_payload(raw_bodies,raw_members,proof['raw_members_sha256'])
    lock,pin=replay.validate_api(json.loads(meta_bodies['class-interaction-published/'+profile+'/api.json']),profile)
    require(proof['protocol']=='phase6-independent-published-original-interaction-profile-v1' and
            proof['status']=='verified-published-original-nine-flow-interaction-profile-only' and proof['auditor_source']==source and
            proof['profile']==profile and proof['actual_auditor_pid']>0 and proof['original_source']==lock['source'] and
            proof['original_run_id']==lock['run_id'] and proof['original_job_id']==pin['job_id'] and
            proof['original_artifact_id']==pin['artifact_id'] and proof['original_archive_bytes']==pin['archive_bytes'] and
            proof['original_archive_sha256']==pin['archive_sha256'],'Exact completed original interaction/replay lineage required')
    require(proof['source_api_sha256']==meta_members['class-interaction-published/'+profile+'/api.json'] and
            proof['raw_members_sha256']==raw_members['raw-members.json'] and
            proof['all_five_original_interaction_audits_reproduced_byte_identically'] is True and
            proof['all_original_logical_members_and_input_guards_unchanged'] is True and
            proof['actual_original_interaction_processes']==18 and proof['new_simulator_processes']==0 and
            proof['other_profiles_and_formal_class_facets_pending'] is True and all(proof[k] is False for k in FLAGS),
            'Every original raw witness, byte-identical audit and remaining acceptance gate required')
    storage=verify_manifest(raw,proof);audits=[];metadata={};identities={};_,flows=replay.original.conserved_sources()
    for value in proof['actual_original_simulator_identities']:
        require(value['pid']>0 and value['start_ticks']>0 and value['repeat'] in (1,2) and value['flow'] in flows,
                'Actual original process/start identity required')
        key=(value['flow'],value['repeat']);require(key not in identities,'Duplicate original flow/repetition identity');identities[key]=value
    require(len(identities)==len({(v['pid'],v['start_ticks']) for v in identities.values()})==18,'Every original interaction process must remain unique')
    for plan_name in load(replay.original.LOCK)['selected_plans']:
        stem=Path(plan_name).stem;name=prefix+stem+'-audit.json';audit=json.loads(meta_bodies[name]);audits.append(audit)
        require(meta_members[name]==proof['original_audit_sha256'][plan_name],'Every complete original audit must reproduce byte for byte')
        old='hosted-native-class-interactions/'+profile+'/'+stem+'-audit.json';capture='native-class-interactions/'+profile+'/'+stem+'/interactions.json'
        witness(raw,old,meta_members[name]);witness(raw,capture,audit['capture_sha256'])
        metadata[str(CI/'out'/old)]=meta_members[name];metadata[str(CI/'out'/capture)]=audit['capture_sha256']
        require(audit['qualified_families']==sorted({f for flow in load(replay.original.PLAN_DIR/plan_name)['flows'] for f in flow['families']}),
                'Complete original plan/family scope required')
        for flow in load(replay.original.PLAN_DIR/plan_name)['flows']:
            for repeat,actual in enumerate(audit['flows'][flow['id']],1):
                root='native-class-interactions/'+profile+'/'+stem+'/'+flow['id']+'-'+str(repeat)+'/'
                require(actual['actual_pid']==identities[(flow['id'],repeat)]['pid'],'Original audit/process identity differs')
                for leaf,digest in actual['files_sha256'].items():
                    require(PurePosixPath(leaf).name==leaf,'Original audit requires flat complete captured files');witness(raw,root+leaf,digest)
                witness(raw,root+'scene.rgba',actual['files_sha256']['scene.rgba'],1280*720*4)
                for check in actual['assertions']:
                    require(all(not isinstance(v,float) or math.isfinite(v) for v in (check['left'],check['right'])) and
                            OPS[check['check']['op']](check['left'],check['right']),
                            'Every original finite actuator/outcome comparison required')
            for leaf in ('flight-state.csv','flight-animations.csv','input-events.csv','saved.scn','scene.rgba'):
                first='native-class-interactions/'+profile+'/'+stem+'/'+flow['id']+'-1/'+leaf
                second='native-class-interactions/'+profile+'/'+stem+'/'+flow['id']+'-2/'+leaf
                require(raw[first]==raw[second],'Original repeated state, input, save and full-frame equality must remain exact')
    coverage=replay.original.profile_coverage(profile,audits,flows);coverage['metadata_sha256']=metadata
    require(coverage==proof['original_facets'],'Every original profile/flow/repeat/frame/guard scope must remain complete')
    witness(raw,'hosted-native-class-interactions/'+profile+'/collection.json',proof['original_collection_sha256'])
    reference=json.loads(meta_bodies[prefix+'original-reference-bindings.json'])
    require(meta_members[prefix+'original-reference-bindings.json']==proof['original_reference_bindings_sha256'] and
            reference['old_reference_owner']==lock['source'] and reference['current_reference_owner']==source and
            reference['old_API_receipts_preserved'] is True and reference['old_capture_relabelled'] is False and
            len(reference['old_guarded_inputs'])==293,'Every original and current source/reference guard must remain represented')
    comparison=reference['independent_original_retry_comparison']
    require(comparison['raw_API_and_log_transport_identities_preserved'] is True and comparison['API_attempts_normalized'] is False and
            comparison['old_failed_attempt_relabelled'] is False,'Prior failed attempt and distinct original API transports must remain exact')
    for name,entry in reference['old_guarded_inputs'].items():
        relative=PurePosixPath(name).relative_to(CI).as_posix()
        if entry['identity']=='exact-published-historical-reference-receipt':
            rel=PurePosixPath(name).relative_to(CI/'out').as_posix();require(rel.startswith(replay.reference.RECEIPTS[0]) or rel in replay.reference.RECEIPTS[1:],
                'Only explicit historical API receipt paths may use archived metadata')
            require(entry['path']==str(CI/'out/interaction-independent'/profile/'original-artifact'/rel),'Historical receipt path identity differs')
            witness(raw,rel,entry['sha256'])
        else:
            require(entry['identity']=='same-actual-input-or-source' and entry['path']==name,'Original source/runtime/reference guard was redirected')
            if relative.startswith('Tests/'):
                require(closed.gitsha(lock['source'],relative)==entry['sha256'],'Original immutable reference helper source differs')
    x11=json.loads(meta_bodies[prefix+'original-X11-bindings.json']);provider=x11['original_provider']
    require(meta_members[prefix+'original-X11-bindings.json']==proof['original_X11_bindings_sha256'] and
            x11['new_X11_processes']==0 and len(x11['original_backends'])==2 and provider['source']==lock['source'] and
            provider['candidate_version']=='2:21.1.22-1ubuntu1.3' and
            provider['executable_sha256']=='4adf27968d6f78f329f88beb71cbd3d181fa2018850a95ae3716afae2ae236c9' and
            provider['helper_sha256']==closed.gitsha(lock['source'],'Tests/Production/Closeout/hosted_class_interactions.py'),
            'Both original private X11 backend/provider identities required without reexecution')
    for repeat,backend in enumerate(x11['original_backends'],1):
        root='native-class-interactions/'+profile+'/rms-six-joint-x11-v1/rms-six-joint-and-stow-'+str(repeat)+'/compositor/'
        require(backend['actual_original_Xvfb_pid']>0,'Actual original private X11 process identity required')
        witness(raw,root+'invocation.json',backend['invocation_sha256']);witness(raw,root+'process-receipt.json',backend['receipt_sha256'])
    for command in proof['commands']:
        require(command['actual_pid']>0 and command['actual_returncode']==0 and not command.get('timed_out') and
                meta_members[prefix+command['label']+'.log']==command['log_sha256'],'Every actual independent command/log receipt required')
    expected=['stock-data','planet-data','base-assets','test-font','complete-stock-assets']+['unchanged-original-'+Path(n).stem for n in load(replay.original.LOCK)['selected_plans']]
    require([v['label'] for v in proof['commands']]==expected,'Every original provisioning/auditing command required; no simulator may be launched')
    closed.controls(meta_bodies,'published-interaction-controls.json',source,366)
    return dict(profile=profile,status='verified-published-complete-original-nine-flow-interactions-only',actual_original_processes=18,
        actual_original_successful_presents=coverage['successful_presents'],complete_flows=9,repeats=2,compiled_runtime_source=replay.original.COMPILED,
        original_capture_source=lock['source'],independent_replay_source=source,original_raw_artifact_id=pin['artifact_id'],
        original_raw_archive_sha256=pin['archive_sha256'],original_raw_archive_bytes=pin['archive_bytes'],raw_members_sha256=proof['raw_members_sha256'],
        complete_member_witness=storage,all_five_original_audits_byte_identical=True,all_293_original_source_reference_guards_preserved=True,
        original_audit_sha256=proof['original_audit_sha256'],independent_proof_sha256=meta_members[prefix+'proof.json'],
        new_simulator_processes=0,new_X11_processes=0,**{k:False for k in FLAGS})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual independent standard hosted publication check required')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out'),'Fresh separate published interaction scope output required');a.output.mkdir(parents=True)
    lock=load(LOCK);result={};inputs={}
    for profile,pins in lock['profiles'].items():
        restored={}
        for role,pin in pins.items():
            base=a.inputs/profile/role;bodies,members=closed.restore(base,pin);restored[role]=(bodies,members)
            inputs[profile+'/'+role]=dict(source=pin['source'],run_id=pin['run_id'],artifact_id=pin['artifact_id'],
                archive_bytes=pin['archive_bytes'],archive_sha256=pin['archive_sha256'],api_sha256=sha(base/'api.json'),members_sha256=members)
        result[profile]=inspect_profile(profile,*restored['metadata'],*restored['witness'],pins)
    require(set(result)==set(lock['profiles'])==set(lock['expected_profiles']),'Complete exact declared published profile scope required')
    report=dict(protocol='phase6-published-complete-original-interaction-receipt-verification-v1',
        status='verified-published-original-interaction-profiles-only',auditor_source=os.environ['GITHUB_SHA'],profiles=result,inputs=inputs,
        actual_original_processes=sum(v['actual_original_processes'] for v in result.values()),
        actual_original_successful_presents=sum(v['actual_original_successful_presents'] for v in result.values()),
        original_frozen_interaction_sources=replay.original.conserved_sources()[0],exact_input_lock_sha256=sha(LOCK),
        new_simulator_processes=0,new_X11_processes=0,remaining_profiles_and_formal_class_eligibility_pending=True,
        **{k:False for k in FLAGS})
    atomic_json(a.output/'published-interaction-verification.json',report);print(report['status'])

if __name__=='__main__':main()
