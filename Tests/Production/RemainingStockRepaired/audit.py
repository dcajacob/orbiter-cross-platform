#!/usr/bin/env python3
"""Independently audit the complete explicitly repaired four-profile Windows candidate."""
import argparse
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path,PurePosixPath,PureWindowsPath
import re
import stat
import subprocess
import sys
import zipfile

import capture
from pe_symbols import PE
from behavior_suite import quaternion,quaternion_angle
from verify_original import compare_state

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
OBSERVER='Modules/Plugin/ProductionCockpitDriver.dll'
REPLACED={'Modules/Atlantis_Tank.dll','Modules/Dragonfly.dll','Modules/Plugin/OGLClient.dll',OBSERVER}
SIDECARS={str(PurePosixPath(name).with_suffix(suffix)) for name in REPLACED for suffix in ('.pdb','.ilk')}
require=capture.require;sha=capture.sha;sha_lf=capture.sha_lf


def checksum(body):return hashlib.sha256(body).hexdigest()
@lru_cache(maxsize=None)
def git(producer,name):return subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+safe(name)])


def safe(name):
    path=PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,
            'Unsafe evidence path: '+name)
    return name


def raw_source_hashes(producer,name):
    body=git(producer,name).replace(b'\r\n',b'\n')
    return {checksum(body),checksum(body.replace(b'\n',b'\r\n'))}


def verifier_inputs():
    paths={Path(__file__).resolve()}
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if ROOT in path.parents and path.suffix=='.py':paths.add(path)
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}


def archive_members(archive,root):
    seen=set();members={}
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            name=safe(member.filename)
            require(name not in seen and not stat.S_ISLNK(member.external_attr>>16),'Duplicate or symlink archive member')
            seen.add(name)
            if member.is_dir():continue
            actual=root/name
            require(actual.is_file() and sha(actual)==checksum(source.read(member)),
                    'Decoded member differs from exact artifact ZIP: '+name)
            members[name]=sha(actual)
    require(members,'Empty Windows evidence artifact')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(actual==set(members),'Unmanifested decoded artifact file')
    return members


def preserved(root):
    metadata=json.loads((root/'test-runtime.json').read_text())
    client=json.loads((root/'control-reference-runtime.json').read_text())
    require(metadata['source_commit']==client['application_source']==BASE,'Independent original application/SDK source differs')
    expected={**metadata['files'],**client['client_files_sha256']}
    expected.update({name:sha(root/name) for name in ('test-runtime.json','control-reference-runtime.json')})
    require(all(sha(root/safe(name))==value for name,value in expected.items()),'Independent retained original bytes changed')
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==set(expected),
            'Independent original package has unrecorded files')
    require(PE(root/'Orbiter.exe').width==8,'Original application is not native x64')
    return expected


