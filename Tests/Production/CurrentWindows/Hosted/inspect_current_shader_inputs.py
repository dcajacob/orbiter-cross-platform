"""Independently bind exported shader inputs to the original API-inspected C08 SDK."""
import hashlib
from pathlib import Path,PureWindowsPath
import subprocess
from source_complete_shader_provider import require,sha
from current_client_shaders import PROTOCOL,PREFIX,CMAKE,ESSENTIAL,inspect_delivery
from restore_sdk import PRODUCER,PINS,validate_api as sdk_api
import json

ROOT=Path(__file__).resolve().parents[4]


def load(path):return json.loads(Path(path).read_text())


def inspect_sources(plan,sdk_guards,owner=ROOT):
    require(plan['protocol']==PROTOCOL and plan['status']=='verified-exact-compiled-source-renderer-inputs-only' and
            plan['compiled_source']==PRODUCER and plan['original_renderer_install_rule']==CMAKE and
            plan['install_rule_sha256_lf']==sdk_guards[CMAKE] and plan['original_sdk_and_manifest_modified'] is False and
            plan['source_shader_bytes_modified'] is False and plan['phase6_complete'] is False and plan['native_admission_qualified'] is False,
            'Exact original C08 shader source delivery contract required')
    names=subprocess.check_output(['git','-C',str(owner),'ls-tree','-r','--name-only',PRODUCER,'--',PREFIX],text=True).splitlines()
    require(names and len(names)==len(set(names)) and ESSENTIAL<={name.removeprefix(PREFIX) for name in names},
            'Every original compiled-source shader/include required')
    expected={'Modules/OGLClient/'+name.removeprefix(PREFIX):name for name in names}
    require(set(plan['files'])==set(expected),'Missing or substituted original shader/include input')
    source_checks={}
    for target,name in expected.items():
        require(name.startswith(PREFIX) and '/' not in name[len(PREFIX):],'Exact flat original shader placement required')
        body=subprocess.check_output(['git','-C',str(owner),'show',PRODUCER+':'+name]).replace(b'\r\n',b'\n')
        value=plan['files'][target];allowed={(hashlib.sha256(raw).hexdigest(),len(raw)) for raw in (body,body.replace(b'\n',b'\r\n'))}
        checksum=hashlib.sha256(body).hexdigest()
        require(value['source']==name and value['source_sha256_lf']==sdk_guards[name]==checksum and
                (value['sha256'],value['bytes']) in allowed,
                'Copied shader bytes are not the exact original LF/CRLF representation of the compiled C08 source')
        source_checks[name]=checksum
    cmake=subprocess.check_output(['git','-C',str(owner),'show',PRODUCER+':'+CMAKE]).replace(b'\r\n',b'\n')
    require(hashlib.sha256(cmake).hexdigest()==sdk_guards[CMAKE],'Original compiled renderer placement source differs')
    return source_checks,{hashlib.sha256(raw).hexdigest() for raw in (cmake,cmake.replace(b'\n',b'\r\n'))}


