#!/usr/bin/env python3
"""Independently decode fresh v2 build bytes; preserve actual original/failure APIs."""
import argparse,hashlib,importlib.util,json,os,shutil,stat,subprocess,sys,tarfile,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from contracts import require,sha,load,atomic_json
from restore_sdk import unpack,safe,REQUIRED_STEPS
from hosted_native_package import test_result


def api(role,profile):
    origin=load(HERE/'origins.json')[role];base=ROOT/'out/physics-v2-input'/role/profile
    record=load(base/'api.json');run=record['run'];a=record['artifact'];archive=base/'producer.zip'
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and record['physics_version']=='assembly-contact-v2' and
        run['id']==origin['run_id'] and run['head_sha']==origin['source'] and run['head_branch']==origin['branch'] and run['path']==origin['workflow'] and
        run['run_attempt']==1 and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False,'Exact explicit v2 API/source origin required')
    name='Rebuilt physics v2 native '+profile.replace('-',' ') if role=='native' else 'windows / Real Windows client '+profile+' x64'
    jobs=[j for j in record['jobs'] if j['name']==name];require(len(jobs)==1,'Unique actual build job required');job=jobs[0]
    require(job['id']==record['selected_job_id'] and job['run_id']==run['id'] and job['head_sha']==origin['source'] and job['status']=='completed' and job['conclusion']==('failure' if role=='native' else 'success') and
        job['labels']==(['ubuntu-24.04'] if role=='native' else ['windows-2025']),'Actual successful standard-runner selected job required; unrelated failures remain preserved')
    required=REQUIRED_STEPS if role=='windows' else ('Build all stock families, normal host and unchanged upstream unit bodies with sanitizers','Run every original native unit and complete source-matched Catch cases','Seal exact runtime, generated sources and actual test results without acceptance credit')
    for name in required:
        found=[s for s in job['steps'] if s['name']==name];conclusion='failure' if role=='native' and name!=required[0] else 'success'
        require(len(found)==1 and found[0]['status']=='completed' and found[0]['conclusion']==conclusion,'Every original actual build/test/retention conclusion must remain exact: '+name)
    require(a['name']==('physics-v2-native-'+profile if role=='native' else 'current-windows-sdk-'+profile) and a['expired'] is False and a['workflow_run']['id']==run['id'] and
        a['workflow_run']['head_sha']==origin['source'] and 0<a['size_in_bytes']<2*1024**3 and a['size_in_bytes']==archive.stat().st_size and a['digest']=='sha256:'+sha(archive),'Actual API archive bytes/source differ')
    return origin,base,record,archive,job


def original_sources(record,source):
    for name,h in record.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==h and sha_lf(ROOT/name)==h,'Actual compiled input differs from immutable owner: '+name)