def source_variant(root,producer):
    report=json.loads((root/'source-variant.json').read_text())
    require(report['schema']==1 and report['status']=='prepared-awaiting-build-and-independent-audit' and
            report['protocol']=='remaining-stock-repaired-sources-v2' and
            report['producer_commit']==producer and report['original_application_and_sdk_source']==BASE and
            report['complete_scenes']==38 and report['declared_classes']==19 and report['recording_files']==36 and
            report['staged_original_module_files_unchanged_except_declared_changes'] and
            report['repository_scene_class_and_recording_inputs_verified'] and not report['runtime_assets_staged'] and
            not report['native_admission_qualified'] and not report['phase6_complete'],'Module source variant misidentified')
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--',
        'Src/Vessel/Atlantis','Src/Vessel/Dragonfly'],text=True).splitlines()
    original={name:git(BASE,name) for name in paths};expected=dict(original)
    tank='Src/Vessel/Atlantis/Atlantis_Tank/Atlantis_Tank.cpp'
    body=original[tank].decode('cp1252').replace('\r\n','\n')
    old='\tif (GetAltitude() < 0.0) oapiDeleteVessel (GetHandle());'
    require(body.count(old)==1,'Original tank callback differs')
    expected[tank]=body.replace(old,
        '\t// The orbiter owns this propellant while connected, including on the pad.\n'
        '\tif (!GetDockStatus (GetDockHandle (0)) && GetAltitude() < 0.0)\n'
        '\t\toapiDeleteVessel (GetHandle());').encode('cp1252')
    dragonfly={'Src/Vessel/Dragonfly/'+name for name in ('instruments.cpp','instruments.h','WglContext.h','WglBitmapTarget.h','Esystems.cpp')}
    for name in dragonfly:expected[name]=git(producer,name)
    # Independently derive the sole electrical delta from the frozen original,
    # rather than accepting an arbitrary producer's electrical source.
    electrical='Src/Vessel/Dragonfly/Esystems.cpp'
    prior=original[electrical].replace(b'\r\n',b'\n')
    anchor=b'  Volts=28.8;\n  power_load=r_amp;'
    require(prior.count(anchor)==1,'Original fuel-cell initialization boundary differs')
    repaired=prior.replace(anchor,b'  Volts=28.8;\n  Amperes=0; // No previous current before the first refresh.\n  power_load=r_amp;',1)
    require(expected[electrical].replace(b'\r\n',b'\n')==repaired and
            report['initialization_repair']==dict(field='FCell::Amperes',initial_value=0,
                policy='Define previous current before the first thermal update; retain every original update formula and callback order.'),
            'Electrical source exceeds the one declared initial-current assignment')
    original_hashes={name:checksum(body) for name,body in original.items()}
    staged={name:checksum(body) for name,body in expected.items()}
    actual={p.relative_to(root/'source').as_posix():sha(p) for p in (root/'source').rglob('*') if p.is_file()}
    require(report['original_files_sha256']==original_hashes and report['staged_files_sha256']==staged==actual,
            'Exact original/repaired module source or resource closure differs')
    changes={name:dict(original_sha256=original_hashes.get(name),repaired_sha256=value)
             for name,value in staged.items() if original_hashes.get(name)!=value}
    require(set(changes)=={tank,*dragonfly} and report['declared_changes']==changes,'Module changes exceed six declared platform/lifetime/initial-current paths')
    require(report['preparer_sha256'] in raw_source_hashes(producer,'Tests/Production/RemainingStockRepaired/prepare_sources.py'),
            'Actual source preparer producer differs')
    require(report['current_dragonfly_producer_sha256']=={name:staged[name] for name in dragonfly},'Dragonfly source producer differs')
    return dict(manifest_sha256=sha(root/'source-variant.json'),original_files=len(original),staged_files=len(actual),changes=changes)


def source_closure(values,producer,minimum):
    require(set(minimum)<=set(values),'Evidence source closure omits required owning inputs')
    for name,value in values.items():
        require(checksum(git(producer,name).replace(b'\r\n',b'\n'))==value,'Immutable producer source differs: '+name)


