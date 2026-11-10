#!/usr/bin/env python3
"""Execute unchanged original fixture argv with the actual matching hosted compiler outside runtime container."""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from contracts import ROOT,PROFILES,require,load,sha,atomic_json
from processes import OwnedProcess
from inspect_rejection_cpp_abi import abi_tokens,host_macros

FIXTURE='Tests/Production/RemainingVessels/RejectedModule.cpp'
FIXTURE_SHA='724212d8c9ac9d9e7edb9190361cb21ee1d949fa4fd0a9dafaf8d9eb41a1b5a1'
MAX_MESSAGE=2*1024**2


def expected_argv(profile,index,root=ROOT):
    require(profile in PROFILES and type(index) is int and 0<=index<7,'One exact original profile and invalid-metadata fixture required')
    build=root/'out/phase6-hosted-native'/profile/'engine';configuration=profile.split('-')[0]
    return ['/usr/bin/c++','-std=c++17','-shared','-fPIC','-Wl,--no-undefined','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DORBITER_NATIVE_BUILD_CONFIGURATION="'+configuration+'"','-DPHASE6_REJECTED_METADATA='+str(index),'-I'+str(root/'Src/Orbiter'),'-I'+str(build/'native-sdk'),str(root/FIXTURE),'-o',str(root/'out/native-class-rejections'/profile/'fixtures'/('metadata-'+str(index)+'.so'))]


def validate_request(request,profile,completed,root=ROOT):
    require(type(request) is dict and set(request)=={'profile','index','argv'} and request['profile']==profile and request['argv']==expected_argv(profile,request['index'],root) and request['index'] not in completed and request['index']==len(completed),'Only one actual unchanged original fixture compiler command per index may execute')
    return request['index']


def receive(stream):
    blocks=[];length=0
    while True:
        b=stream.recv(65536)
        if not b:break
        length+=len(b);require(length<=MAX_MESSAGE,'Bounded compiler bridge request/response required');blocks.append(b)
    return json.loads(b''.join(blocks))


def send(stream,value):
    body=json.dumps(value,allow_nan=False).encode();require(len(body)<=MAX_MESSAGE,'Bounded actual compiler receipt required');stream.sendall(body);stream.shutdown(socket.SHUT_WR)


def client():
    profile=os.environ['PROFILE'];argv=['/usr/bin/c++',*sys.argv[1:]];ids=[i for i in range(7) if argv==expected_argv(profile,i)];require(len(ids)==1,'Unchanged original fixture compile argv required by declared bridge')
    base=ROOT/'out/rejection-fixture-compiler'/profile
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
        stream.settimeout(240);stream.connect(str((base/'bridge.sock').relative_to(ROOT)));send(stream,dict(profile=profile,index=ids[0],argv=argv));response=receive(stream)
    require(response['index']==ids[0] and type(response['actual_returncode']) is int,'Actual matching original compiler process receipt required')
    sys.stdout.buffer.write(base64.b64decode(response['output_base64'],validate=True));sys.stdout.buffer.flush()
    if response['actual_returncode']==0:require(sha(argv[-1])==response['output_sha256'],'Actual newly compiled fixture body differs from hosted compiler receipt')
    return response['actual_returncode']


