#!/usr/bin/env python3
"""Seal the tested Actions application/SDK without granting stock acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[3]
WINDOWS_2025_IMAGES={'win25','win25-vs2026'}


def standard_windows_2025(image,runner_os):
    return runner_os=='Windows' and image in WINDOWS_2025_IMAGES


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def safe(name):
    relative=PurePosixPath(name)
    require(name and str(relative)==name and name!='.' and not relative.is_absolute() and '..' not in relative.parts and
            ':' not in name and '\\' not in name,'Unsafe SDK package member')


def unit_result(inventory,result):
    names=[item['name'] for item in inventory['tests']]
    cases=ET.parse(result).getroot().findall('.//testcase')
    executed=[case.attrib['name'] for case in cases]
    require(names and len(names)==len(set(names))==len(executed)==len(set(executed)) and
            set(names)==set(executed),'Complete actual Windows CTest inventory required')
    require(not any(case.find(tag) is not None for case in cases for tag in ('failure','error','skipped')),
            'Failed/skipped Windows units cannot qualify SDK retention')
    return dict(registered_processes=len(names),executed_processes=len(cases),junit_sha256=sha(result))


def runtime_files(runtime,producer):
    manifest=runtime/'test-runtime.json';sdk=json.loads(manifest.read_text())
    require(sdk['source_commit']==producer and sdk['files'],'Exact current application/SDK producer required')
    for name,checksum in sdk['files'].items():
        safe(name);path=runtime/name
        require(path.is_file() and not path.is_symlink() and sha(path)==checksum,'Original SDK member changed: '+name)
    paths=list(runtime.rglob('*'))
    require(not any(path.is_symlink() for path in paths),'SDK runtime symlinks cannot be sealed')
    files={path.relative_to(runtime).as_posix():sha(path) for path in paths if path.is_file()}
    require({'Orbiter.exe','test-runtime.json','Orbitersdk/lib/Orbiter.lib','Orbitersdk/lib/Orbitersdk.lib',
             'Orbitersdk/include/Orbitersdk.h','Modules/Plugin/OGLClient.dll'}<=set(files),
            'Complete current application, SDK and separately linked renderer required')
    return files


def prepare_runtime(archive,tested,runtime,variants,producer):
    """Keep the original SDK intact after client jobs replace a test-only driver."""
    require(not runtime.exists() and not variants.exists(),'Fresh SDK and driver-variant destinations required')
    runtime.mkdir();variants.mkdir();changes={}
    with zipfile.ZipFile(archive) as packaged:
        sdk=json.loads(packaged.read('test-runtime.json'))
        require(sdk['source_commit']==producer and len(packaged.namelist())==len({n.casefold() for n in packaged.namelist()}) and
                set(packaged.namelist())==set(sdk['files'])|{'test-runtime.json'},'Closed original source-built SDK archive required')
        require(sum(i.file_size for i in packaged.infolist())<4*1024**3,'SDK archive exceeds bounded retention')
        for name in packaged.namelist():
            safe(name);body=packaged.read(name);target=runtime/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
            checksum=hashlib.sha256(body).hexdigest()
            if name!='test-runtime.json':require(checksum==sdk['files'][name],'Original SDK archive member differs')
            current=tested/name;require(current.is_file() and not current.is_symlink(),'Tested SDK member missing')
            if sha(current)!=checksum:
                require(name in {'Modules/Plugin/ProductionBehaviorDriver.'+suffix for suffix in ('dll','pdb','ilk')},
                        'Production application/SDK changed after client tests: '+name)
                destination=variants/Path(name).name;shutil.copy2(current,destination)
                changes[name]=dict(original_sdk_sha256=checksum,tested_driver_sha256=sha(current),
                    retained_tested_driver=str(destination))
    renderer=tested/'Modules/Plugin/OGLClient.dll';require(renderer.is_file(),'Tested separately linked renderer missing')
    shutil.copy2(renderer,runtime/'Modules/Plugin/OGLClient.dll')
    return changes


def source_files(producer):
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',producer],text=True).splitlines()
    guards={}
    with subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as reader:
        for name in names:
            safe(name);reader.stdin.write((producer+':'+name+'\n').encode());reader.stdin.flush()
            header=reader.stdout.readline().split();require(len(header)==3 and header[1]==b'blob','Actual source blob missing')
            original=reader.stdout.read(int(header[2]));require(reader.stdout.read(1)==b'\n','Incomplete source read')
            path=ROOT/name;actual=path.read_bytes().replace(b'\r\n',b'\n')
            require(actual==original.replace(b'\r\n',b'\n'),'Owning current source changed: '+name)
            guards[name]=hashlib.sha256(actual).hexdigest()
        reader.stdin.close();require(reader.wait()==0,'Actual immutable source reader failed')
    return guards


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    parser.add_argument('--output',type=lambda v:Path(v).resolve(),required=True);args=parser.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform','Authorized actual GitHub Windows runner required')
    require(not args.output.exists() and args.output.is_relative_to(ROOT/'out'),'Fresh SDK retention below repository out required')
    args.output.mkdir(parents=True);producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    report=dict(protocol='phase6-github-current-application-v1',status='retaining',source_commit=producer,
        builder_sha256=sha(__file__),configurations={},cloud_builds_used=True,phase6_complete=False,
        stock_qualification_pending=True,native_admission_qualified=False,
        github=dict(repository=os.environ['GITHUB_REPOSITORY'],run_id=int(os.environ['GITHUB_RUN_ID']),
                    run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),job=os.environ['GITHUB_JOB'],
                    source=os.environ['GITHUB_SHA'],runner_os=os.environ['RUNNER_OS'],image_os=os.environ['ImageOS']))
    def save():(args.output/'current-application.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        require(producer==report['github']['source'] and standard_windows_2025(report['github']['image_os'],report['github']['runner_os']),
                'Exact current source and standard Windows 2025 image required')
        tested=ROOT/'out/production-app';build=ROOT/'out/runtime-rebuild'
        runtime=args.output/'runtime';original_archive=ROOT/'out/runtime-archive/windows-test-runtime.zip'
        inventory=json.loads(subprocess.check_output(['ctest','--test-dir',str(build),'--show-only=json-v1'],text=True))
        tests=unit_result(inventory,build/'runtime-ctest.xml')
        (args.output/'registered-tests.json').write_text(json.dumps(inventory,indent=2)+'\n')
        for path in (build/'runtime-ctest.xml',build/'build-inputs.json',ROOT/'runtime-ctest.log',
                     ROOT/'out/opengl-client/compile_commands.json'):
            shutil.copy2(path,args.output/path.name)
        metadata=json.loads((build/'build-inputs.json').read_text());cache=metadata['cmake_cache']
        require(cache['CMAKE_BUILD_TYPE:STRING']==args.configuration and
                cache['ORBITER_MAKE_TESTS:BOOL']=='ON' and cache['ORBITER_PRODUCTION_REFERENCE_CAPTURE:BOOL']=='ON',
                'Actual Windows configuration/test options differ')
        guards=source_files(producer)
        changes=prepare_runtime(original_archive,tested,runtime,args.output/'tested-driver-variants',producer)
        files=runtime_files(runtime,producer)
        archive=args.output/'runtime.zip'
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as packaged:
            for name in sorted(files):packaged.write(runtime/name,name)
        with zipfile.ZipFile(archive) as packaged:
            require(len(packaged.namelist())==len(files) and set(packaged.namelist())==set(files) and
                    all(hashlib.sha256(packaged.read(name)).hexdigest()==checksum for name,checksum in files.items()),
                    'Sealed SDK archive closure differs')
        require(files==runtime_files(runtime,producer) and
                all(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==value for name,value in guards.items()),
                'Owning current runtime/source changed during retention')
        report.update(status='built-and-client-tested-awaiting-complete-stock-qualification',owning_sources_unchanged=True,
            source_guard_sha256_lf=guards,runtime_archive_sha256=sha(archive),runtime_archive_bytes=archive.stat().st_size,
            original_sdk_archive_sha256=sha(original_archive),client_test_driver_variants=changes,
            original_sdk_members_preserved=True,stock_observer_still_requires_compilation_against_this_sdk=True)
        report['configurations'][args.configuration]=dict(status='built',runtime=str(runtime),build=str(build),
            sdk_manifest_sha256=sha(runtime/'test-runtime.json'),build_inputs_sha256=sha(build/'build-inputs.json'),
            runtime_files_sha256=files,tests=tests)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