def inspect(payload,cfg,inputs,export,config):
    workspace=PureWindowsPath(cfg['workspace']);item=cfg['renderer_shader_delivery'];plan_path=payload/'current-shader-delivery'/(cfg['name']+'.json')
    require(PureWindowsPath(item['path'])==workspace/'out/current-shader-delivery'/(cfg['name']+'.json') and
            plan_path.is_file() and not plan_path.is_symlink() and sha(plan_path)==item['sha256'],
            'Actual API-retained shader delivery plan path/bytes differ')
    plan=load(plan_path);sdk_file=payload/'current-windows-sdk/restoration.json';sdk=load(sdk_file)
    api_file=payload/'current-sdk-source/api.json';api=load(api_file);sdk_job=sdk_api(api,cfg['configuration'])
    original=load(Path(inputs['runtime_local']).parent/'sdk-source/current-application.json')
    require(sha(Path(inputs['runtime_local']).parent/'sdk-source/current-application.json')==inputs['original_sdk_manifest_sha256'] and
            inputs['compiled_application_source']==inputs['compiled_observer_source']==PRODUCER and
            sdk['protocol']=='phase6-github-current-sdk-restoration-v1' and sdk['status']=='restored-and-verified-current-sdk-only' and sdk['compiled_source']==PRODUCER and
            sdk['stock_simulation_executed'] is False and sdk['phase6_complete'] is False and sdk['native_admission_qualified'] is False and
            sdk['original_artifact_id']==api['artifact']['id'] and sdk['original_artifact_sha256']==PINS[cfg['configuration']][2] and
            sdk['original_run_id']==api['run']['id'] and sdk['original_job_id']==sdk_job['id'] and
            PureWindowsPath(sdk['source_owner'])==PureWindowsPath(cfg['source']) and
            PureWindowsPath(sdk['runtime'])==PureWindowsPath(inputs['runtime_original_path']) and
            sdk['collector_source']==cfg['github']['collector_commit'] and sdk['configuration']==plan['configuration']==cfg['configuration'] and
            sdk['source_guard_sha256_lf']==original['source_guard_sha256_lf'] and
            sdk['runtime_files_sha256']==inputs['runtime_files_sha256'] and
            sdk['original_build_manifest_sha256']==inputs['original_sdk_manifest_sha256'] and
            plan['collector_source']==cfg['github']['collector_commit'] and plan['cell']==cfg['name'] and
            plan['sdk_manifest_sha256']==inputs['sdk_manifest_sha256']==cfg['roles']['sdk']['manifest_sha256'] and
            plan['sdk_restoration_sha256']==sha(sdk_file) and sdk['source_api_sha256']==sha(api_file) and
            plan['original_sdk_artifact_id']==PINS[cfg['configuration']][0]==api['artifact']['id'] and
            plan['original_sdk_artifact_sha256']==PINS[cfg['configuration']][2] and
            PureWindowsPath(plan['source_owner'])==PureWindowsPath(cfg['source']) and
            PureWindowsPath(plan['sdk_restoration_path'])==workspace/'out/current-windows-sdk/restoration.json',
            'Actual shader plan must bind the independently inspected original SDK/source and captured role identities')
    source_checks,cmake_raw=inspect_sources(plan,original['source_guard_sha256_lf'])
    guardmap={PureWindowsPath(k):v for k,v in plan['guarded_files_sha256'].items()}
    require(len(guardmap)==len(plan['guarded_files_sha256']),'Aliased/case-colliding shader source guard paths')
    cmake_path=PureWindowsPath(cfg['source'])/CMAKE
    require(guardmap.get(cmake_path) in cmake_raw,'Exact original renderer placement bytes must be guarded')
    expected={workspace/'out/current-windows-sdk/restoration.json':sha(sdk_file),workspace/'out/current-sdk-source/api.json':sha(api_file),
              PureWindowsPath(inputs['runtime_original_path'])/'test-runtime.json':inputs['sdk_manifest_sha256'],cmake_path:guardmap[cmake_path]}
    expected.update({PureWindowsPath(cfg['source'])/v['source']:v['sha256'] for v in plan['files'].values()})
    require(guardmap==expected,'Complete original shader/SDK/API/source guard closure required')
    count=0
    for case in config['cases']:
        for repeat in (1,2):
            folder=export/(cfg['math_profile']+'-'+cfg['phase'])/(case['id']+'-'+str(repeat))
            inspect_delivery(folder,plan,item['sha256']);count+=1
    require(len(config['cases'])==38 and count==76,'All actual current process shader input receipts required')
    return dict(protocol=PROTOCOL,plan_sha256=item['sha256'],compiled_source=PRODUCER,
        actual_original_shader_and_include_count=len(plan['files']),original_sdk_modified=False,qualification_granted=False,
        actual_exported_processes=count,original_source_sha256_lf=source_checks)
