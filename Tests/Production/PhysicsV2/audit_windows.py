#!/usr/bin/env python3
"""Verify published Windows v2 SDK/capture bytes on Linux; start no Windows processes."""
import hashlib,json,os,shutil,stat,subprocess,sys,tarfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/CurrentWindows')]
from contracts import require,sha,load,atomic_json
from restore import api
from restore_sdk import unpack,safe
from retain_hosted_sdk import unit_result
from rejection_input_bundle import inspect_archive
from windows_capture import inspect as inspect_all_scenes


def main():
    config=os.environ['CONFIGURATION'];require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux','Independent standard-server byte inspection only')
    origin,base,record,archive,job=api('windows',config);output=ROOT/'out/physics-v2-Windows-independent'/config;output.mkdir(parents=True,exist_ok=False)
    sdk=output/'sdk-outer';unpack(archive,sdk);report=load(sdk/'current-application.json');item=report['configurations'][config];inner=sdk/'runtime.zip'
    require(report['source_commit']==origin['source'] and report['status']=='built-and-client-tested-awaiting-complete-stock-qualification' and report['owning_sources_unchanged'] is True and report['runtime_archive_sha256']==sha(inner) and report['runtime_archive_bytes']==inner.stat().st_size and
        report['github']['source']==origin['source'] and report['github']['run_id']==origin['run_id'] and report['github']['run_attempt']==1 and report['github']['image_os'] in ('win25','win25-vs2026') and item['status']=='built','Actual original new Windows SDK producer required')
    source_names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',origin['source']],text=True).splitlines();require(set(source_names)==set(report['source_guard_sha256_lf']),'Complete actual compiled owning-source roster required')
    with subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as reader:
        for n in source_names:
            safe(n);reader.stdin.write((origin['source']+':'+n+'\n').encode());reader.stdin.flush();header=reader.stdout.readline().split();require(len(header)==3 and header[1]==b'blob','Actual immutable source blob required');raw=reader.stdout.read(int(header[2]));require(reader.stdout.read(1)==b'\n','Complete source blob required')
            require(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==report['source_guard_sha256_lf'][n] and (ROOT/n).read_bytes().replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'),'Actual compiled Windows source differs from its immutable owner')
        reader.stdin.close();require(reader.wait()==0,'Original complete source object reader failed')
    hashes={};sdk_manifest=None
    with zipfile.ZipFile(inner) as z:
        entries=z.infolist();require(len(entries)==len({m.filename.casefold() for m in entries})==len(item['runtime_files_sha256']) and sum(m.file_size for m in entries)<4*1024**3,'Complete bounded original SDK member roster required')
        for m in entries:
            safe(m.filename);require(not stat.S_ISLNK(m.external_attr>>16),'Original SDK contains no symbolic redirects');h=hashlib.sha256()
            with z.open(m) as stream:
                if m.filename=='test-runtime.json':sdk_manifest=json.loads(stream.read());h.update(z.read(m))
                else:
                    for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
            hashes[m.filename]=h.hexdigest();require(item['runtime_files_sha256'].get(m.filename)==hashes[m.filename],'Actual original v2 SDK member differs')
    require(sdk_manifest['source_commit']==origin['source'] and hashes['test-runtime.json']==item['sdk_manifest_sha256'] and unit_result(load(sdk/'registered-tests.json'),sdk/'runtime-ctest.xml')==item['tests'] and item['tests']['executed_processes']==28,'Every original actual Windows SDK/test guard required')
    captured=ROOT/'out/physics-v2-published/windows'/config;binding=load(captured/'api.json');p=load(HERE/'capture-origin-v1.json');raw_zip=captured/'producer.zip';found=[j for j in binding['jobs'] if j['id']==binding['selected_job_id']]
    require(binding['run']['id']==p['run_id'] and binding['run']['head_sha']==p['source'] and binding['run']['run_attempt']==1 and len(found)==1 and found[0]['name']=='Fresh v2 original failed scenes Windows '+config and found[0]['status']=='completed' and found[0]['conclusion']=='success' and found[0]['labels']==['windows-2025'] and binding['artifact']['name']=='physics-v2-Windows-'+config+'-raw' and
        binding['artifact']['expired'] is False and binding['artifact']['workflow_run']['id']==p['run_id'] and binding['artifact']['workflow_run']['head_sha']==p['source'] and raw_zip.stat().st_size==binding['artifact']['size_in_bytes'] and 'sha256:'+sha(raw_zip)==binding['artifact']['digest'],'Actual published source-bound Windows scenario bytes/job required')
    outer=output/'capture-outer';unpack(raw_zip,outer);folder=outer/'physics-v2-Windows'/config;index=load(folder/'diagnostic-raw-index.json');raw=folder/'diagnostic-raw.tar.gz'
    restored=load(outer/'current-windows-sdk/restoration.json')
    require(restored['compiled_source']==origin['source'] and restored['collector_source']==p['source'] and restored['actual_artifact']['id']==record['artifact']['id'] and restored['actual_artifact']['digest']==record['artifact']['digest'] and restored['runtime_files_sha256']==item['runtime_files_sha256'] and restored['tests']==item['tests'] and index['missing_guarded_paths']==[],'Actual capture must use the exact independently verified pristine new SDK and all its28unit receipts')
    require(sha(raw)==index['archive_sha256'] and raw.stat().st_size==index['archive_bytes'],'Exact whole published original raw bundle required');closure=inspect_archive(raw,index['files']);require(closure==index['closure'],'Every original logical raw member/type/length/hash required')
    prefix='out/physics-v2-Windows/'+config+'/';require(all(n.startswith(prefix) for n in index['files']),'Only original declared scenario evidence may materialize')
    with tarfile.open(raw,'r:gz') as tar:
        require(sum(m.size for m in tar.getmembers())<2*1024**3,'Bounded original Windows scenario evidence required')
        for m in tar.getmembers():
            require(m.isfile() and not m.mode&0o7000,'Original Windows raw regular files only');safe(m.name);dest=ROOT/m.name;require(not dest.exists() and dest.resolve()==dest,'Fresh original raw destination required');dest.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(m) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst,1024**2)
            require(sha(dest)==index['files'][m.name]['sha256'],'Actual original raw Windows member changed')
    actual=ROOT/'out/physics-v2-Windows'/config;collection=load(actual/'collection.json');require(collection['source']==p['source'] and collection['application_source']==origin['source'] and collection['frames']==60 and collection['fixed_step']==.25 and collection['pristine_sdk_unchanged'] is True and sha(actual/'ProductionCockpitDriver.dll')==collection['observer']['binary_sha256'],'Actual unchanged observer, new SDK/source and original scenario clock required')
    observer='Tests/Production/RemainingStock/Driver.cpp';body=subprocess.check_output(['git','show',origin['source']+':'+observer]);lf=body.replace(b'\r\n',b'\n')
    require(collection['observer']['source_sha256'] in {hashlib.sha256(body).hexdigest(),hashlib.sha256(lf).hexdigest(),hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest()} and hashlib.sha256(lf).hexdigest()==report['source_guard_sha256_lf'][observer] and collection['observer']['source_modified'] is False,'Exact original60frame observer under its declared Windows checkout line endings required')
    for key,case in collection['cases'].items():
        mode=key.split('-',1)[0];math=(actual/key/'math-profile.txt').read_text().strip();require(math in ('fma3','sse2') and (mode!='sse2' or math=='sse2'),'Actual original Windows math dispatch must match declared mode')
        require(case['process']['actual_pid']>0 and case['process']['actual_returncode']==0 and not case['process']['timed_out'],'Every actual normal terminal Windows process required')
        require(all(sha(actual/key/n)==h for n,h in case['files_sha256'].items()),'Every actual per-case raw byte must match the producer record')
    inspect_all_scenes();proof=load(actual/'independent-scene-inspection.json')
    atomic_json(output/'verification.json',dict(status='independently-verified-fresh-v2-Windows-four-scenes-both-math-modes-only',physics_version='assembly-contact-v2',configuration=config,compiled_source=origin['source'],capture_source=p['source'],actual_capture_processes=8,new_simulator_processes=0,original_sdk_complete_members=len(hashes),original_windows_unit_processes=28,actual_sdk_api_artifact=record['artifact'],actual_capture_api_artifact=binding['artifact'],complete_original_raw_closure=closure,scene_proof=proof,qualification_granted=False,phase6_complete=False))


if __name__=='__main__':main()
