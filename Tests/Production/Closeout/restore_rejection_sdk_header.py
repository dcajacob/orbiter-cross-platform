"""Reconstruct an omitted SDK header from the unchanged template and retained binary SDK identities."""
import hashlib
from pathlib import Path
import re
import subprocess
from contracts import ROOT,PROFILES,require,load,sha,atomic_json
COMPILED='ccc02c8a34bd1f227624d8778a141e8736ae8111'
SOURCES=('Src/Orbiter/Production/NativeBuild.h.in','Src/Orbiter/Production/NativeAbi.h','Src/Orbiter/Production/NativeModule.cpp','Src/Orbiter/Production/CMakeLists.txt')


def source_guards(root):
    result={}
    for name in SOURCES:
        body=(root/name).read_bytes()
        require(body==subprocess.check_output(['git','-C',str(root),'show',COMPILED+':'+name]),'Exact original SDK template/token/loader source required: '+name)
        result[str(root/name)]=hashlib.sha256(body).hexdigest()
    return result


def binary_sdk_base(path,configuration):
    require(configuration in ('Debug','Release'),'Exact original build configuration required')
    tokens=set();tail=b''
    with Path(path).open('rb') as stream:
        require(stream.read(4)==b'\x7fELF','Actual retained ELF module required');stream.seek(0)
        for block in iter(lambda:stream.read(1024*1024),b''):
            body=tail+block
            tokens.update((m[1].decode(),m[2].decode()) for m in re.finditer(rb'(?<![^\x00])([0-9a-f]{64}):(Debug|Release)\x00',body))
            tail=body[-96:]
    require(len(tokens)==1,'One unambiguous original SDK identity per retained binary required')
    base,actual=next(iter(tokens));require(actual==configuration,'Retained binary SDK build configuration differs');return base


def header_bytes(template,base,cockpit):
    require(re.fullmatch('[0-9a-f]{64}',base) and cockpit=='ON','Exact compiled SDK token and original enabled cockpit required')
    before=b'@ORBITER_NATIVE_BUILD_BASE@';define=b'#cmakedefine01 ORBITER_BUILD_NATIVE_COCKPIT'
    require(template.count(before)==template.count(define)==1,'Original configure_file template shape differs')
    body=template.replace(before,base.encode()).replace(define,b'#define ORBITER_BUILD_NATIVE_COCKPIT 1')
    require(b'@' not in body and b'#cmakedefine' not in body,'No unresolved original SDK template field permitted');return body


def restore(profile,build_record,output,root=ROOT):
    root=Path(root).resolve();build_record=Path(build_record);output=Path(output)
    require(profile in PROFILES and not output.exists(),'Fresh source-bound exact SDK restoration required')
    build=root/'out/phase6-hosted-native'/profile/'engine';require(build_record==build.parent/'build.json','Exact retained compiled package record required')
    record=load(build_record);require(record['status']=='built' and record['source_base']==COMPILED and record['owning_sources_unchanged'] is True and record['instrumentation']=='address,undefined' and record['configuration']+'-'+record['math_profile']==profile,'Original complete unchanged sanitized build identity required')
    sources=source_guards(root);runtime=record['runtime_files_sha256'];cache=build/'CMakeCache.txt';boundary=build/'liborbiter_production_boundary.so'
    modules=sorted((build/'NativeModules').rglob('*.so'));require(modules and any(p.name=='HST.so' for p in modules),'Actual original stock SDK modules required')
    paths=[cache,boundary,*modules];guards={}
    for path in paths:
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(build),'Original SDK witness must remain within the declared retained build')
        name=path.relative_to(root).as_posix();require(name in runtime and sha(path)==runtime[name],'Exact retained source-bound SDK witness bytes required: '+name);guards[str(path)]=runtime[name]
    values=dict(line.split('=',1) for line in cache.read_text().splitlines() if '=' in line and not line.startswith(('#','//')))
    require(values['CMAKE_BUILD_TYPE:STRING']==record['configuration'] and values['ORBITER_BUILD_NATIVE_COCKPIT:BOOL']=='ON' and values['ORBITER_MATH_FORCE_SSE2:BOOL']==('ON' if record['math_profile']=='sse2' else 'OFF'),'Original compiled cockpit/configuration/math cache differs')
    observed={str(path):binary_sdk_base(path,record['configuration']) for path in [boundary,*modules]}
    require(len(set(observed.values()))==1,'Every unchanged boundary and native module must declare the identical SDK build')
    base=next(iter(observed.values()));body=header_bytes((root/SOURCES[0]).read_bytes(),base,values['ORBITER_BUILD_NATIVE_COCKPIT:BOOL'])
    header=build/'native-sdk/OrbiterNativeBuild.h';require(not header.parent.is_symlink() and not header.is_symlink(),'SDK destination may not redirect original inputs')
    existed=header.exists()
    if existed:require(header.is_file() and header.read_bytes()==body,'Existing SDK input differs; never overwrite it')
    else:
        header.parent.mkdir(parents=True,exist_ok=True)
        with header.open('xb') as stream:stream.write(body)
        header.chmod(0o644)
    require(all(sha(p)==v for p,v in {**sources,**guards}.items()),'Original SDK source, cache or compiled witness changed during restoration')
    report=dict(protocol='phase6-reconstructed-omitted-original-SDK-header-v1',status='reconstructed-declared-header-only-not-runtime-qualified',profile=profile,compiled_source=COMPILED,header=str(header),header_sha256=sha(header),header_was_present=existed,header_was_in_original_retained_archive=False,derivation='Unchanged original configure_file template; one identical SDK token embedded in every unchanged boundary and native module; original guarded cockpit cache flag',binary_SDK_build_bases=observed,original_sources_sha256=sources,original_binary_and_cache_sha256=guards,original_build_record_sha256=sha(build_record),compiled_runtime_rebuilt=False,original_capture_or_audit_relabelled=False,original_fixture_or_rejection_auditor_changed=False,original_sanitizer_or_acceptance_check_changed=False,phase6_complete=False)
    atomic_json(output,report);return report