def runtime_variant(root,producer,configuration,original_root):
    path=root/'build.json';build=json.loads(path.read_text());runtime=root/'runtime'
    require(build['schema']==1 and build['status']=='built-awaiting-runtime-and-independent-audit' and
            build['producer_commit']==producer and build['configuration']==configuration and
            build['protocol']=='remaining-stock-repaired-v1' and build['original_application_and_sdk_source']==BASE and
            build['preserved_package_unchanged'] and not build['native_admission_qualified'] and not build['phase6_complete'],
            'Repaired build incomplete or misidentified')
    require((runtime/'runtime-variant.json').read_bytes()==path.read_bytes(),'Runtime manifest differs from actual build report')
    before=preserved(original_root)
    require(build['preserved_package_sha256']==before,'Original package closure differs from independent retained bytes')
    for name in ('test-runtime.json','control-reference-runtime.json'):
        require((runtime/name).read_bytes()==(original_root/name).read_bytes(),'Original package metadata was replaced')
    subset={p.relative_to(runtime).as_posix():sha(p) for p in runtime.rglob('*') if p.is_file() and p.name!='runtime-variant.json'}
    after=dict(before);after.update(subset)
    require(after==build['runtime_files_sha256'],'Actual uploaded replacement files do not reconstruct the explicit complete runtime manifest')
    require(all(name in REPLACED|SIDECARS or name.startswith('Modules/OGLClient/') or before.get(name)==value
                for name,value in after.items()),'An undeclared original application/SDK/module/configuration file changed')
    require(set(before)<=set(after) and REPLACED<=set(subset),'Original file missing or replacement binary absent')
    changes={name:dict(original_sha256=before.get(name),variant_sha256=value)
             for name,value in after.items() if before.get(name)!=value}
    require(changes==build['declared_runtime_changes'] and REPLACED<=set(changes),'Declared runtime delta differs from actual replacement bytes')
    require(all(name not in changes for name in before if name.startswith('Orbitersdk/')) and
            after['Orbiter.exe']==before['Orbiter.exe'] and after['Modules/Atlantis_SRB.dll']==before['Modules/Atlantis_SRB.dll'],
            'Original application, SDK or running SRB changed')
    require(all(not name.lower().endswith(('.dll','.exe','.so','.lib')) for name in changes if name.startswith('Modules/OGLClient/')),
            'Executable/import library is hidden among client shader/license resources')
    require(all(PE(runtime/name).width==8 for name in REPLACED),'A replacement application module is not native x64')
    sources=build['source_sha256_lf']
    ledger=json.loads(git(producer,'Tests/Production/phase3-extraction.lock.json'))['files']
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',producer,'--',
        'OVP/OGLClient','Tests/Production/RemainingStock','Tests/Production/RemainingStockRepaired'],text=True).splitlines()
    source_closure(sources,producer,set(ledger)|set(tracked)|{'Tests/Production/RemainingStockRepaired/CMakeLists.txt',
        'Tests/Production/RemainingStockRepaired/PreservedSdkTypes.h','Tests/Production/StockVessels/Observation.h',
        'Tests/Production/RemainingStock/Details.h','Tests/Production/RemainingStock/Driver.cpp'})
    staged=source_variant(root/'module-sources',producer)
    require(build['module_source_manifest_sha256']==staged['manifest_sha256'],'Built module source manifest differs')
    observer=git(producer,'Tests/Production/RemainingStock/Driver.cpp').replace(b'\r\n',b'\n')
    old=b'require(frames==60,"Incomplete original stock observation")'
    require(observer.count(old)==1,'Original passive observer contract differs')
    compiled=observer.replace(old,b'require(frames==960,"Incomplete repaired stock observation")')
    require((root/'observer/Driver.cpp').read_bytes()==compiled and
            build['observer_source_variant']['original_sha256']==checksum(observer) and
            build['observer_source_variant']['compiled_sha256']==checksum(compiled),
            'Passive observer changes exceed the explicit 960-frame validation')
    compiled_inputs=compile_evidence(root,build,configuration)
    srb=root/'cmake/import-only/Atlantis_SRB.dll'
    require(sha(srb)==build['import_only_srb_sha256'] and PE(srb).exports()==PE(original_root/'Modules/Atlantis_SRB.dll').exports(),
            'Actual import-only SRB public symbols differ from the running original SRB')
    require(PE(runtime/'Modules/Atlantis_Tank.dll').imports().get('atlantis_srb.dll',set())<=PE(srb).exports(),
            'Tank import spellings do not bind the actual original SRB')
    for name in ('Modules/Atlantis_Tank.dll','Modules/Dragonfly.dll'):
        require(PE(runtime/name).width==8 and PE(runtime/name).exports()==PE(original_root/name).exports(),
                'Repaired module architecture or public export spellings differ')
    controls=json.loads((root/'runtime-file-controls.json').read_text())
    require(controls['status']=='passed' and controls['actual_build_unchanged'] and
            controls['actual_build_manifest_sha256']==sha(path) and controls['source_sha256'] in
            raw_source_hashes(producer,'Tests/Production/RemainingStockRepaired/RuntimeFiles.Test.py') and
            {r['control'] for r in controls['controls']}=={'changed_application','changed_original_srb','changed_public_sdk',
                'missing_original_configuration','unrecorded_vessel_module','unrecorded_root_library'} and
            len(controls['controls'])==6 and all(r['reason'] for r in controls['controls']),
            'Protected original-runtime controls incomplete')
    return build,dict(build_manifest_sha256=sha(path),runtime_manifest_sha256=sha(runtime/'runtime-variant.json'),
        actual_original_files_verified=len(before),actual_runtime_files=len(after),declared_changes=changes,
        source_variant=staged,**compiled_inputs,runtime_file_controls_sha256=sha(root/'runtime-file-controls.json'))


