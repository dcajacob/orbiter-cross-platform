#!/usr/bin/env python3
"""Observe the preserved API failure and corrected startup exit on current Windows."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from windows_session_v1 import context
from runtime_descriptor_v3 import preflight,require,sha
from static_binary_link_staging_v1 import BinaryLinks


def load(path):return json.loads(Path(path).read_text())
def lfsha(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def events(text):
    result=[]
    for line in text.splitlines():
        if 'Test: ' in line:result.append(line[line.index('Test: '):].rstrip())
        elif line.rstrip().endswith(' - passed'):result.append(' - passed')
        elif '=== All tests passed ===' in line:result.append('=== All tests passed ===')
    return result


def main():
    request=Path(sys.argv[1]);cfg=load(request);share=request.parent;source=Path(cfg['source']);output=Path(cfg['output'])
    report=dict(status='running',source=cfg['source_commit'],configuration=cfg['configuration'],math_profile=cfg['math_profile'],
        roles=cfg['roles'],transport_protocol=cfg['transport_protocol'],context=context(),request_sha256=sha(request),
        script_sha256=sha(__file__),cloud_builds_used=False,native_admission_qualified=False,phase6_complete=False,
        diagnostic_only=True,cases={})
    links=None
    def save():
        temporary=share/'worker-result.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(share/'worker-result.json')
    try:
        require(report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']),
                'Actual declared rendering context differs')
        report['root_preflight']=preflight(cfg)
        require(cfg['capture_scope']==dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']) and
                cfg['source_role']=='application' and cfg['math_profile']=='matrix', 'Explicit API correction scope required')
        require(sha(cfg['application_build_manifest'])==cfg['application_build_manifest_sha256'],'Current build record differs')
        built=load(cfg['application_build_manifest']);item=built['configurations'][cfg['configuration']]
        require(built['source_commit']==cfg['source_commit'] and built['owning_sources_unchanged'] and item['status']=='built' and
                Path(item['runtime'])==Path(cfg['preserved']),'Actual current application/SDK package differs')
        require(all(cfg['roles'][role]['manifest_sha256']==item['sdk_manifest_sha256'] and
                    Path(cfg['roles'][role]['manifest_path'])==Path(cfg['preserved'])/'test-runtime.json'
                    for role in ('application','sdk')),'Application/SDK role does not name the actual current package')
        require(subprocess.check_output([cfg['git'],'-C',source,'rev-parse','HEAD'],text=True).strip()==cfg['source_commit'],
                'Actual owning application source differs')
        source_guards=built['source_guard_sha256_lf']
        require(all(lfsha(source/name)==value for name,value in source_guards.items()),'Current application source changed')
        runtime=Path(cfg['preserved']);guards={str(runtime/name):value for name,value in item['runtime_files_sha256'].items()}
        require(all(sha(path)==value for path,value in guards.items()),'Current runtime bytes differ')
        observer_build=load(cfg['roles']['observer']['manifest_path']);observer=observer_build['observer']
        require(observer_build['status']=='prepared-passive-observer-only' and observer['kind']=='general-api' and
                observer['source_commit']==cfg['roles']['observer']['commit'] and observer['sdk_source_commit']==cfg['source_commit'] and
                observer['configuration']==cfg['configuration'] and sha(observer['binary'])==observer['sha256'],
                'Actual matching-SDK API observer differs')
        require(observer_build['sdk']['manifest_sha256']==item['sdk_manifest_sha256'],
                'Observer was compiled against a different SDK package')
        guards[observer['binary']]=observer['sha256']
        variant=load(cfg['variant']['manifest']);require(sha(cfg['variant']['manifest'])==cfg['variant']['manifest_sha256'] and
            variant['protocol']=='general-api-spice-test-correction-v2' and variant['oracle']['replaced_regions']==4 and
            variant['planetary_data_and_simulation_tolerances_unchanged'], 'Pinned narrow API correction required')
        corrected=Path(cfg['variant']['script']);require(sha(corrected)==variant['corrected_script_sha256'],'Corrected test bytes differ')
        script='Script/Tests/GeneralApiTest.lua';scenario='Scenarios/Tests/GeneralApiTest.scn'
        require(lfsha(runtime/script)==variant['locked_inputs_sha256_lf'][script] and
                lfsha(runtime/'Config/Earth.cfg')==variant['locked_inputs_sha256_lf']['Src/Celbody/SPICE/Config/Earth.cfg'],
                'Original script or locked SPICE Earth configuration differs')
        require(lfsha(source/scenario)==cfg['scenario_sha256_lf'],'Unchanged stock scenario required')
        sys.path[:0]=[str(source/'Tests/Production/RemainingStock'),str(source/'Tests/Production/Client'),str(source/'Tests/Production')]
        from stage_original import run
        from run_client import mesa_files
        provider=load(Path(cfg['mesa'])/'mesa-runtime.json')
        guards.update({str(Path(cfg['mesa'])/name):v['sha256'] for name,v in provider['files'].items()})
        os.environ.update(PATH=str(Path(cfg['git']).parent)+';'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1',
                          LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
        output.mkdir();links=BinaryLinks(guards,output);links.install();save()
        for profile in ('automatic','sse2'):
            if profile=='sse2':os.environ['ORBITER_TEST_OBSERVER_SSE2']='1'
            else:os.environ.pop('ORBITER_TEST_OBSERVER_SSE2',None)
            for test in ('original','corrected'):
                for mode in ('off','on'):
                    if mode=='off':os.environ['ORBITER_TEST_DISABLE_API_OBSERVER']='1'
                    else:os.environ.pop('ORBITER_TEST_DISABLE_API_OBSERVER',None)
                    folder=output/(profile+'-'+test+'-'+mode)
                    case=dict(scenario='Tests/GeneralApiTest.scn',scenario_entry_point=scenario,playback_vessels=[])
                    def configure(directory):
                        config=directory/'Orbiter.cfg';text=config.read_text()
                        require(text.count('  ProductionBehaviorDriver')==1,'Owning staging fixture differs')
                        text=text.replace('  ProductionBehaviorDriver',
                            '  ProductionGeneralApiObserver\n  OGLClient')
                        config.write_text(text+'\nFPS = 0\n')
                        target=directory/script
                        if test=='corrected':target.unlink();target.write_bytes(corrected.read_bytes())
                        target=directory/scenario;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/scenario).read_bytes())
                        fixture='Scenarios/Tests/Description.txt';target=directory/fixture
                        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/fixture,target)
                        require(all((directory/name).is_file() for name in (
                            'Config/Sun.cfg',fixture,'Textures/transp.dds','Textures2/DG/dgmk4_1.dds',
                            'Meshes/dummy.msh','Modules/ScriptVessel.dll')),'Original API file-access fixtures incomplete')
                        shutil.copy2(observer['binary'],directory/'Modules/Plugin/ProductionGeneralApiObserver.dll')
                        (directory/'ogl-evidence.enabled').touch();mesa_files(Path(cfg['mesa']),directory)
                    run(runtime/'Orbiter.exe',Path(cfg['data']),Path(cfg['planets']),folder,
                        dict(fixed_step=0.015625,frames=60,delivery_repairs=[]),case,configure,process_timeout=900)
                    identity=load(folder/'api-observer.json');timing=load(folder/'process-timing.json')
                    invocation=load(folder/'invocation.json')
                    (folder/'diagnostic-invocation.json').write_text(json.dumps(dict(argv=invocation['argv'],
                        stager_manifest_sha256=sha(folder/'invocation.json'),stager_cockpit_driver_is_inactive=True,
                        actual_api_observer_sha256=observer['sha256'],script_sha256=sha(folder/script),
                        profile=profile,variant=test,observation=mode),indent=2)+'\n')
                    require(identity['actual_pid']==timing['actual_pid'] and identity['initial_fma3']==1 and
                            identity['active_fma3']==(0 if profile=='sse2' else 1) and
                            identity['observation_enabled']==(mode=='on'),'Actual observer/mode/PID differs')
                    text=(folder/'Orbiter.log').read_text(errors='replace');observed=events(text)
                    if test=='corrected':
                        require(observed.count('=== All tests passed ===')==1 and observed.count(' - passed')==11 and
                                not any(s in text for s in ('Assertion failed',' - FAILED!','LuaCall (','Lua error:')),
                                'Corrected actual API test failed')
                        require(not (folder/'graphics-lifecycle.json').exists(),'Windows abrupt exit unexpectedly changed')
                    else:
                        require('Assertion failed' in text and 'Test: planet status' in text and
                                '=== All tests passed ===' not in text,'Original inherited failure was lost')
                    report['cases'][folder.name]=dict(process=timing,observer=identity,assertion_events=observed,
                        script_result='failed-inherited-assertion' if test=='original' else 'passed-corrected-test',
                        script_sha256=sha(folder/script),scenario_sha256_lf=lfsha(folder/scenario),
                        graphics=load(folder/'graphics-lifecycle.json') if (folder/'graphics-lifecycle.json').exists() else None,
                        provider_sha256=sha(identity['dispatch_provider']),folder=str(folder))
                    save()
                a=report['cases'][profile+'-'+test+'-off'];b=report['cases'][profile+'-'+test+'-on']
                require(a['assertion_events']==b['assertion_events'] and a['graphics']==b['graphics'],
                        'Startup observation changed assertions or graphics completion')
                if test=='original':
                    name='Scenarios/(Current state).scn'
                    require(sha(Path(a['folder'])/name)==sha(Path(b['folder'])/name),'Startup observation changed original final saved state')
        require(all(sha(path)==value for path,value in guards.items()) and
                all(lfsha(source/name)==value for name,value in source_guards.items()),
                'Owning source, runtime, SDK, provider or observer changed')
        links.close();export=Path(cfg['export']);export.mkdir()
        for name in report['cases']:
            folder=output/name;target=export/name;target.mkdir()
            paths=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in ('.dll','.exe')]
            paths += [folder/script,folder/scenario]
            current=folder/'Scenarios/(Current state).scn'
            if current.exists():paths.append(current)
            for path in paths:
                destination=target/path.relative_to(folder);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
        report.update(status='captured-current-Windows-original-and-corrected-api-diagnostic-only',
            observer_equivalence=True,actual_processes=8,owning_runtime_sdk_provider_unchanged=True,
            export_files_sha256={p.relative_to(export).as_posix():sha(p) for p in export.rglob('*') if p.is_file()})
    except BaseException as error:
        report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        if links:links.close()
        save()


if __name__=='__main__':main()
