#!/usr/bin/env python3
"""Independently reread complete published v2 raw bytes, original readers and OS receipts."""
import hashlib,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'Tests/Production/Closeout')]
from contracts import require,sha,load,atomic_json
from inspect_published_numerical_observers import restore_outer
from stream_retained_numerical_inputs import verify
from rejection_input_bundle import safe
from native_capture import verify_scope,version_lock,RUNTIME
from frozen_admission_api import REFERENCE


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux','Independent standard-hosted raw audit only')
    profile=os.environ['PROFILE'];origin=load(HERE/'capture-origin-v1.json');base=ROOT/'out/physics-v2-published/native'/profile;api=load(base/'api.json');archive=base/'producer.zip';job=[j for j in api['jobs'] if j['id']==api['selected_job_id']]
    require(api['run']['id']==origin['run_id'] and api['run']['head_sha']==origin['source'] and api['run']['run_attempt']==1 and len(job)==1 and job[0]['name']=='Fresh v2 all157normal stock '+profile and job[0]['status']=='completed' and job[0]['conclusion']=='success' and job[0]['labels']==['ubuntu-24.04'] and
        api['artifact']['name']=='physics-v2-normal-'+profile+'-raw' and api['artifact']['expired'] is False and api['artifact']['workflow_run']['id']==origin['run_id'] and api['artifact']['workflow_run']['head_sha']==origin['source'] and archive.stat().st_size==api['artifact']['size_in_bytes'] and 'sha256:'+sha(archive)==api['artifact']['digest'],'Independent actual completed capture/API/archive binding required')
    output=ROOT/'out/physics-v2-normal-independent'/profile;output.mkdir(parents=True,exist_ok=False)
    prefix='hosted-normal-admission/'+profile;raw=prefix+'/capture-raw.tar.gz';outer=output/'outer';members=restore_outer(archive,outer,raw);index=load(outer/prefix/'capture-raw-index.json')
    relative='out/'+prefix;names=set(index['files']);selected={relative+'/'+n for n in ('collection.json','independent-full-stock-audit.json','capture/stock-scenarios.json')}
    selected|={n for n in names if n.startswith(relative+'/capture/') and (len(Path(n).parts)==6 and Path(n).suffix in {'.csv','.json','.txt','.log','.cfg','.scn','.so'} or '/api-assets/' in n)}
    with zipfile.ZipFile(archive) as z,z.open(raw) as stream:verified,closure=verify(ROOT,stream,index,selected,output/'raw-objects')
    unit=outer/'physics-v2-unit-recheck'/profile;target=ROOT/'out/physics-v2-unit-recheck'/profile;require(unit.is_dir() and not target.exists(),'Exact separately published original timeout replay required');target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(unit,target)
    captured=ROOT/relative;collection=load(captured/'collection.json');capture=captured/'capture';report=load(capture/'stock-scenarios.json');old_audit=load(captured/'independent-full-stock-audit.json')
    require(collection['status']=='captured-and-audited-fresh-v2-full-normal-profile-only' and collection['collector_source']==origin['source'] and collection['compiled_runtime_source']==RUNTIME and collection['actual_processes']==157 and
        collection['normal_admission_qualified'] is False and collection['phase6_complete'] is False,'Exact new version/source/full capture scope required')
    require(verify_scope(capture,captured/'independent-full-stock-audit.json',profile,version_lock())==collection['full_stock_scope'],'Recomputed full v2 scope/finite original repaired-scene binding differs')
    sys.path[:0]=[str(ROOT/'Tests/Production/StockScenarios')]
    import run as original
    from inventory import initial_ships,digest
    reference=original.api_admission.reference(REFERENCE);exit_ref=ROOT/'out/frozen-stock-exit';results={};pids=set()
    for name,case in report['cases'].items():
        folder=capture/case['output'];receipt=load(folder/'process-receipt.json');argv=load(folder/'invocation.json');pid=receipt['actual_collector_pid'];roots=[p for p in receipt['owned_process_identities'] if p['pid']==pid]
        require(receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and len(roots)==1 and roots[0]['argv']==argv and type(roots[0]['start_ticks']) is int and roots[0]['start_ticks']>0 and (pid,roots[0]['start_ticks']) not in pids and
            argv[0]==str(ROOT/'out/phase6-physics-v2-native'/profile/'engine/orbiter-production') and argv.count('--run')==1,'Every actual fresh executable, OS PID/start token, argv and normal terminal receipt required')
        pids.add((pid,roots[0]['start_ticks']))
        def argument(key):
            require(argv.count(key)==1 and argv.index(key)+1<len(argv),'Original launch flag missing/duplicated');return argv[argv.index(key)+1]
        require(argument('--frames')=='60' and argument('--fixed-step')==('0.015625' if case.get('general_api_startup_exit') else '.25') and argument('--evidence')==str(folder),'Unchanged original timing/output route required')
        require(case['initial_ships']==initial_ships((ROOT/'Scenarios'/name).read_text()),'Original complete source scenario/initialized graph differs')
        if case.get('general_api_startup_exit'):
            # Recreate only the canonical aliases opened by the unchanged reader.
            # Every variant body was streamed from the actual published TAR.
            variant=load(folder/'api-asset-variant.json');canonical=Path(variant['canonical_assets']);assets=Path(variant['variant_assets'])
            require(canonical==ROOT/'out/native-stock-assets' and assets==folder/'api-assets' and not canonical.exists(),'Exact fresh canonical/variant paths required')
            for n,h in variant['files_sha256'].items():
                safe(n)
                path=canonical/n;path.parent.mkdir(parents=True,exist_ok=True);actual=assets/n
                require(actual.is_file() and digest(actual)==h['variant'],'Every actual original API variant byte required')
                if h['variant']==h['original']:path.hardlink_to(actual)
                else:
                    require(n=='Script/Tests/GeneralApiTest.lua' and digest(ROOT/n)==h['original'],'Only the original explicitly qualified API script correction may differ');path.write_bytes((ROOT/n).read_bytes())
                require(digest(path)==h['original'],'Actual canonical API reader alias differs')
        actual=original.inspect(folder,case,case['returncode'],name,exit_ref,profile,reference)
        require(actual['status']=='passed' and all(case[k]==v for k,v in actual.items()),'Unchanged original reader rejected independently restored case: '+name)
        row=next(r for r in old_audit['runs'] if r['scenario']==name)
        require(row['files_sha256']==case['files_sha256'] and all(verified[relative+'/capture/'+case['output']+'/'+n]==h for n,h in case['files_sha256'].items()),'Every original observed/audited/raw case byte must match')
        results[name]=dict(original_reader_status=actual['status'],actual_pid=pid,start_ticks=roots[0]['start_ticks'],receipt_sha256=sha(folder/'process-receipt.json'),invocation_sha256=sha(folder/'invocation.json'))
    for n,h in report['source_sha256'].items():
        immutable=subprocess.check_output(['git','-C',str(ROOT),'show',origin['source']+':'+n]);require(hashlib.sha256(immutable).hexdigest()==sha(ROOT/n)==h,'Actual capture source must match immutable original producer')
    require(len(results)==len(pids)==157 and 'sha256:'+sha(archive)==api['artifact']['digest'],'All157actual launches and original published bytes required')
    atomic_json(output/'verification.json',dict(status='independently-verified-fresh-v2-full-normal-profile-only',physics_version='assembly-contact-v2',compiled_source=RUNTIME,capture_source=origin['source'],profile=profile,
        api_artifact=api['artifact'],actual_capture_job_id=job[0]['id'],complete_raw_closure=closure,outer_members_verified=len(members)+1,actual_original_reader_replays=157,actual_capture_processes=157,per_case_receipts=results,new_simulator_processes=0,complete_four_profile_gate_qualified=False,phase6_complete=False))


if __name__=='__main__':main()