def compile_evidence(root,build,configuration):
    cache=root/'cmake/CMakeCache.txt';commands=root/'cmake/compile_commands.json'
    require(sha(cache)==build['cmake_cache_sha256'] and sha(commands)==build['compile_commands_sha256'],
            'Actual MSVC configuration/compile commands changed')
    flags=dict(line.split('=',1) for line in cache.read_text().splitlines() if '=' in line and not line.startswith(('#','//')))
    require(flags['CMAKE_BUILD_TYPE:STRING']==configuration,'Actual compiler configuration differs')
    configure=next(args for args in build['commands'] if args[0]=='cmake' and '-S' in args)
    variables={arg.split('=',1)[0][2:]:arg.split('=',1)[1] for arg in configure if arg.startswith('-D') and '=' in arg}
    windows_repo=PureWindowsPath(configure[configure.index('-S')+1]).parents[2]
    staged_root=PureWindowsPath(variables['ORBITER_REPAIRED_SOURCES'])
    observer_path=PureWindowsPath(variables['ORBITER_REPAIRED_OBSERVER'])
    entries=json.loads(commands.read_text());seen=set();client_cpp=0
    expected={'Src/Vessel/Atlantis/Atlantis_SRB/Atlantis_SRB.cpp','Src/Vessel/Atlantis/Common.cpp',
        'Src/Vessel/Atlantis/Atlantis_Tank/Atlantis_Tank.cpp',
        *('Src/Vessel/Dragonfly/'+name+'.cpp' for name in ('Dragonfly','Internal','instruments','Matrix','quaternion','vectors','Hsystems','Thermal','Esystems'))}
    for entry in entries:
        file=PureWindowsPath(entry['file']);command=entry['command']
        if file.suffix.lower() not in ('.cpp','.c'):continue
        if file.is_relative_to(staged_root) or file==observer_path or file.is_relative_to(windows_repo/'OVP/OGLClient') or 'OGLClient.dir' in command:
            require(re.findall(r'(?:^|\s)[/-](MDd?)(?=\s|$)',command)==['MDd' if configuration=='Debug' else 'MD'],
                    'Actual module/client/observer CRT differs')
        if file.is_relative_to(staged_root):
            name=file.relative_to(staged_root).as_posix();require(name not in seen,'Duplicate original module translation unit');seen.add(name)
        elif file==observer_path:seen.add('observer')
        if 'OGLClient.dir' in command and file.suffix.lower()=='.cpp':
            require('PreservedSdkTypes.h' in command and '/FI' in command,'Actual current client lacks the explicit original-SDK scalar binding')
            client_cpp+=1
    require(seen==expected|{'observer'} and client_cpp>20,'Actual original module/client/observer compile closure incomplete')
    return dict(cmake_cache_sha256=sha(cache),compile_commands_sha256=sha(commands),
                compiler_inputs=len(entries),client_cpp_inputs=client_cpp)


def independent_mesa(root,producer):
    manifest=json.loads((root/'mesa-runtime.json').read_text())
    lock=json.loads(git(producer,'Tests/Production/mesa-ucrt64.lock.json'))
    require(manifest['lock_sha256'] in raw_source_hashes(producer,'Tests/Production/mesa-ucrt64.lock.json') and
            manifest['packages']==[dict(name=p['name'],sha256=p['sha256']) for p in lock['packages']],
            'Independent Mesa package identities differ from the immutable lock')
    packages={p['name'] for p in lock['packages']}
    for name,value in manifest['files'].items():
        require(value['package'] in packages and sha(root/safe(name))==value['sha256'],
                'Independent pinned Mesa DLL/license bytes changed: '+name)
    require({'opengl32.dll','libgallium_wgl.dll','zlib1.dll'}<=set(manifest['files']),
            'Independent Mesa closure lacks WGL/zlib providers')
    imports={}
    for name in manifest['files']:
        if name.lower().endswith('.dll'):
            symbols=PE(root/name).imports().get('zlib1.dll',set())
            if symbols:imports[name]=sorted(symbols)
    return manifest,imports


