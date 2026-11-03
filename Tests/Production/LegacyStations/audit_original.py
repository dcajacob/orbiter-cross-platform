#!/usr/bin/env python3
"""Audit all four original legacy station profiles before native admission."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import re
import stat
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('legacy_station_capture',HERE/'original.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
ROOT=legacy.ROOT
digest=legacy.digest
require=legacy.require
sha_lf=legacy.sha_lf
# The legacy loader places the shared stock helpers first on sys.path.
from verify_original import compare_state

OBSERVER='Modules/Plugin/ProductionCockpitDriver.dll'


def safe_name(name):
    name=name.replace('\\','/');path=PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name,'Unsafe original artifact path')
    return name


def verify_archive(archive,base):
    """Bind every extracted byte to the independently downloaded ZIP digest."""
    seen=set()
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            name=safe_name(item.filename)
            require(name not in seen,'Duplicate original legacy archive member');seen.add(name)
            require('\\' not in item.filename and not stat.S_ISLNK(item.external_attr>>16),
                    'Unsafe original legacy archive member')
            if item.is_dir():continue
            target=base/name
            require(target.is_file() and digest(target)==hashlib.sha256(source.read(item)).hexdigest(),
                    'Extracted original legacy archive member differs: '+name)
    require(seen,'Original legacy archive is empty')
    return len(seen)


def producer_sources(report,producer):
    source={safe_name(name):value for name,value in report['source_sha256_lf'].items()}
    folder=HERE.relative_to(ROOT).as_posix()
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',producer,'--',folder],text=True).splitlines()
    own={name for name in tracked if str(PurePosixPath(name).parent)==folder}
    shared={name for name in legacy.sources() if str(PurePosixPath(name).parent)!=folder}
    require(set(source)==own|shared,'Original legacy observer manifest incomplete')
    for name,expected in source.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected,
                'Original legacy producer source differs: '+name)
    for name in ('original.py','cases-v2.json','recording_inputs.py','stage_original.py','Playback.h','Driver.cpp'):
        require(source[folder+'/'+name]==sha_lf(HERE/name),'Current legacy reader or case protocol differs from producer')
    return source


def module_audit(out,recorded,expected,case):
    root=PureWindowsPath(json.loads((out/'invocation.json').read_text())['argv'][0]).parent
    bindings=json.loads((out/'mesa-bindings.json').read_text());runtime=bindings['runtime']
    lock_path=ROOT/'Tests/Production/mesa-ucrt64.lock.json';lock=json.loads(lock_path.read_text())
    require(runtime['lock_sha256']==digest(lock_path) and
            {p['name']:p['sha256'] for p in runtime['packages']}=={p['name']:p['sha256'] for p in lock['packages']},
            'Original legacy Mesa package pins differ')
    mesa={PurePosixPath(name).name.casefold():item['sha256'] for name,item in runtime['files'].items()
          if name.lower().endswith('.dll')}
    effective={name.casefold():item['effective_sha256'] for name,item in bindings['bindings'].items()}
    actual={str(PureWindowsPath(line)).casefold() for line in (out/'renderer-modules.txt').read_text().splitlines()
            if PureWindowsPath(line).suffix.lower() in ('.dll','.exe')}
    require(actual=={str(PureWindowsPath(item['path'])).casefold() for item in recorded['loaded_modules']},
            'Original legacy DLL inventory differs from actual paths')
    names=set()
    for item in recorded['loaded_modules']:
        path=PureWindowsPath(item['path']);name=path.name.casefold();names.add(name)
        if path.is_relative_to(root):
            allowed={effective.get(name,mesa[name])} if name in mesa else expected.get(name,set())
            require(item['sha256'] in allowed,'Executed original legacy DLL differs: '+name)
        else:
            require(len(path.parts)>1 and path.parts[1].casefold()=='windows','Unrecorded external original legacy DLL')
    required={'orbiter.exe','oglclient.dll','opengl32.dll','productioncockpitdriver.dll','deltaglider.dll','shuttlea.dll'}
    if 'ShuttlePB' in legacy.ships((ROOT/'Scenarios'/case['scenario']).read_text()).values():required.add('shuttlepb.dll')
    require(required<=names,'Required original legacy application, renderer or vessel DLL absent')


def audit_profile(base,profile,config,producer,preserved_root=None,metadata=None):
    configuration,math_profile=profile.split('-',1)
    capture=base/'legacy-stations-original';report=json.loads((capture/'capture.json').read_text())
    require(report['status']=='captured-awaiting-four-profile-audit' and not report['failures'] and
            report['host']=='original-windows' and report['producer_commit']==producer and
            report['configuration']==configuration and report['math_profile']==math_profile and
            report['application_source']==config['application_source'] and
            report['protocol']==2 and report['settings_sha256_lf']==sha_lf(HERE/'cases-v2.json') and
            report['preserved_runtime_unchanged'] and report['observer_sources_unchanged'],
            'Original legacy profile failed, incomplete or misidentified: '+profile)
    sources=producer_sources(report,producer)
    names={case['id'] for case in config['cases']}
    require(set(report['cases'])==names,'Original legacy case set incomplete')
    runtime_root=base/'legacy-station-original-runtime'
    runtime=json.loads((runtime_root/'control-reference-runtime.json').read_text())
    preserved=json.loads((runtime_root/'test-runtime.json').read_text())
    if preserved_root:
        for name in ('test-runtime.json','control-reference-runtime.json'):
            require(sha_lf(runtime_root/name)==sha_lf(preserved_root/name),'Original legacy runtime metadata differs from retained SDK/client')
    if metadata:
        require(sha_lf(runtime_root/'test-runtime.json')==metadata['runtime_metadata_sha256_lf'] and
                sha_lf(runtime_root/'control-reference-runtime.json')==metadata['client_metadata_sha256_lf'],
                'Original legacy metadata differs from independently audited pins')
    provenance=json.loads((ROOT/'Tests/Production/Cockpit/Reference/provenance.json').read_text())
    require(preserved['source_commit']==runtime['application_source']==provenance['application_source']==config['application_source'] and
            runtime['runtime_archive_sha256']==provenance['runtime_artifacts'][configuration]['sha256'] and
            runtime['client_archive_sha256']==provenance['artifacts'][configuration]['sha256'] and runtime==report['runtime'],
            'Original legacy preserved application/SDK/client provenance differs')
    protected={name:value for name,value in {**preserved['files'],**runtime['client_files_sha256']}.items() if name!=OBSERVER}
    require(protected==report['preserved_files_sha256'],'Original legacy preserved file set differs')
    if preserved_root:
        for name,expected in protected.items():
            require(digest(preserved_root/safe_name(name))==expected,'Retained original SDK/client drift: '+name)
    observer=runtime_root/OBSERVER
    require(digest(observer)==report['observer_sha256'],'Executed original legacy observer differs')
    build=base/'legacy-station-driver'
    cache=dict(line.split('=',1) for line in (build/'CMakeCache.txt').read_text().splitlines()
               if '=' in line and not line.startswith(('#','//')))
    require(cache['CMAKE_BUILD_TYPE:STRING']==configuration,'Actual original legacy observer build configuration differs')
    commands=json.loads((build/'compile_commands.json').read_text())
    require(len(commands)==1 and PureWindowsPath(commands[0]['file']).name=='Driver.cpp' and
            PureWindowsPath(commands[0]['file']).parent.name=='LegacyStations' and
            re.findall(r'(?:^|\s)[/-](MDd?)(?=\s|$)',commands[0]['command'])==['MDd' if configuration=='Debug' else 'MD'],
            'Actual original legacy observer source or CRT linkage differs')
    modules={}
    for name,value in {**protected,OBSERVER:report['observer_sha256']}.items():
        modules.setdefault(PurePosixPath(safe_name(name)).name.casefold(),set()).add(value)
    cases={}
    for case in config['cases']:
        captured=report['cases'][case['id']]
        require(captured['scenario']==case['scenario'] and len(captured['runs'])==2,'Original legacy repeated case incomplete')
        runs=[];paths=[]
        for repeat,recorded in enumerate(captured['runs'],1):
            out=capture/(case['id']+'-'+str(repeat));paths.append(out)
            for name,expected in recorded['files_sha256'].items():
                require(digest(out/safe_name(name))==expected,'Original legacy captured artifact changed: '+name)
            actual=legacy.inspect_artifacts(out,case,config)
            require(all(recorded[key]==value for key,value in actual.items()),'Recomputed original legacy process outcome differs')
            invocation=json.loads((out/'invocation.json').read_text())
            require(invocation['driver_sha256']==report['observer_sha256'],'Original staged legacy observer differs')
            require([arg for arg in invocation['argv'] if arg.startswith('--scenariox=')]==
                    ['--scenariox='+str(PureWindowsPath(case['scenario']).with_suffix(''))],
                    'Actual original scenario argument differs from its Windows-native entry point')
            for name,expected in config['resources_sha256_lf'].items():
                # Before execution, stage() hashes all raw config/mesh bytes.
                frozen=subprocess.check_output(['git','-C',str(ROOT),'show',config['application_source']+':'+name])
                lf=frozen.replace(b'\r\n',b'\n')
                allowed={hashlib.sha256(lf).hexdigest(),hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest()}
                require(invocation['input_sha256'][name] in allowed,'Executed original legacy source config/mesh differs: '+name)
            require(actual['actual_math']==(out/'math-profile.txt').read_text().strip() and
                    (math_profile!='sse2' or actual['actual_math']=='sse2'),'Actual original legacy CRT selection differs')
            module_audit(out,recorded,modules,case)
            runs.append({key:actual[key] for key in ('declared_vessels','finalized_ticks','all_vessel_rows','docking_rows',
                       'legacy_initial_capabilities','actual_math','renderer','recording_files','playback_rows','playback_vessels')})
        require(runs[0]['actual_math']==runs[1]['actual_math'],'Original legacy repeat changed CRT implementation')
        for name in ('stock-vessel-state.csv','stock-vessel-docks.csv','stock-playback.csv','camera.csv'):
            require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Original legacy repeat trace differs')
        similarity=legacy.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
        require(similarity>=config['image_ssim_minimum'] and similarity==captured['repeat_ssim'],
                'Recomputed original legacy repeat image score differs or fails')
        cases[case['id']]=dict(scenario=case['scenario'],runs=runs,repeat_ssim=similarity,camera_byte_identical=True)
    control_path=capture/'gate-control.json';control=json.loads(control_path.read_text())
    expected_controls={'missing_background_iss','missing_background_module1','missing_docking_port','duplicate_docking_port',
        'changed_iss_capabilities','nonfinite_state','shifted_clock','missing_final_tick','changed_scenario',
        'rewritten_scenario_line_endings','incomplete_teardown','wrong_renderer'}
    require(control['status']=='passed' and control['original_capture_unchanged'] and len(control['controls'])==12 and
            {item['control'] for item in control['controls']}==expected_controls,'Original legacy damaged-evidence controls incomplete')
    gate_source=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+HERE.relative_to(ROOT).as_posix()+'/Gate.Test.py'])
    gate_lf=gate_source.replace(b'\r\n',b'\n')
    require(control['source_sha256'] in {hashlib.sha256(gate_lf).hexdigest(),
            hashlib.sha256(gate_lf.replace(b'\n',b'\r\n')).hexdigest()},'Original legacy gate source differs')
    positive=legacy.inspect_artifacts(capture/'legacy_stations_3-1',config['cases'][2],config)
    require(control['positive']==positive,'Original legacy gate positive capture differs')
    playback_control=json.loads((capture/'playback-gate-control.json').read_text())
    require(playback_control['status']=='passed' and playback_control['original_capture_unchanged'] and
            {row['control'] for row in playback_control['controls']}=={'missing_position_stream','changed_recording',
                'false_playback_flag','missing_nonfocus_flag','wrong_entry_point'} and len(playback_control['controls'])==5,
            'Original playback controls incomplete')
    playback_source=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+HERE.relative_to(ROOT).as_posix()+'/PlaybackGate.Test.py'])
    playback_lf=playback_source.replace(b'\r\n',b'\n')
    require(playback_control['source_sha256'] in {hashlib.sha256(playback_lf).hexdigest(),
            hashlib.sha256(playback_lf.replace(b'\n',b'\r\n')).hexdigest()},'Original playback control source differs')
    playback_positive=legacy.inspect_inputs(capture/'legacy_stations_4-1',config['cases'][3],config,legacy.rows)
    require(playback_control['positive']==playback_positive,'Original actual playback control capture differs')
    return dict(capture_sha256=digest(capture/'capture.json'),observer_sha256=digest(observer),
        source_manifest_sha256=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        runtime_metadata_sha256_lf=sha_lf(runtime_root/'test-runtime.json'),
        client_metadata_sha256_lf=sha_lf(runtime_root/'control-reference-runtime.json'),
        gate_sha256=digest(control_path),playback_gate_sha256=digest(capture/'playback-gate-control.json'),
        preserved_files=len(protected),cases=cases)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts','download-manifest','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    for name in ('preserved-debug','preserved-release','metadata-lock'):p.add_argument('--'+name,type=lambda v:Path(v).resolve())
    p.add_argument('--producer-commit',required=True)
    a=p.parse_args();config=legacy.settings();require(not a.output.exists(),'Original legacy audit output exists')
    require(re.fullmatch('[0-9a-f]{40}',a.producer_commit),'Original legacy producer must be immutable')
    require((a.preserved_debug and a.preserved_release) or a.metadata_lock,'Independent retained SDK/client roots or audited metadata pins required')
    pins=json.loads(a.metadata_lock.read_text()) if a.metadata_lock else None
    if pins:
        require(pins['status']=='audited-original-observations' and pins['automatic_refresh'] is False and
                pins['producer_commit']==a.producer_commit and pins['application_source']==config['application_source'],
                'Original legacy metadata pins are not independently audited')
    downloads=json.loads(a.download_manifest.read_text())
    profiles={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
    require(downloads['status']=='passed' and downloads['source_commit']==a.producer_commit and
            len(downloads['artifacts'])==4 and {item['profile'] for item in downloads['artifacts']}==profiles,
            'Original legacy archive matrix incomplete')
    result=dict(status='failed',phase6_complete=False,producer_commit=a.producer_commit,
        application_source=config['application_source'],verifier_sha256=digest(Path(__file__)),
        download_manifest_sha256=digest(a.download_manifest),profiles={},build_pairs={},native_admission_qualified=False)
    try:
        for profile in sorted(profiles):
            configuration=profile.split('-',1)[0];entry=next(item for item in downloads['artifacts'] if item['profile']==profile)
            archive=ROOT/safe_name(entry['path'])
            require(entry['name']=='original-legacy-stations-v2-'+profile and archive.stat().st_size==entry['bytes'] and
                    digest(archive)==entry['sha256'],'Original legacy archive transport differs')
            members=verify_archive(archive,a.artifacts/profile)
            if pins:
                frozen=next(item for item in pins['artifacts'] if item['profile']==profile)
                require(all(entry[key]==frozen[key] for key in ('id','name','bytes','sha256')),'Original legacy pinned transport differs')
            result['profiles'][profile]=audit_profile(a.artifacts/profile,profile,config,a.producer_commit,
                getattr(a,'preserved_'+configuration.lower()),pins['runtime_metadata'][configuration] if pins else None)
            result['profiles'][profile].update(archive_sha256=entry['sha256'],archive_members_verified=members)
        for math_profile in ('automatic','sse2'):
            pairs={}
            for case in config['cases']:
                paths=[a.artifacts/(c+'-'+math_profile)/'legacy-stations-original'/(case['id']+'-1') for c in ('Debug','Release')]
                errors=compare_state(*paths,config)
                require((paths[0]/'camera.csv').read_bytes()==(paths[1]/'camera.csv').read_bytes(),
                        'Original legacy Debug/Release camera differs')
                similarity=legacy.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(similarity>=config['image_ssim_minimum'],'Original legacy Debug/Release full-frame image gate fails')
                pairs[case['id']]=dict(maxima=errors,ssim=similarity,camera_byte_identical=True)
            result['build_pairs'][math_profile]=pairs
        runs=[run for profile in result['profiles'].values() for case in profile['cases'].values() for run in case['runs']]
        require(len(runs)==32,'Original legacy process matrix incomplete')
        result.update(status='passed',processes=len(runs),presentations=len(runs)*config['frames'],
            all_vessel_rows=sum(run['all_vessel_rows'] for run in runs),docking_rows=sum(run['docking_rows'] for run in runs))
    except BaseException as error:result['error']=str(error);raise
    finally:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','processes','presentations','all_vessel_rows','docking_rows')}))


if __name__=='__main__':main()
