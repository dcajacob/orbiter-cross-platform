#!/usr/bin/env python3
"""Inspect exact retained SDK strings and ELF exports on hosted runners; never execute a simulator."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
from recheck_native_discovery import validate_api,safe,PRODUCER


def tokens(body,pattern):
    return sorted({(m[1].decode(),m[2].decode()) for m in re.finditer(pattern,body)})


def inspect(api,archive,output):
    require(not output.exists(),'Fresh separate SDK inspection output required');output.mkdir(parents=True)
    profile='Debug-sse2';validate_api(api,profile);artifact=api['artifact']
    require(artifact['id']==13633311229 and artifact['size_in_bytes']==82507652 and artifact['digest']=='sha256:11f150fffd8b02bf6f9d438a4aff9b37a203c2d9db4eea8ae2905ff078d2898f' and archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],'Exact unchanged original compiled Debug-sse2 source archive required')
    with zipfile.ZipFile(archive) as z:
        seen=set()
        for item in z.infolist():
            name=safe(item.filename);require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16),'Exact safe original ZIP member required');seen.add(name.casefold())
        sealed=json.loads(z.read(profile+'/hosted-package.json'));packed=output/'original-package.tar.gz'
        with z.open(profile+'.tar.gz') as source,packed.open('xb') as target:shutil.copyfileobj(source,target,1024*1024)
    require(sealed['status']=='built-only-tests-failed-or-incomplete' and sealed['source_commit']==PRODUCER and sealed['archive_bytes']==packed.stat().st_size and sealed['archive_sha256']==sha(packed),'Exact preserved failed producer manifest and tar bytes required')
    expected=sealed['archive_members_sha256'];witnesses={};seen=set();build=None;cache=None
    prefix='out/phase6-hosted-native/'+profile+'/';strict=rb'(?<![^\x00])([0-9a-f]{64}):(Debug|Release)\x00';embedded=rb'([0-9a-f]{64}):(Debug|Release)\x00'
    with tarfile.open(packed,'r:gz') as tar:
        require(sum(m.size for m in tar.getmembers())<4*1024**3,'Bounded original native package required')
        for item in tar:
            name=safe(item.name);require(item.isfile() and not item.mode&0o7000 and name.startswith(prefix) and name in expected and name not in seen,'Exact safe complete original tar member required');seen.add(name)
            stream=tar.extractfile(item);h=hashlib.sha256();length=0;body=None
            target=(name==prefix+'engine/liborbiter_production_boundary.so' or ('/engine/NativeModules/' in name and name.endswith('.so')))
            wanted=target or name in (prefix+'build.json',prefix+'engine/CMakeCache.txt')
            chunks=[] if wanted else None
            for block in iter(lambda:stream.read(1024*1024),b''):
                h.update(block);length+=len(block)
                if wanted:chunks.append(block)
            require(length==item.size and h.hexdigest()==expected[name],'Original retained member digest differs: '+name)
            if wanted:body=b''.join(chunks)
            if name==prefix+'build.json':build=json.loads(body)
            elif name==prefix+'engine/CMakeCache.txt':cache=body.decode()
            if target:
                binary=output/'exact-current-ELF.so';require(not binary.exists() and body[:4]==b'\x7fELF','Fresh exact original ELF witness required');binary.write_bytes(body)
                command=['nm','-D','--defined-only',str(binary)];result=subprocess.run(command,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                exports=[line.split()[-1] for line in result.stdout.splitlines() if line.split()];sdk=tokens(body,embedded)
                witnesses[name]=dict(sha256=h.hexdigest(),bytes=length,strict_NUL_bounded_SDK_tokens=tokens(body,strict),embedded_terminated_SDK_tokens=sdk,exported_OrbiterNativeQuery=('OrbiterNativeQuery' in exports),SDK_related_exports=sorted(v for v in exports if 'OrbiterNative' in v or 'SdkBuild' in v),SDK_token_contexts=[dict(token=base+':'+configuration,contexts=[body[max(0,m.start()-24):min(len(body),m.end()+16)].hex() for m in re.finditer(re.escape((base+':'+configuration).encode()+b'\x00'),body)][:6]) for base,configuration in sdk],ELF_export_inspection_argv=command,actual_returncode=result.returncode)
                binary.unlink()
    require(seen==set(expected) and build and cache and build['source_base']==PRODUCER and build['runtime_files_sha256'][prefix+'engine/CMakeCache.txt']==hashlib.sha256(cache.encode()).hexdigest(),'Exact complete original member and guarded cache closure required')
    for name,v in witnesses.items():require(build['runtime_files_sha256'][name]==v['sha256'],'ELF witness must match original complete runtime manifest')
    report=dict(protocol='phase6-read-only-retained-original-SDK-witness-inspection-v1',status='inspected-original-bytes-only-not-qualified',collector_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),compiled_runtime_source=PRODUCER,source_artifact_id=artifact['id'],source_artifact_sha256=sha(archive),source_archive_members_verified=len(seen),original_generated_SDK_header_member_present=(prefix+'engine/native-sdk/OrbiterNativeBuild.h' in seen),witnesses=witnesses,SDK_identity_scanner_or_acceptance_modified=False,new_simulator_processes=0,ELF_modules_executed=False,phase6_complete=False,hands_on_ready=False)
    atomic_json(output/'inspection.json',report);packed.unlink();return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('api','archive','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();require(__import__('os').environ.get('GITHUB_ACTIONS')=='true' and __import__('os').environ.get('RUNNER_OS')=='Linux','Read-only binary inspection runs only on the standard hosted Linux runner')
    report=inspect(load(a.api),a.archive,a.output)
    print(json.dumps(report,indent=2))