def loaded_modules(out,recorded,runtime,case,config,mesa,mesa_imports,original_root):
    invocation=json.loads((out/'invocation.json').read_text())
    executable=PureWindowsPath(invocation['argv'][0]);staged=executable.parent
    require(executable.is_absolute() and executable.name=='Orbiter.exe','Executed application path differs')
    bindings=json.loads((out/'mesa-bindings.json').read_text())
    expected_bindings={}
    mesa_zlib=mesa['files']['zlib1.dll']['sha256']
    if runtime.get('zlib1.dll',mesa_zlib)!=mesa_zlib:
        exports=PE(original_root/'zlib1.dll').exports()
        require(all(set(values)<=exports for values in mesa_imports.values()),'Original zlib lacks actual pinned Mesa imports')
        expected_bindings['zlib1.dll']=dict(
            policy='retain original source-built application zlib; exact C exports audited',
            effective_sha256=runtime['zlib1.dll'],mesa_package_sha256=mesa_zlib,imports=mesa_imports)
    require(bindings==dict(runtime=mesa,bindings=expected_bindings),
            'Executed Mesa files or original-zlib binding differ from independent retained bytes')
    expected=dict(runtime)
    for body,names in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),
                       'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
        for name in names:
            expected['Modules/Celbody/'+body+'/Atmosphere/'+name+'.dll']=runtime['Modules/Celbody/Atmosphere/'+name+'.dll']
    for name,value in mesa['files'].items():
        if name.lower().endswith('.dll'):
            expected[name]=expected_bindings.get(name,{}).get('effective_sha256',value['sha256'])
    expected={PureWindowsPath(name):value for name,value in expected.items()}
    trace=[PureWindowsPath(line.strip()) for line in (out/'renderer-modules.txt').read_text().splitlines() if line.strip()]
    require(all(p.is_absolute() and p.suffix.lower() in ('.dll','.exe') for p in trace) and len(trace)==len(set(trace)),
            'Invalid or duplicate loaded module trace')
    require({PureWindowsPath(row['path']) for row in recorded}==set(trace) and len(recorded)==len(trace),
            'Captured loaded identities differ from the raw process module trace')
    loaded={};system={}
    for row in recorded:
        path=PureWindowsPath(row['path']);name=path.name.casefold();value=row['sha256']
        require(name not in loaded and re.fullmatch('[0-9a-f]{64}',value),'Duplicate or invalid loaded DLL identity')
        loaded[name]=value
        if path.is_relative_to(staged):
            require(expected.get(path.relative_to(staged))==value,'Actual executed DLL differs from retained runtime/Mesa: '+str(path))
        else:
            require(path.is_relative_to(PureWindowsPath('C:/Windows')),'Unrecorded external module provider: '+str(path))
            system[str(path)]=value
    required={'orbiter.exe','oglclient.dll','productioncockpitdriver.dll','opengl32.dll','libgallium_wgl.dll'}
    required|={PurePosixPath(config['classes'][kind]['original_module']).name.casefold()
               for kind in set(case['declared_vessels'].values()) if config['classes'][kind]['module']}
    require(required<=set(loaded),'Actual declared factory/application/client/observer/Mesa was not loaded')
    return system


def expected_configuration(producer):
    text=git(producer,'Tests/Production/Fixtures/Orbiter.cfg').decode('ascii').replace('\r\n','\n')
    text=text.replace('ProductionReferenceDriver','ProductionBehaviorDriver')
    text+='\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n'
    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
        require(text.count(line)==1,'Producer fixture propagator override differs');text=text.replace(line,'')
    return text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+\
        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'


