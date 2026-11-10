#!/usr/bin/env python3
"""Read actual failed fixture/engine ABI bytes and the standard runner preprocessor; no simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
import rejection_input_bundle as bundle

SOURCE='6293d10c96be28b7900ea98137e46b8a865875e6'
RUN=42876473444
JOB=130041486308
ARTIFACT=13794535514
SIZE=737683034
DIGEST='24960e0e6abdf93ab368a22c1010c22656de394f17645d95fb7ed782f420f96c'
PROFILE='Debug-automatic'
CPP=re.compile(rb'(?<![^\x00])(gcc-[^\x00:]{1,128}:libstdc\+\+-[0-9]{8}-abi-[01]-(?:normal|debug)-gxx-[0-9]+:[0-9]+L)\x00')


def abi_tokens(body):
    require(body[:4]==b'\x7fELF','Actual preserved ELF input required')
    return sorted({m[1].decode() for m in CPP.finditer(body)})


def validate(api):
    run=api['run'];a=api['artifact'];jobs=api['jobs']
    require(api['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']=='qualification/native-class-rejections-v6' and run['path']=='.github/workflows/phase6-native-class-rejections-official-pool-uri.yml' and run['run_attempt']==1,'Exact original failed source/run must be preserved')
    require(len(jobs)==5 and len({j['id'] for j in jobs})==5 and all(j['run_id']==RUN and j['head_sha']==SOURCE and j['labels']==['ubuntu-24.04'] for j in jobs),'Complete actual original standard hosted job roster required')
    selected=next(j for j in jobs if j['id']==JOB);require(selected['name']=='Original normal host class and loader rejection controls '+PROFILE and selected['status']=='completed' and selected['conclusion']=='failure','Only actual completed original failure may be inspected')
    require(a['id']==ARTIFACT and a['name']=='original-class-normal-host-rejection-controls-'+PROFILE and a['size_in_bytes']==SIZE and a['digest']=='sha256:'+DIGEST and a['expired'] is False and a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==SOURCE,'Exact original failed raw artifact required')


def host_macros(header,output):
    argv=['c++','-std=c++17','-DORBITER_NATIVE_BUILD_CONFIGURATION="Debug"','-I'+str(ROOT/'Src/Orbiter'),'-I'+str(header.parent),'-dM','-E','-x','c++','-']
    result=subprocess.run(argv,input='#include "Production/NativeAbi.h"\n',text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60);(output/'host-preprocessor-macros.log').write_text(result.stdout);(output/'host-preprocessor-stderr.log').write_text(result.stderr);require(result.returncode==0,'Actual runner header preprocessor must complete')
    values={}
    for line in result.stdout.splitlines():
        if line.startswith('#define '):
            parts=line[8:].split(' ',1);values[parts[0]]=parts[1] if len(parts)>1 else ''
    require('__clang__' not in values and all(n in values for n in ('__VERSION__','__GLIBCXX__','_GLIBCXX_USE_CXX11_ABI','__GXX_ABI_VERSION','__cplusplus')),'Actual GCC/libstdc++ macro identity required')
    selected={k:values[k] for k in ('__VERSION__','__GLIBCXX__','_GLIBCXX_USE_CXX11_ABI','__GXX_ABI_VERSION','__cplusplus')};selected['_GLIBCXX_DEBUG_present']='_GLIBCXX_DEBUG' in values
    token='gcc-'+json.loads(values['__VERSION__'])+':libstdc++-'+values['__GLIBCXX__']+'-abi-'+values['_GLIBCXX_USE_CXX11_ABI']+('-debug' if '_GLIBCXX_DEBUG' in values else '-normal')+'-gxx-'+values['__GXX_ABI_VERSION']+':'+values['__cplusplus']
    return dict(argv=argv,actual_returncode=0,macro_values=selected,actual_cpp_abi=token,preprocessor_sha256=sha(output/'host-preprocessor-macros.log'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('api','archive','output'):p.add_argument('--'+n,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT and not a.output.exists(),'Fresh actual standard hosted ABI inspection required')
    a.output.mkdir(parents=True);api=load(a.api);validate(api);require(a.archive.stat().st_size==SIZE and sha(a.archive)==DIGEST,'Actual failed raw archive bytes differ')
    prefix='out/hosted-native-class-rejections/'+PROFILE+'/';raw=a.output/'retained-raw.tar.gz';seen=set();outer={}
    with zipfile.ZipFile(a.archive) as z:
        for item in z.infolist():
            name=item.filename;bundle.safe(name);require(name.casefold() not in seen and not __import__('stat').S_ISLNK(item.external_attr>>16),'Safe unique original failed outer member required');seen.add(name.casefold())
        for name in ('raw-index.json','collection.json','original-SDK-header-restoration.json','original-fixture-SDK.json'):
            outer[name]=json.loads(z.read(prefix+name));atomic_json(a.output/name,outer[name])
        with z.open(prefix+'raw-original-inputs.tar.gz') as src,raw.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
    for name,digest in outer['original-SDK-header-restoration.json']['original_sources_sha256'].items():require(sha(name)==digest,'Actual original SDK/ABI template source must remain unchanged during host preprocessing')
    index=outer['raw-index.json'];require(raw.stat().st_size==index['archive_bytes'] and sha(raw)==index['archive_sha256'] and bundle.inspect_archive(raw,index['files'])==index['closure'],'Every original partial logical member and raw archive hash must remain exact')
    before='out/phase6-hosted-native/'+PROFILE+'/engine/';cap='out/native-class-rejections/'+PROFILE+'/'
    wanted={before+'liborbiter_production_boundary.so',before+'NativeModules/Vessel/HST.so',before+'CMakeCache.txt',before+'native-sdk/OrbiterNativeBuild.h','out/phase6-hosted-native/'+PROFILE+'/build.json',cap+'rejections.json',cap+'HST-metadata-6/console.log',cap+'HST-metadata-6/process-receipt.json',cap+'HST-metadata-6/graphics-lifecycle.json',cap+'HST-metadata-6/invocation.json'}
    wanted.update(cap+'fixtures/'+kind+str(i)+suffix for i in range(7) for kind,suffix in (('metadata-','.so'),('command-','.json')))
    requested=set(wanted)
    with tarfile.open(raw) as tar:headers={m.name:m for m in tar}
    queue=list(wanted)
    while queue:
        name=queue.pop();require(name in headers,'Every requested actual original witness must exist')
        entry=headers[name]
        if entry.islnk() and entry.linkname not in wanted:
            bundle.safe(entry.linkname);require(entry.linkname in index['files'],'Exact original hardlink target required');wanted.add(entry.linkname);queue.append(entry.linkname)
    selected={};pending={}
    with tarfile.open(raw) as tar:
        for item in tar:
            if item.name not in wanted:continue
            if item.islnk():pending[item.name]=item.linkname;continue
            require(item.isfile() and item.size<128*1024**2,'Bounded actual binary/header/log witness required');body=tar.extractfile(item).read();require(len(body)==index['files'][item.name]['bytes'] and hashlib.sha256(body).hexdigest()==index['files'][item.name]['sha256'],'Actual retained witness differs');selected[item.name]=body
    while pending:
        progress=False
        for name,target in list(pending.items()):
            if target in selected:selected[name]=selected[target];del pending[name];progress=True
        require(progress,'Every selected original hardlink target must be retained')
    require(set(selected)==wanted,'Every actual original ABI, header and command witness required')
    binary={n:dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),actual_NUL_bounded_CPP_ABI_tokens=abi_tokens(body)) for n,body in selected.items() if n in requested and n.endswith('.so')}
    capture=json.loads(selected[cap+'rejections.json']);require(capture['status']=='failed' and capture['producer_commit']==SOURCE and capture['failures'] and list(capture['failures'])==['HST-metadata-6'],'Exact original failed partial capture must remain failed')
    header=a.output/'sdk/OrbiterNativeBuild.h';header.parent.mkdir();header.write_bytes(selected[before+'native-sdk/OrbiterNativeBuild.h']);host=host_macros(header,a.output)
    commands={str(i):json.loads(selected[cap+'fixtures/command-'+str(i)+'.json']) for i in range(7)}
    for i,argv in commands.items():require('-std=c++17' in argv and '-DPHASE6_REJECTED_METADATA='+i in argv and str(ROOT/'Tests/Production/RemainingVessels/RejectedModule.cpp') in argv,'Actual unchanged original fixture compiler command required')
    engine=binary[before+'liborbiter_production_boundary.so']['actual_NUL_bounded_CPP_ABI_tokens'];fixture=binary[cap+'fixtures/metadata-6.so']['actual_NUL_bounded_CPP_ABI_tokens'];require(len(engine)==len(fixture)==1,'Unambiguous actual engine and lifecycle-fixture ABI token required')
    console=selected[cap+'HST-metadata-6/console.log'].decode(errors='replace');(a.output/'failed-control-console.log').write_bytes(selected[cap+'HST-metadata-6/console.log']);cache=selected[before+'CMakeCache.txt'].decode();(a.output/'original-CMakeCache.txt').write_text(cache)
    for name in ('build.json',):atomic_json(a.output/name,json.loads(selected['out/phase6-hosted-native/'+PROFILE+'/'+name]))
    atomic_json(a.output/'inspection.json',dict(protocol='phase6-read-only-actual-original-rejection-CPP-ABI-v1',status='inspected-original-failed-fixture-and-engine-identities-only',auditor_source=os.environ['GITHUB_SHA'],original_source=SOURCE,original_run_id=RUN,original_job_id=JOB,original_artifact=api['artifact'],original_raw_bundle_sha256=sha(raw),all_original_partial_members_verified=len(index['files']),original_failed_capture_status=capture['status'],original_completed_control_count=len(capture['controls']),original_requested_control_count=len(capture['controls_requested']),original_failed_control='HST-metadata-6',original_actual_failed_control_receipt=json.loads(selected[cap+'HST-metadata-6/process-receipt.json']),original_actual_failed_control_lifecycle=json.loads(selected[cap+'HST-metadata-6/graphics-lifecycle.json']),original_fixture_commands=commands,binary_witnesses=binary,engine_CPP_ABI=engine[0],failed_fixture_CPP_ABI=fixture[0],fixture_rejected_for_CPP_ABI=('Native module C++ toolchain/ABI mismatch' in console),original_fixture_initializer_called=('REJECTION_FIXTURE_INITIALIZE_CALLED' in console),host_preprocessor=host,host_compiler_ABI_matches_engine=(host['actual_cpp_abi']==engine[0]),engine_or_fixture_loaded=False,actual_new_simulator_processes=0,qualification_granted=False,phase6_complete=False,hands_on_ready=False))
    raw.unlink();print('Inspected actual original engine/fixture/header identities; original failure retained')


if __name__=='__main__':main()