def serve(profile):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and Path.cwd().resolve()==ROOT,'Actual standard GitHub Ubuntu host compiler required; no local service')
    folder=ROOT/'out/rejection-fixture-compiler'/profile;require(not folder.exists(),'Fresh actual compiler bridge receipt directory required');folder.mkdir(parents=True)
    compiler=Path('/usr/bin/c++').resolve();require(compiler.is_file() and not compiler.is_relative_to(ROOT),'Actual installed standard-runner compiler required')
    build=ROOT/'out/phase6-hosted-native'/profile/'engine';engine=abi_tokens((build/'liborbiter_production_boundary.so').read_bytes());require(len(engine)==1,'One actual retained engine compiler ABI required')
    require(sha(ROOT/FIXTURE)==FIXTURE_SHA,'Unchanged original seven-fixture source required')
    report=dict(protocol='phase6-original-fixture-host-compiler-bridge-v1',status='waiting-for-original-commands',profile=profile,source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),original_compiler_path='/usr/bin/c++',actual_host_compiler=str(compiler),actual_host_compiler_sha256=sha(compiler),actual_engine_CPP_ABI=engine[0],original_fixture_source_sha256=FIXTURE_SHA,requests=[],new_simulator_processes=0,bridge_source_sha256=sha(Path(__file__)),compiler_version_or_ABI_macros_overridden=False,original_fixture_or_collector_argv_changed=False,original_488_installed_package_versions_unchanged=True,one_container_compiler_alias_explicitly_overlaid=True,runtime_shared_library_provider_bytes_unchanged=True,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(folder/'compiler-bridge.json',report)
    completed=set();report['actual_host_service_pid']=os.getpid();(folder/'server.pid').write_text(str(os.getpid())+'\n');save()
    endpoint=folder/'bridge.sock'
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
            server.bind(str(endpoint.relative_to(ROOT)));endpoint.chmod(0o600);server.listen(1);server.settimeout(30)
            (folder/'ready').write_text('actual-host-compiler-service-ready\n')
            while len(completed)<7:
                try:connection,_=server.accept()
                except socket.timeout:continue
                with connection:
                    connection.settimeout(240);request=receive(connection);index=validate_request(request,profile,completed);item=dict(index=index,original_requested_argv=request['argv'],actual_host_argv=request['argv'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['requests'].append(item);save()
                    try:
                        header=build/'native-sdk/OrbiterNativeBuild.h';require(header.is_file() and sha(ROOT/FIXTURE)==FIXTURE_SHA and sha(compiler)==report['actual_host_compiler_sha256'],'Original fixture, real compiler and derived SDK header must remain exact')
                        if 'host_preprocessor' not in report:
                            report['host_preprocessor']=host_macros(header,folder);require(report['host_preprocessor']['actual_cpp_abi']==engine[0],'Actual unmodified hosted compiler/header ABI must equal retained engine')
                            report['native_sdk_header_sha256']=sha(header);save()
                        require(sha(header)==report['native_sdk_header_sha256'],'Actual SDK header changed between original commands')
                        output=Path(request['argv'][-1]);require(not output.exists() and not output.is_symlink() and output.parent.is_dir() and output.parent.resolve()==output.parent,'Fresh original fixture output required')
                        log=folder/('compile-'+str(index)+'.log')
                        with log.open('wb') as stream:
                            owned=OwnedProcess(request['argv'],cwd=ROOT,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'},stdout=stream,stderr=subprocess.STDOUT)
                            try:owned.process.wait(timeout=180)
                            finally:receipt=owned.cancel()
                        atomic_json(folder/('compile-'+str(index)+'-process.json'),receipt);code=receipt['actual_returncode'];require(receipt['terminal'] is True and receipt['cancelled'] is False and code==0,'Actual original hosted fixture compiler must complete successfully')
                        body=output.read_bytes();tokens=abi_tokens(body)
                        require((tokens==[] and b'incompatible-cpp-abi\x00' in body) if index==1 else tokens==engine,'Actual fixture compiler ABI must equal engine except the unchanged deliberate mismatch fixture')
                        require(sha(ROOT/FIXTURE)==FIXTURE_SHA and sha(header)==report['native_sdk_header_sha256'] and sha(compiler)==report['actual_host_compiler_sha256'],'Original actual compiler/source/header changed during fixture compilation')
                        item.update(actual_returncode=code,actual_compiler_process_receipt_sha256=sha(folder/('compile-'+str(index)+'-process.json')),output_sha256=sha(output),actual_CPP_ABI_tokens=tokens,log_sha256=sha(log),actual_compiler_pid=receipt['actual_collector_pid']);completed.add(index);save()
                        send(connection,dict(index=index,actual_returncode=code,output_base64=base64.b64encode(log.read_bytes()).decode(),output_sha256=sha(output)))
                    except BaseException as error:
                        item.update(status='failed',error=str(error));report.update(status='failed-unqualified',error=str(error));save();send(connection,dict(index=index,actual_returncode=1,output_base64=base64.b64encode((str(error)+'\n').encode()).decode(),output_sha256=None));raise
            report['status']='all-seven-original-fixture-compiler-processes-completed';save()
    finally:endpoint.unlink(missing_ok=True);save()


def install(profile):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and os.geteuid()==0,'Actual hosted runtime container adapter only')
    folder=ROOT/'out/rejection-fixture-compiler'/profile;require((folder/'ready').read_text()=='actual-host-compiler-service-ready\n' and (folder/'bridge.sock').is_socket(),'Actual ready same-workspace hosted compiler bridge required')
    destination=Path('/usr/bin/c++');require(destination.is_symlink(),'Original container compiler alias must be retained explicitly')
    before=dict(original_alias_target=os.readlink(destination),original_resolved_compiler=str(destination.resolve()),original_resolved_compiler_sha256=sha(destination.resolve()))
    body=b'#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\nsys.path.insert(0,str(Path.cwd()/"Tests/Production/Closeout"))\nfrom rejection_fixture_compiler_bridge import client\nraise SystemExit(client())\n'
    wrapper=folder/'container-compiler-adapter';wrapper.write_bytes(body);wrapper.chmod(0o755)
    destination.unlink();destination.symlink_to(wrapper)
    atomic_json(folder/'container-adapter.json',dict(protocol='phase6-explicit-container-compiler-alias-to-actual-host-v1',profile=profile,**before,declared_adapter=str(wrapper),adapter_sha256=sha(wrapper),original_compiler_request_path=str(destination),actual_compilation_runs_on_standard_Ubuntu_host=True,original_installed_runtime_package_inventory_unchanged=True,no_version_or_ABI_macro_spoofing=True,no_cached_or_prebuilt_fixture_outputs=True,phase6_complete=False))



def verify(profile):
    folder=ROOT/'out/rejection-fixture-compiler'/profile;report=load(folder/'compiler-bridge.json')
    require(report['source']==os.environ['GITHUB_SHA'] and report['profile']==profile and report['status']=='all-seven-original-fixture-compiler-processes-completed' and report['host_preprocessor']['actual_cpp_abi']==report['actual_engine_CPP_ABI'] and report['compiler_version_or_ABI_macros_overridden'] is False and report['original_fixture_or_collector_argv_changed'] is False and report['original_488_installed_package_versions_unchanged'] is True and report['one_container_compiler_alias_explicitly_overlaid'] is True,'Exact explicitly declared actual host compiler scope required')
    require(len(report['requests'])==7 and [r['index'] for r in report['requests']]==list(range(7)),'All seven actual original fixture compiler processes required')
    pids=set()
    for r in report['requests']:
        i=r['index'];receipt=load(folder/('compile-'+str(i)+'-process.json'));actual=[v for v in receipt['owned_process_identities'] if v['pid']==receipt['actual_collector_pid']]
        require(r['original_requested_argv']==r['actual_host_argv']==expected_argv(profile,i) and r['actual_returncode']==0 and r['actual_compiler_pid']==receipt['actual_collector_pid'] and len(actual)==1 and actual[0]['start_ticks']>0 and actual[0]['argv']==expected_argv(profile,i) and receipt['terminal'] is True and receipt['cancelled'] is False and receipt['actual_returncode']==0 and sha(folder/('compile-'+str(i)+'-process.json'))==r['actual_compiler_process_receipt_sha256'] and sha(folder/('compile-'+str(i)+'.log'))==r['log_sha256'] and sha(r['actual_host_argv'][-1])==r['output_sha256'],'Actual original compiler PID/start/argv/output/log receipt differs')
        token=(actual[0]['pid'],actual[0]['start_ticks']);require(token not in pids,'A compiler process cannot supply multiple original fixtures');pids.add(token)
    require(sha(ROOT/FIXTURE)==FIXTURE_SHA and sha(ROOT/'out/phase6-hosted-native'/profile/'engine/native-sdk/OrbiterNativeBuild.h')==report['native_sdk_header_sha256'],'Original fixture source and actual SDK input must stay unchanged')
    print('Verified seven distinct actual original fixture compilations with matching host ABI; runtime qualification remains separate')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('serve','install','verify'));p.add_argument('--profile',choices=PROFILES,required=True);a=p.parse_args()
    if a.mode=='serve':serve(a.profile)
    elif a.mode=='install':install(a.profile)
    else:verify(a.profile)
