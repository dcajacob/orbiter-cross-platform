"""Deliver the missing renderer inputs from the same immutable compiled C08 source.

The sealed SDK stays unchanged. Every original shader/include file is copied without
editing, retained in the raw export, and checked before and after the simulator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path,PureWindowsPath
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,load
from restore_sdk import PRODUCER,PINS

PROTOCOL='phase6-current-same-source-renderer-shader-inputs-v1'
PREFIX='OVP/OGLClient/shaders/'
CMAKE='OVP/OGLClient/CMakeLists.txt'
ESSENTIAL={'Constellations.vs','Constellations.fs','Common.inc','LogDepth.inc','Types.inc','Uniforms.inc'}
SUFFIXES={'.vs','.fs','.inc'}


def source_bytes(owner,name,guards):
    path=Path(owner)/name
    require(path.is_file() and not path.is_symlink() and path.resolve()==path,'Exact real source asset required: '+name)
    raw=path.read_bytes();normalized=raw.replace(b'\r\n',b'\n')
    original=subprocess.check_output(['git','-C',str(owner),'show',PRODUCER+':'+name]).replace(b'\r\n',b'\n')
    require(normalized==original and hashlib.sha256(normalized).hexdigest()==guards[name],
            'Renderer asset differs from its actual compiled SDK source owner: '+name)
    return raw


def build_plan(sdk_path,source,configuration,collector,cell):
    sdk_path=Path(sdk_path);source=Path(source);sdk=load(sdk_path)
    require(configuration in PINS and re.fullmatch('[0-9a-f]{40}',collector) and
            cell in {configuration+'-'+m+'-'+p for m in ('automatic','sse2') for p in ('stock','reload')},
            'Exact current renderer delivery profile and collector required')
    ident,_,digest=PINS[configuration]
    require(sdk['protocol']=='phase6-github-current-sdk-restoration-v1' and sdk['status']=='restored-and-verified-current-sdk-only' and
            sdk['compiled_source']==PRODUCER and sdk['configuration']==configuration and sdk['collector_source']==collector and
            sdk['original_artifact_id']==ident and sdk['original_artifact_sha256']==digest and Path(sdk['source_owner'])==source and
            sdk['stock_simulation_executed'] is False and sdk['phase6_complete'] is False and sdk['native_admission_qualified'] is False,
            'Exact previously verified immutable C08 SDK restoration required')
    require(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==PRODUCER,
            'Separate compiled C08 asset owner required')
    runtime=Path(sdk['runtime']);manifest=runtime/'test-runtime.json'
    require(sha(manifest)==sdk['runtime_files_sha256']['test-runtime.json'] and
            load(manifest)['source_commit']==PRODUCER,'Original sealed SDK manifest changed')
    api=sdk_path.parents[1]/'current-sdk-source/api.json'
    require(sha(api)==sdk['source_api_sha256'],'Actual retained SDK API receipt changed')
    guards=sdk['source_guard_sha256_lf'];cmake=source_bytes(source,CMAKE,guards)
    text=cmake.replace(b'\r\n',b'\n').decode()
    require('file(GLOB shaders CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/shaders/*")' in text and
            'COMMAND ${CMAKE_COMMAND} -E copy_if_different ${shaders} "${ORBITER_TEST_RUNTIME}/Modules/OGLClient"' in text,
            'Original same-source renderer asset placement rule differs')
    names=subprocess.check_output(['git','-C',str(source),'ls-tree','-r','--name-only',PRODUCER,'--',PREFIX],text=True).splitlines()
    require(names and len(names)==len(set(names)) and all(name.startswith(PREFIX) and '/' not in name[len(PREFIX):] for name in names) and
            ESSENTIAL<={name[len(PREFIX):] for name in names},'Every original renderer shader and include input required')
    files={};protected={str(sdk_path):sha(sdk_path),str(api):sha(api),str(manifest):sha(manifest),str(source/CMAKE):hashlib.sha256(cmake).hexdigest()}
    for name in sorted(names):
        raw=source_bytes(source,name,guards);target='Modules/OGLClient/'+name[len(PREFIX):]
        require(Path(target).suffix in SUFFIXES,'Unexpected original renderer input extension')
        files[target]=dict(source=name,source_sha256_lf=guards[name],sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        protected[str(source/name)]=files[target]['sha256']
    return dict(protocol=PROTOCOL,status='verified-exact-compiled-source-renderer-inputs-only',compiled_source=PRODUCER,
        collector_source=collector,configuration=configuration,cell=cell,source_owner=str(source),sdk_manifest_sha256=sha(manifest),
        sdk_restoration_path=str(sdk_path),sdk_restoration_sha256=sha(sdk_path),original_sdk_artifact_id=ident,original_sdk_artifact_sha256=digest,
        original_renderer_install_rule=CMAKE,install_rule_sha256_lf=guards[CMAKE],files=files,guarded_files_sha256=protected,
        original_sdk_and_manifest_modified=False,source_shader_bytes_modified=False,phase6_complete=False,native_admission_qualified=False)


def guarded(cfg):
    item=cfg['renderer_shader_delivery'];path=Path(item['path'])
    require(sha(path)==item['sha256'],'Renderer delivery plan changed')
    plan=load(path)
    require(plan['protocol']==PROTOCOL and plan['status']=='verified-exact-compiled-source-renderer-inputs-only' and
            plan['compiled_source']==cfg['source_commit']==cfg['roles']['sdk']['commit']==PRODUCER and
            plan['collector_source']==cfg['github']['collector_commit'] and plan['configuration']==cfg['configuration'] and
            plan['cell']==cfg['name'] and Path(plan['source_owner'])==Path(cfg['source']) and
            plan['sdk_manifest_sha256']==cfg['roles']['sdk']['manifest_sha256'] and
            plan['original_sdk_and_manifest_modified'] is False and plan['source_shader_bytes_modified'] is False and
            plan['phase6_complete'] is False and plan['native_admission_qualified'] is False,
            'Same-source current renderer plan/profile/SDK identities differ')
    result=dict(plan['guarded_files_sha256']);result[str(path)]=item['sha256']
    require(result and all(sha(name)==value for name,value in result.items()),'Actual C08 shader source/SDK/API/plan changed')
    return result


def verify(cfg):
    protected=guarded(cfg);plan=load(cfg['renderer_shader_delivery']['path'])
    sdk_path=Path(plan['sdk_restoration_path']);require(str(sdk_path) in protected,'Explicit guarded SDK restoration required')
    actual=build_plan(sdk_path,Path(cfg['source']),cfg['configuration'],cfg['github']['collector_commit'],cfg['name'])
    require(actual==plan and guarded(cfg)==protected,'Renderer delivery plan differs from independently recomputed source/SDK inputs')
    return dict(protocol=PROTOCOL,plan_sha256=cfg['renderer_shader_delivery']['sha256'],compiled_source=PRODUCER,
                actual_original_shader_and_include_count=len(plan['files']),original_sdk_modified=False,qualification_granted=False)


def validate_paths(cfg,workspace):
    item=cfg['renderer_shader_delivery']
    require(set(item)=={'path','sha256'} and re.fullmatch('[0-9a-f]{64}',item['sha256']) and
            PureWindowsPath(item['path'])==workspace/'out/current-shader-delivery'/(cfg['name']+'.json'),
            'Exact new renderer delivery receipt below inherited workspace required')


def inspect_delivery(directory,plan,plan_sha256):
    directory=Path(directory);receipt=load(directory/'current-client-shader-delivery.json')
    expected={name:value['sha256'] for name,value in plan['files'].items()}
    require(receipt==dict(protocol=PROTOCOL,status='staged-exact-original-C08-renderer-shader-inputs',plan_sha256=plan_sha256,
        compiled_source=PRODUCER,configuration=plan['configuration'],sdk_manifest_sha256=plan['sdk_manifest_sha256'],files_sha256=expected,
        original_sdk_modified=False,source_shader_bytes_modified=False,qualification_granted=False),
        'Actual per-process renderer input delivery receipt differs')
    actual={p.relative_to(directory).as_posix():sha(p) for p in (directory/'Modules/OGLClient').rglob('*')
            if p.is_file() and p.suffix in SUFFIXES}
    require(actual==expected and all(not (directory/name).is_symlink() for name in expected),
            'Actual staged or exported renderer shader/include bytes differ from the immutable C08 plan')
    return receipt


def stage(directory,cfg):
    protected=guarded(cfg);plan=load(cfg['renderer_shader_delivery']['path']);directory=Path(directory)
    receipt=directory/'current-client-shader-delivery.json';require(not receipt.exists(),'Fresh renderer input delivery receipt required')
    for relative,value in plan['files'].items():
        path=directory/relative;require(path.is_relative_to(directory/'Modules/OGLClient') and not path.is_symlink(),'Exact owned renderer input destination required')
        path.parent.mkdir(parents=True,exist_ok=True);require(path.parent.resolve()==path.parent,'Redirected renderer input parent')
        if path.exists():require(sha(path)==value['sha256'],'Conflicting staged original renderer input')
        else:shutil.copy2(Path(plan['source_owner'])/value['source'],path)
        require(path.stat().st_size==value['bytes'] and sha(path)==value['sha256'],'Original source renderer bytes changed while copying')
    record=dict(protocol=PROTOCOL,status='staged-exact-original-C08-renderer-shader-inputs',plan_sha256=cfg['renderer_shader_delivery']['sha256'],
        compiled_source=PRODUCER,configuration=plan['configuration'],sdk_manifest_sha256=plan['sdk_manifest_sha256'],
        files_sha256={name:value['sha256'] for name,value in plan['files'].items()},original_sdk_modified=False,
        source_shader_bytes_modified=False,qualification_granted=False)
    receipt.write_text(json.dumps(record,indent=2)+'\n');inspect_delivery(directory,plan,cfg['renderer_shader_delivery']['sha256'])
    require(guarded(cfg)==protected,'Original SDK/shader/API sources changed while staging renderer inputs')
    return {str(directory/name):value['sha256'] for name,value in plan['files'].items()}|{str(receipt):sha(receipt)}


def inspect_staged(directory,cfg):
    guarded(cfg)
    return inspect_delivery(directory,load(cfg['renderer_shader_delivery']['path']),cfg['renderer_shader_delivery']['sha256'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cell',required=True);p.add_argument('--configuration',choices=sorted(PINS),required=True);a=p.parse_args()
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('ImageOS') in {'win25','win25-vs2026'},
            'Actual standard GitHub Windows shader source preparation required')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();require(head==os.environ['GITHUB_SHA'],'Exact renderer delivery collector required')
    output=ROOT/'out/current-shader-delivery'/(a.cell+'.json');require(not output.exists(),'Fresh source-bound renderer plan required');output.parent.mkdir(parents=True,exist_ok=True)
    plan=build_plan(ROOT/'out/current-windows-sdk/restoration.json',ROOT/'application-source',a.configuration,head,a.cell)
    output.write_text(json.dumps(plan,indent=2)+'\n');print(plan['status'])


if __name__=='__main__':main()