def sha_lf(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def native(profile):
    origin,base,record,archive,job=api('native',profile);outer=base/'decoded';unpack(archive,outer)
    prefix='phase6-physics-v2-native/'+profile
    sealed_path=outer/(prefix+'/hosted-package.json');sealed=load(sealed_path);tar_path=outer/(prefix+'.tar.gz')
    require(sealed['source_commit']==origin['source'] and sealed['configuration']+'-'+sealed['math_profile']==profile and sealed['status']=='built-only-tests-failed-or-incomplete' and sealed['test_errors']=={'engine':'A failed or skipped unit cannot qualify the package'} and
        sealed['archive_sha256']==sha(tar_path) and sealed['archive_bytes']==tar_path.stat().st_size,'Exact fresh complete source-bound sanitized package required')
    expected=sealed['archive_members_sha256'];package=ROOT/'out/phase6-physics-v2-native'/profile;require(not package.exists(),'Fresh complete v2 runtime destination required')
    with tarfile.open(tar_path,'r:gz') as tar:
        members=tar.getmembers();names=[m.name for m in members]
        require(len(names)==len(set(n.casefold() for n in names))==len(expected) and set(names)==set(expected) and sum(m.size for m in members)<4*1024**3,'Complete bounded exact v2 package member roster required')
        for m in members:
            safe(m.name);p=ROOT/m.name
            require(m.isfile() and not m.mode&0o7000 and p.is_relative_to(package) and not p.exists() and p.resolve()==p,'Unsafe/colliding v2 package member')
            p.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(m) as incoming,p.open('xb') as sink:shutil.copyfileobj(incoming,sink,1024**2)
            p.chmod(m.mode&0o777);require(sha(p)==expected[m.name],'Retained v2 package member changed')
    build=load(package/'build.json');original_sources(build['source_sha256_lf']|build['dependency_sha256_lf'],origin['source'])
    require(sha(package/'build.json')==sealed['build_manifest_sha256'] and build['source_base']==origin['source'] and build['status']=='built' and build['physics_version']=='assembly-contact-v2' and
        build['instrumentation']=='address,undefined' and build['owning_sources_unchanged'] is True,'Actual corrected sanitized runtime build required')
    names=[t['name'] for t in load(package/'registered-unit-tests.json')['tests']];cases=ET.parse(package/'engine-tests.xml').getroot().findall('.//testcase')
    failures=[c for c in cases if any(c.find(k) is not None for k in ('failure','error','skipped'))]
    require(len(names)==len(set(names))==len(cases)==32 and {c.attrib['name'] for c in cases}==set(names) and len(failures)==1 and failures[0].attrib['name']=='Production.NativeCelestialEvidence' and failures[0].find('failure').attrib=={'message':'Timeout'},'Preserve exact31passed/one original evidence-verifier timeout; any other failure remains blocked')
    tests=dict(original_engine_passes=31,original_engine_timeout='Production.NativeCelestialEvidence',upstream=test_result(package/'upstream-registered-unit-tests.json',package/'upstream-tests.xml'))
    complete=load(package/'complete-unit-verification.json')
    require(tests['upstream']==sealed['tests']['upstream'] and tests['upstream']['executed_processes']==2 and complete['status']=='failed-or-incomplete-unqualified' and complete['failures']==[dict(component='engine',error='Original unit/discovery command failed: engine-tests')] and set(complete['fresh_upstream_results'])=={'Lua.Interpreter','Collision.CollisionCore'},'All original actual upstream/discovered cases and the prior timeout must remain exact')
    proof=dict(status='restored-fresh-source-bound-v2-native-with-one-unresolved-original-test',physics_version='assembly-contact-v2',compiled_source=origin['source'],profile=profile,actual_job_id=job['id'],api_artifact=record['artifact'],complete_package_members=len(expected),build_manifest_sha256=sha(package/'build.json'),tests=tests,qualification_granted=False)
    atomic_json(base/'restoration.json',proof)


def windows(config):
    from pathlib import PureWindowsPath
    origin,base,record,archive,job=api('windows',config);output=ROOT/'out/current-windows-sdk';require(not output.exists(),'Fresh v2 SDK output required');output.mkdir(parents=True)
    payload=output/'source-artifact';outer=unpack(archive,payload);report=load(payload/'current-application.json');item=report['configurations'][config]
    require(report['protocol']=='phase6-github-current-application-v1' and report['status']=='built-and-client-tested-awaiting-complete-stock-qualification' and report['source_commit']==origin['source'] and report['owning_sources_unchanged'] is True and item['status']=='built' and
        report['github']['run_id']==origin['run_id'] and report['github']['run_attempt']==1 and report['github']['source']==origin['source'] and report['github']['image_os'] in ('win25','win25-vs2026') and
        report['phase6_complete'] is False and report['native_admission_qualified'] is False,'Actual closed v2 SDK build receipt required')
    runtime=output/'runtime';require(PureWindowsPath(item['runtime'])==PureWindowsPath(str(runtime)),'Keep original recorded absolute runtime path')
    inner=payload/'runtime.zip';require(sha(inner)==report['runtime_archive_sha256'] and inner.stat().st_size==report['runtime_archive_bytes'],'Exact sealed SDK inner bytes required')
    unpack(inner,runtime,item['runtime_files_sha256']);owner=ROOT/'application-source'
    require(subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],text=True).strip()==origin['source'],'Separate actual v2 compiled source owner required')
    helper=owner/'Tests/Production/CurrentWindows/retain_hosted_sdk.py'
    spec=importlib.util.spec_from_file_location('v2_unchanged_sdk_reader',helper);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    require(helper.read_bytes().replace(b'\r\n',b'\n')==subprocess.check_output(['git','-C',str(owner),'show',origin['source']+':Tests/Production/CurrentWindows/retain_hosted_sdk.py']).replace(b'\r\n',b'\n'),'Unchanged actual SDK reader required')
    require(reader.source_files(origin['source'])==report['source_guard_sha256_lf'] and reader.runtime_files(runtime,origin['source'])==item['runtime_files_sha256'] and sha(runtime/'test-runtime.json')==item['sdk_manifest_sha256'],'All original SDK/source guards required for new version')
    tests=reader.unit_result(load(payload/'registered-tests.json'),payload/'runtime-ctest.xml')
    require(tests==item['tests'] and tests['executed_processes']==28 and sha(payload/'build-inputs.json')==item['build_inputs_sha256'],'All original passed Windows units/compiler inputs required')
    require(all(sha(payload/n)==h for n,h in outer.items()),'API-bound v2 SDK evidence changed')
    atomic_json(output/'restoration.json',dict(protocol='phase6-versioned-physics-v2-sdk-restoration',compiled_source=origin['source'],collector_source=os.environ['GITHUB_SHA'],configuration=config,runtime=str(runtime),source_owner=str(owner),source_guard_sha256_lf=report['source_guard_sha256_lf'],runtime_files_sha256=item['runtime_files_sha256'],tests=tests,actual_job_id=job['id'],actual_artifact=record['artifact'],qualification_granted=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('role',choices=('native','windows'));p.add_argument('profile');a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true','Server-side artifact verification only')
    (native if a.role=='native' else windows)(a.profile)


if __name__=='__main__':main()