def audit_profile(root,profile,config,producer,original_root,mesa,mesa_imports):
    capture_root=root/'remaining-stock-repaired';build_root=root/'remaining-stock-repaired-build'
    report=json.loads((capture_root/'capture.json').read_text());configuration,math_profile=profile.split('-',1)
    require(report['status']=='captured-awaiting-independent-audit' and report['host']=='repaired-original-windows' and
            report['protocol']==config['protocol'] and report['producer_commit']==producer and
            report['original_application_and_sdk_source']==BASE and report['configuration']==configuration and
            report['math_profile']==math_profile and report['settings_sha256_lf']==sha_lf(capture.shared.CASE_FILE) and
            report['protocol_sha256_lf']==sha_lf(HERE/'protocol.json') and report['runtime_variant_unchanged'] and
            report['observer_sources_unchanged'] and report['actual_original_simulation_data_unchanged'] and not report['failures'] and
            not report['native_admission_qualified'] and not report['phase6_complete'] and
            set(report['cases'])=={c['id'] for c in config['cases']},'Repaired full profile incomplete or misidentified')
    build,built=runtime_variant(build_root,producer,configuration,original_root)
    capture.data_inputs.validate(report['actual_original_simulation_data'])
    for name,value in report['actual_original_simulation_data']['lock_sha256_lf'].items():
        require(value==checksum(git(producer,'Tests/Production/'+name).replace(b'\r\n',b'\n')),
                'Actual data witness lock differs from immutable producer')
    runtime=build['runtime_files_sha256'];sources=report['source_sha256_lf']
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',producer,'--',
        'Tests/Production/RemainingStockRepaired','Tests/Production/RemainingStock'],text=True).splitlines()
    source_closure(sources,producer,set(tracked)|{
        'Tests/Production/Client/run_client.py','Tests/Production/Client/compare_client.py',
        'Tests/Production/StockVessels/Observation.h','Tests/Production/StockVessels/original.py',
        '.github/workflows/repaired-remaining-stock.yml'})
    require(set(sources)==set(report['source_raw_sha256']) and
            all(value in raw_source_hashes(producer,name) for name,value in report['source_raw_sha256'].items()),
            'Actual raw capture source differs from its immutable producer')
    for name in ('Tests/Production/RemainingStockRepaired/capture.py','Tests/Production/RemainingStockRepaired/protocol.json',
                 'Tests/Production/RemainingStockRepaired/data_inputs.py',
                 'Tests/Production/RemainingStock/original.py','Tests/Production/RemainingStock/inputs.py',
                 'Tests/Production/RemainingStock/cases.json','Tests/Production/Client/run_client.py',
                 'Tests/Production/Client/compare_client.py','Tests/Production/StockVessels/original.py'):
        require(sha_lf(ROOT/name)==sources[name],'Current independent trace reader differs from capture producer: '+name)
    require(report['runtime_files_sha256']==runtime and report['observer_sha256']==runtime[OBSERVER] and
            report['runtime_variant_manifest_sha256']==built['runtime_manifest_sha256'],
            'Executed full runtime/observer differs from audited build')
    expected_variant=dict(protocol=config['protocol'],protocol_sha256_lf=report['protocol_sha256_lf'],
        original_application_and_sdk_source=BASE,producer_commit=producer,
        runtime_variant_manifest_sha256=built['runtime_manifest_sha256'],frames=960,fixed_step=1/64,capture_tick=800)
    expected_inputs={name:value for name,value in build['preserved_package_sha256'].items()
                     if name.startswith(('Config/','Meshes/'))}
    results={};maths=set();system={}
    for case in config['cases']:
        recorded_case=report['cases'][case['id']]
        require(recorded_case['scenario']==case['scenario'] and len(recorded_case['runs'])==2,'Complete repaired scene repetition missing')
        paths=[];runs=[]
        for repeat,recorded in enumerate(recorded_case['runs'],1):
            out=capture_root/(case['id']+'-'+str(repeat));paths.append(out)
            for name,value in recorded['files_sha256'].items():
                require(sha(out/safe(name))==value,'Raw captured repaired bytes changed: '+name)
            actual=capture.inspect_artifacts(out,case,config)
            require(set(recorded)==set(actual)|{'loaded_modules'} and
                    all(recorded[key]==value for key,value in actual.items()),'Recomputed complete repaired observation differs')
            require((out/'Orbiter.cfg').read_bytes().replace(b'\r\n',b'\n')==expected_configuration(producer).encode('ascii'),
                    'Actual staged configuration differs beyond the explicit repaired fixture')
            require(json.loads((out/'reference-variant.json').read_text())==expected_variant,'Actual executed reference variant differs')
            require(json.loads((out/'actual-data-inputs.json').read_text())==report['actual_original_simulation_data'],
                    'Actual staged kernel/gravity/planet bytes differ from the verified original data source')
            invocation=json.loads((out/'invocation.json').read_text())
            require(invocation['case']==case and invocation['preserved_inputs_sha256']==expected_inputs and
                    all(invocation['input_sha256'][name]==value for name,value in expected_inputs.items()) and
                    invocation['driver_sha256']==runtime[OBSERVER] and invocation['argv'][1:]==[
                        '--scenariox='+str(PureWindowsPath(case['scenario']).with_suffix('')),
                        '--fixedstep=0.015625','--maxframes=960'],
                    'Actual unchanged original inputs/observer/clock arguments differ')
            require(set(invocation['data_profiles'])=={'stock-data.lock.json','standard-planets.lock.json'} and
                    all(value in raw_source_hashes(producer,'Tests/Production/'+name)
                        for name,value in invocation['data_profiles'].items()),'Pinned original data profiles differ')
            providers=loaded_modules(out,recorded['loaded_modules'],runtime,case,config,mesa,mesa_imports,original_root)
            for name,value in providers.items():system.setdefault(name,set()).add(value)
            require(math_profile!='sse2' or actual['actual_math']=='sse2','Actual repaired CRT path differs')
            maths.add(actual['actual_math'])
            runs.append({key:value for key,value in actual.items() if key not in ('files_sha256','renderer')})
        for name in (*capture.shared.TRACES,'camera.csv'):
            require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Repeated actual state/resource/playback/mesh/camera differs: '+name)
        score=capture.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
        require(score>=config['image_ssim_minimum'] and score==recorded_case['repeat_ssim'],'Repeated full-frame budget failed')
        results[case['id']]=dict(scenario=case['scenario'],runs=runs,repeat_ssim=score)
    require(len(maths)==1,'Actual CRT path changed between complete scenes')
    controls=json.loads((capture_root/'gate-control.json').read_text())
    names={'missing_background_vessel','missing_thruster','missing_tank','unknown_tank_owner','missing_attachment',
        'missing_mesh_slot','false_initial_playback','missing_position_recording','wrong_windows_entry_point',
        'changed_class_input','shifted_clock','missing_population_tick','missing_mesh_delivery_repair',
        'changed_mesh_delivery_provenance','forced_single_step_propagators','wrong_full_frame_tick',
        'incomplete_presentations','wrong_reference_variant','changed_actual_data_hash','missing_actual_planet_archive'}
    require(controls['status']=='passed' and controls['protocol']==config['protocol'] and controls['owning_capture_unchanged'] and
            len(controls['controls'])==20 and {row['control'] for row in controls['controls']}==names and
            all(row['reason'] for row in controls['controls']) and controls['source_sha256'] in
            raw_source_hashes(producer,'Tests/Production/RemainingStockRepaired/Gate.Test.py'),
            'Real complete repaired reader controls incomplete or from a different producer')
    require(controls['positive']==capture.inspect_artifacts(capture_root/'remaining_stock_003-1',config['cases'][2],config),
            'Actual owning positive control capture differs')
    clock_control=json.loads((capture_root/'clock-control.json').read_text())
    clock_names={'missing_tick','reordered_ticks','nonfinite_clock','system_clock_regression',
                 'different_vessel_snapshot','missing_clock_column','zero_system_step','zero_acceleration'}
    clock_positive=capture_root/'remaining_stock_003-1'
    require(clock_control['status']=='passed' and clock_control['owning_capture_unchanged'] and
            len(clock_control['controls'])==8 and {row['control'] for row in clock_control['controls']}==clock_names and
            all(row['reason'] for row in clock_control['controls']) and
            clock_control['source_sha256'] in raw_source_hashes(producer,'Tests/Production/RemainingStock/Clock.Test.py') and
            clock_control['reader_sha256'] in raw_source_hashes(producer,'Tests/Production/RemainingStock/clock_observation.py') and
            clock_control['positive']==capture.shared.inspect_clock(clock_positive,config['frames']) and
            clock_control['owning_capture_files_sha256']=={name:sha(clock_positive/name) for name in ('stock-clock.csv','stock-vessel-state.csv')},
            'Actual SDK clock reader controls or owning observations differ')
    return dict(capture_sha256=sha(capture_root/'capture.json'),actual_math=next(iter(maths)),build=built,cases=results,
        source_manifest_sha256=checksum(json.dumps(sources,sort_keys=True).encode()),
        gate_control_sha256=sha(capture_root/'gate-control.json'),
        captured_system_library_identities={name:sorted(values) for name,values in system.items()},
        system_library_scope='Paths and hashes recorded by the actual Windows process; system DLL bytes are not independently archived here.')


