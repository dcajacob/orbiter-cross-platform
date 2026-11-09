#!/usr/bin/env python3
"""Restore the exact independently controlled Mesa repair with its actual compiled owner."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from hosted_native_package import ROOT,require,sha,load
from restore_hosted_native_providers import safe

SOURCE='6d17e4f18e4eade72fa295c3d03a38a58182d35f'
RUN=42543636813
ARTIFACT=13642189340
SIZE=53687675
DIGEST='7a2b06da0b1d39153066414d8ea303cdfafcbe8184170e9e80bc33cee6d61392'
BASE_SOURCE='60ba46377f236c2d4705f444c0174e0f5af8252f'
PREFIX='out/hosted-mesa-topology'
STEPS=('Build only Mesa and run original allocator and graphics plus CPU owner controls in exact userspace',
       'Retain the separate repair bytes and every completed or partial control','Run actions/upload-artifact@v7')


def validate_api(record):
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==RUN and run['head_sha']==SOURCE and
        run['head_branch']=='qualification/mesa-topology-repair' and run['path']=='.github/workflows/phase6-mesa-topology.yml' and
        run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','Exact successful Mesa repair producer required')
    require(artifact['id']==ARTIFACT and artifact['name']=='mesa-topology-owner-repair' and artifact['expired'] is False and
        artifact['size_in_bytes']==SIZE and artifact['digest']=='sha256:'+DIGEST and artifact['workflow_run']['id']==RUN and
        artifact['workflow_run']['head_sha']==SOURCE,'Exact successful Mesa repair API artifact required')
    require(len(jobs)==1 and jobs[0]['id']==128923839407 and jobs[0]['run_id']==RUN and jobs[0]['head_sha']==SOURCE and
        jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and 'ubuntu-24.04' in jobs[0]['labels'],
        'Successful actual Mesa controls on the standard runner required')
    for name in STEPS:
        selected=[s for s in jobs[0]['steps'] if s['name']==name]
        require(len(selected)==1 and selected[0]['status']=='completed' and selected[0]['conclusion']=='success','Actual Mesa repair step differs: '+name)


def controls(base,sealed):
    require(set(sealed['controls'])=={'allocator','cpu-owner','egl'} and all(c['status']=='passed' and sha(c['path'])==c['sha256'] for c in sealed['controls'].values()),
        'Complete original allocator, original EGL and new CPU owner controls required')
    cpu=load(base/'cpu-controls/report.json');require(cpu['status']=='passed' and cpu['sanitizers']==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),
        'Actual unsuppressed Mesa owner controls required')
    require(set(cpu['runs'])=={'baseline','candidate','genuine-leak'},'Original baseline, clean candidate and independent genuine leak all required')
    for name,expected in [('baseline',2560),('genuine-leak',81920)]:
        run=cpu['runs'][name];require(run['actual_returncode']!=0 and 'completed_ownership_cycles=20' in run['output'] and
            f'{expected} byte(s) leaked in 20 allocation(s)' in run['output'],'Actual independent failing owner/leak control required')
    clean=cpu['runs']['candidate'];require(clean['actual_returncode']==0 and 'completed_ownership_cycles=20' in clean['output'] and
        not any(t in clean['output'] for t in ('ERROR:','SUMMARY:','runtime error:')),'Actual candidate owner lifetimes must be clean')
    path=ROOT/'Tests/Production/GraphicsDriverLifetime/topology_cleanup.py'
    require(path.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':Tests/Production/GraphicsDriverLifetime/topology_cleanup.py']),
        'Exact immutable topology variant reader required')
    spec=importlib.util.spec_from_file_location('verified_mesa_topology_variant',path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    actual=(base/'mesa/mesa-26.0.8/src/util/u_cpu_detect.c').read_bytes()
    require(actual.endswith(helper.APPEND) and helper.candidate(actual[:-len(helper.APPEND)])==actual and
        cpu['original_source_sha256']==helper.ORIGINAL_SHA256 and cpu['compiled_source_sha256']==sha(base/'mesa/mesa-26.0.8/src/util/u_cpu_detect.c'),
        'Original CPU detection and sole unload-lifetime addition differ')
    cases=list(ET.parse(base/'egl-controls/candidate.xml').getroot().iter('testcase'))
    require(len(cases)==2 and {c.attrib['name'] for c in cases}=={'driver-mipmap','driver-no-mipmap'} and
        not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped')),'Both unchanged original EGL unload tests must have executed and passed')
    build=load(base/'mesa/driver-build.json');libraries=base/'mesa/install/lib/x86_64-linux-gnu'
    require(build['status']=='built' and set(build['libraries'])=={'libgallium-26.0.8.so','libEGL_mesa.so.0.0.0','libGLX_mesa.so.0.0.0'} and
        all(sha(libraries/name)==value for name,value in build['libraries'].items()),'Exact complete compiled Mesa library identities required')


def verify_restored(path,owner,collector):
    record=load(path);require(record['protocol']=='phase6-hosted-Mesa-topology-restoration-v1' and record['status']=='restored-verified-Mesa-only' and
        record['compiled_mesa_source']==SOURCE and record['base_provider_source']==BASE_SOURCE and record['restorer_source']==collector and
        record['original_run_id']==RUN and record['original_artifact_id']==ARTIFACT and record['original_api_archive_sha256']==DIGEST,
        'Exact separately compiled/restored Mesa role required')
    archive=Path(record['source_archive'])
    require(Path(owner).resolve()==ROOT and archive.is_relative_to(ROOT/'out') and archive.stat().st_size==SIZE and sha(archive)==DIGEST,'Actual original Mesa ZIP must still bind the restored manifest')
    with zipfile.ZipFile(archive) as incoming:
        names=[n for n in incoming.namelist() if Path(n).name=='hosted-mesa-topology.json']
        require(len(names)==1,'Unique original Mesa manifest required')
        sealed=json.loads(incoming.read(names[0]))
    require(record['members']==sealed['members'] and record['controls']==sealed['controls'] and sealed['compiled_mesa_source']==SOURCE,
        'Actual restored Mesa/control manifest differs from immutable API ZIP')
    require(all(str(safe(name)).startswith(PREFIX+'/') and sha(Path(owner)/name)==value['sha256'] for name,value in record['members'].items()),'Actual restored Mesa/control closure changed')
    controls(Path(owner)/PREFIX,sealed)
    return Path(owner)/PREFIX/'mesa'


def restore_tree(archive,expected,owner):
    base=owner/PREFIX;require(not base.exists(),'Fresh source-bound provider tree required')
    links=[];seen=set()
    with tarfile.open(archive,'r:gz') as incoming:
        require(sum(m.size for m in incoming.getmembers())<8*1024**3,'Provider archive exceeds bounded restoration')
        for info in incoming.getmembers():
            name=str(safe(info.name));require(PurePosixPath(name).is_relative_to(PREFIX) and name in expected and
                    name.casefold() not in seen and not info.mode&0o7000,'Unmanifested, duplicate or unsafe provider member')
            seen.add(name.casefold());path=owner/name;path.parent.mkdir(parents=True,exist_ok=True)
            require(not path.exists() and not path.is_symlink(),'Provider restoration would overwrite another input')
            if info.isfile():
                require(expected[name]['symlink'] is None,'Provider link kind differs');path.write_bytes(incoming.extractfile(info).read());path.chmod(info.mode&0o777)
                require(sha(path)==expected[name]['sha256'],'Actual restored provider byte differs')
            elif info.issym():
                require(expected[name]['symlink']==info.linkname,'Actual provider symlink differs')
                target=Path(info.linkname);resolved=Path(os.path.normpath(str(target if target.is_absolute() else path.parent/target)))
                require(resolved.is_relative_to(base),'Provider symlink escapes the guarded tree');links.append((path,info.linkname,True))
            elif info.islnk():
                target=str(safe(info.linkname));require(target in expected and expected[name]['symlink'] is None and
                    expected[name]['sha256']==expected[target]['sha256'],'Unsafe or mismatched provider hardlink');links.append((path,owner/target,False))
            else:raise ValueError('Unsupported provider archive member kind')
    require(len(seen)==len(expected),'Complete provider archive closure required')
    pending=links
    while pending:
        remaining=[]
        for path,target,symbolic in pending:
            if symbolic:path.symlink_to(target)
            elif Path(target).is_file():os.link(target,path)
            else:remaining.append((path,target,symbolic))
        require(len(remaining)<len(pending),'Unresolvable provider hardlink closure');pending=remaining
    require(all((owner/name).resolve().is_relative_to(base) and sha(owner/name)==item['sha256'] for name,item in expected.items()),
            'Complete restored provider byte/link closure differs')
    return base

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(os.environ.get('GITHUB_ACTIONS')=='true' and sys.platform=='linux','Hosted Linux Mesa restoration only')
    record=load(a.api);validate_api(record);require(a.archive.stat().st_size==SIZE and sha(a.archive)==DIGEST,'Actual retained Mesa API ZIP differs')
    source=a.output.parent/'source-artifact';require(not source.exists() and not a.output.exists(),'Fresh Mesa source and restoration receipts required');source.mkdir(parents=True)
    wanted={'hosted-mesa-topology.tar.gz','hosted-mesa-topology.json'};found=set()
    with zipfile.ZipFile(a.archive) as incoming:
        for entry in incoming.infolist():
            if entry.is_dir():continue
            name=str(safe(entry.filename));leaf=Path(name).name
            if leaf not in wanted:continue
            require(leaf not in found,'Duplicate original Mesa payload');found.add(leaf);(source/leaf).write_bytes(incoming.read(entry))
    require(found==wanted,'Both exact original Mesa payload and manifest required')
    sealed=load(source/'hosted-mesa-topology.json');bundle=source/'hosted-mesa-topology.tar.gz'
    require(sealed['protocol']=='phase6-hosted-Mesa-topology-provider-v1' and sealed['status']=='built-and-dependency-controls-only' and
        sealed['compiled_mesa_source']==SOURCE and sealed['original_provider_source']==BASE_SOURCE and sealed['archive_sha256']==sha(bundle) and
        sealed['archive_bytes']==bundle.stat().st_size and sealed['phase6_complete'] is False and sealed['native_admission_qualified'] is False,
        'Complete immutable separate Mesa build/control package required')
    base=restore_tree(bundle,sealed['members'],ROOT);require(sha(base/'build.json')==sealed['build_sha256'],'Actual original Mesa build receipt differs');controls(base,sealed)
    result=dict(protocol='phase6-hosted-Mesa-topology-restoration-v1',status='restored-verified-Mesa-only',compiled_mesa_source=SOURCE,
        base_provider_source=BASE_SOURCE,restorer_source=os.environ['GITHUB_SHA'],original_run_id=RUN,original_artifact_id=ARTIFACT,
        original_api_archive_sha256=DIGEST,source_archive=str(a.archive),members=sealed['members'],controls=sealed['controls'],source_api_sha256=sha(a.api),
        phase6_complete=False,native_admission_qualified=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');verify_restored(a.output,ROOT,os.environ['GITHUB_SHA']);print(result['status'])


if __name__=='__main__':main()