def detail_calibration(left,right):
    identities={'tick','object','index','to_parent','id','attached','resource_object','resource_index','resource_state',
                'resource_id','resource_seen_tick','present','template','name','visibility','playback','count'}
    maxima={}
    for name in capture.shared.TRACES[2:]:
        a=capture.shared.rows(left/name);b=capture.shared.rows(right/name)
        require(len(a)==len(b),'Paired complete detail row count differs')
        for x,y in zip(a,b):
            require(x.keys()==y.keys() and all(x[key]==y[key] for key in x if key in identities),
                    'Paired population/resource/attachment/playback/mesh identity differs')
            for key in x:
                if key not in identities:
                    maxima[name+':'+key]=max(maxima.get(name+':'+key,0),abs(float(x[key])-float(y[key])))
    return maxima


def camera_comparison(left,right,config):
    records=[capture.shared.rows(path/'camera.csv') for path in (left,right)]
    require(all(len(rows)==1 for rows in records),'Paired camera observation incomplete')
    a,b=[rows[0] for rows in records]
    require(all(math.isfinite(float(v)) for row in (a,b) for v in row.values()),'Nonfinite paired camera')
    position=math.dist([float(a[k]) for k in ('px','py','pz')],[float(b[k]) for k in ('px','py','pz')])
    rotation=quaternion_angle(quaternion(a),quaternion(b))
    require(position<=config['budgets']['position_m'] and rotation<=config['budgets']['rotation_rad'] and
            float(a['aperture'])==float(b['aperture']),'Paired camera exceeds unchanged original budgets')
    return dict(position_m=position,rotation_rad=rotation,byte_identical=(left/'camera.csv').read_bytes()==(right/'camera.csv').read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts','download-manifest','preserved-debug','preserved-release','mesa-runtime','output'):
        p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    p.add_argument('--producer-commit',required=True);a=p.parse_args()
    require(not a.output.exists(),'Fresh independent audit output required; replacement forbidden')
    result=dict(status='failed',protocol='remaining-stock-repaired-v1',phase6_complete=False,native_admission_qualified=False,
        producer_commit=a.producer_commit,original_application_and_sdk_source=BASE,verifier_sha256=sha(Path(__file__)),
        verifier_input_sha256=verifier_inputs(),
        profiles={},build_pairs={},scope='Independent explicitly repaired Windows candidate evidence only. '
            'No observations lock, native class admission, native parity or Phase 6 acceptance is created.')
    try:
        require(re.fullmatch('[0-9a-f]{40}',a.producer_commit),'Full immutable producer commit required')
        config=capture.settings();downloads=json.loads(a.download_manifest.read_text())
        profiles={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
        require(downloads['status']=='passed' and downloads['source_commit']==a.producer_commit and
                len(downloads['artifacts'])==4 and {item['profile'] for item in downloads['artifacts']}==profiles,
                'Exact complete four-profile repaired artifact transport required')
        result.update(download_manifest_sha256=sha(a.download_manifest),
            protocol_sha256_lf=sha_lf(HERE/'protocol.json'),settings_sha256_lf=sha_lf(capture.shared.CASE_FILE),
            unchanged_state_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum'])
        mesa,mesa_imports=independent_mesa(a.mesa_runtime,a.producer_commit)
        result['independent_mesa_manifest_sha256']=sha(a.mesa_runtime/'mesa-runtime.json')
        for profile in sorted(profiles):
            item=next(v for v in downloads['artifacts'] if v['profile']==profile);archive=ROOT/safe(item['path'])
            require(item['name']=='repaired-remaining-stock-v1-'+profile and
                    archive.stat().st_size==item['bytes'] and sha(archive)==item['sha256'],
                    'Exact repaired artifact ZIP transport differs: '+profile)
            members=archive_members(archive,a.artifacts/profile)
            result['profiles'][profile]=audit_profile(a.artifacts/profile,profile,config,a.producer_commit,
                a.preserved_debug if profile.startswith('Debug-') else a.preserved_release,mesa,mesa_imports)
            result['profiles'][profile].update(archive_sha256=item['sha256'],archive_members_verified=len(members))
            print(profile,'independently verified all 38 complete scenes twice',flush=True)
        for math_profile in ('automatic','sse2'):
            pairs={}
            require(result['profiles']['Debug-'+math_profile]['actual_math']==result['profiles']['Release-'+math_profile]['actual_math'],
                    'Paired configurations selected different actual CRT implementations')
            for case in config['cases']:
                paths=[a.artifacts/(kind+'-'+math_profile)/'remaining-stock-repaired'/(case['id']+'-1') for kind in ('Debug','Release')]
                errors=compare_state(*paths,config);detail=detail_calibration(*paths);camera=camera_comparison(*paths,config)
                score=capture.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(score>=config['image_ssim_minimum'],'Paired complete full-frame image exceeds unchanged budget')
                pairs[case['id']]=dict(maxima=errors,ssim=score,camera=camera,detail_numeric_calibration_only=detail)
            result['build_pairs'][math_profile]=pairs
        runs=[run for profile in result['profiles'].values() for case in profile['cases'].values() for run in case['runs']]
        require(len(runs)==304,'Complete 304-process repaired Windows matrix required')
        result.update(status='passed',processes=len(runs),presentations=960*len(runs),
            all_vessel_rows=sum(r['all_vessel_rows'] for r in runs),docking_rows=sum(r['docking_rows'] for r in runs),
            attachment_rows=sum(r['attachment_rows'] for r in runs),thruster_rows=sum(r['thruster_rows'] for r in runs),
            propellant_rows=sum(r['propellant_rows'] for r in runs),mesh_rows=sum(r['mesh_rows'] for r in runs),
            retired_resource_bindings=sum(r['retired_resource_bindings'] for r in runs),
            retired_resource_nonzero_levels=sum(r['retired_resource_nonzero_levels'] for r in runs))
        require(result['verifier_sha256']==sha(Path(__file__)) and
                result['verifier_input_sha256']==verifier_inputs() and result['download_manifest_sha256']==sha(a.download_manifest),
                'Independent verifier inputs or transport manifest changed during audit')
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','processes','presentations','all_vessel_rows','attachment_rows','thruster_rows')}))


if __name__=='__main__':main()
