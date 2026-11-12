#!/usr/bin/env python3
"""Build a fresh source-bound remaining-stock native package with actual original modules."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
import extraction_source


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)


def generated_inputs(engine,producer,log):
    directories=list(engine.glob('native-dragonfly-*'))
    require(len(directories)==1,'Actual generated Dragonfly source tree missing or ambiguous')
    directory=directories[0]
    with log.open('w') as stream:
        subprocess.run([sys.executable,'-B',str(HERE.parent/'Dragonfly/prepare_native.py'),
                        '--output',str(directory),'--verify-output'],stdout=stream,stderr=subprocess.STDOUT,check=True)
    report=json.loads((directory/'native-source.json').read_text())
    require(report['producer_commit']==producer,'Actual generated source producer differs')
    paths=list(directory.rglob('*'))
    require(not any(p.is_symlink() for p in paths),'Symlink in actual generated source inputs')
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_file()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','renderer-dependencies','lua-archive','plot-archive'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--development-prefix',type=lambda v:Path(v).resolve())
    p.add_argument('--math-development-prefix',type=lambda v:Path(v).resolve(),
                   help='Explicit MPFR development prefix for the existing reference-math unit target')
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    p.add_argument('--sanitizers',action='store_true')
    p.add_argument('--include-unit-tests',action='store_true',help='Build and inventory existing registered tests; does not mark them passed')
    p.add_argument('--catch-source',type=lambda v:Path(v).resolve(),
                   help='Offline locked Catch checkout for the existing upstream C++/Lua units')
    p.add_argument('--physics-version',choices=('assembly-contact-v3',),default='assembly-contact-v3')
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();require(sys.platform=='linux','Native package requires Linux')
    require(not a.output.exists() and a.jobs>0,'Fresh package output and positive build concurrency required')
    require(not a.include_unit_tests or a.catch_source is not None,
            'Existing upstream units require their explicit offline Catch source')
    physics_proof=None
    if a.physics_version=='original':extraction_source.verify()
    else:
        from NativePausedAttachments import source as physics_source
        physics_proof=physics_source.verify()
    ledger=json.loads((HERE.parent/'phase3-extraction.lock.json').read_text())['files']
    inputs=set(ledger)|{'OVP/OGLClient/dependencies.lock.json','Tests/Production/dependencies.lock.json',
        'Tests/Production/Licenses/implot-LICENSE','Tests/Production/extraction_source.py',
        'Tests/Production/phase3-extraction.lock.json'}
    inputs.update(subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only','HEAD','--','OVP/OGLClient'],text=True).splitlines())
    inputs.update(path.relative_to(ROOT).as_posix() for path in HERE.iterdir() if path.is_file())
    inputs.update(path.relative_to(ROOT).as_posix() for path in (HERE.parent/'Dragonfly').glob('*.py'))
    if a.include_unit_tests:
        inputs.update(path.relative_to(ROOT).as_posix() for path in (HERE.parent/'CoreUnits').iterdir() if path.is_file())
        inputs.update(('Tests/Lua.Interpreter.cpp','Tests/Collision.CollisionCore.cpp',
                       'Script/oapi_init.lua','Script/strict.lua'))
    if physics_proof:inputs.update(physics_source.INPUTS)
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if ROOT in path.parents and path.suffix=='.py':inputs.add(path.relative_to(ROOT).as_posix())
    before={name:sha_lf(ROOT/name) for name in sorted(inputs)}
    source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,value in before.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+name]).replace(b'\r\n',b'\n')
        require(hashlib.sha256(body).hexdigest()==value,'Builder input differs from immutable producer: '+name)
    archives=[a.lua_archive,a.plot_archive,*sorted(a.renderer_dependencies.glob('*.zip')),
              a.renderer_dependencies/'glfw.tar.gz']
    require(all(path.is_file() for path in archives),'Pinned dependency archive absent')
    archive_hashes={str(path):sha(path) for path in archives}
    engine=a.output/'engine';renderer=a.output/'renderer'
    common=['-DCMAKE_BUILD_TYPE='+a.configuration,'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    if a.include_unit_tests:
        common.append('-DPython3_EXECUTABLE='+sys.executable)
    if a.sanitizers:
        common+=['-DCMAKE_C_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer',
                 '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer']
    commands=[dict(label='engine-configure',argv=['cmake','-S',str(ROOT/'Src/Orbiter/Production'),'-B',str(engine),'-G','Ninja',*common,
        '-DBUILD_TESTING='+('ON' if a.include_unit_tests else 'OFF'),'-DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON','-DORBITER_BUILD_NATIVE_VESSELS=ON',
        '-DORBITER_BUILD_NATIVE_COCKPIT=ON','-DORBITER_BUILD_ATLANTIS_DIAGNOSTIC=ON','-DORBITER_BUILD_REMAINING_STOCK_DIAGNOSTIC=ON',
        '-DORBITER_MATH_FORCE_SSE2='+('ON' if a.math_profile=='sse2' else 'OFF'),
        '-DORBITER_NATIVE_LUA_ARCHIVE='+str(a.lua_archive),'-DORBITER_NATIVE_UI_ARCHIVE='+str(a.renderer_dependencies/'imgui.zip'),
        '-DORBITER_NATIVE_PLOT_ARCHIVE='+str(a.plot_archive)]),
        dict(label='engine-build',argv=['cmake','--build',str(engine),'--parallel',str(a.jobs)]),
        dict(label='renderer-configure',argv=['cmake','-S',str(ROOT/'OVP/OGLClient/Native'),'-B',str(renderer),'-G','Ninja',*common,
        '-DORBITER_ENGINE_BUILD='+str(engine),'-DORBITER_RENDERER_DEPENDENCIES='+str(a.renderer_dependencies)]),
        dict(label='renderer-build',argv=['cmake','--build',str(renderer),'--parallel',str(a.jobs)])]
    if a.development_prefix:commands[2]['argv'].append('-DCMAKE_PREFIX_PATH='+str(a.development_prefix))
    math_inputs={}
    if a.math_development_prefix:
        commands[0]['argv'].append('-DCMAKE_PREFIX_PATH='+str(a.math_development_prefix))
        for path in (a.math_development_prefix/'include/mpfr.h',
                     a.math_development_prefix/'lib/x86_64-linux-gnu/libmpfr.so'):
            require(path.is_file(),'Explicit MPFR development input missing: '+str(path))
            math_inputs[str(path)]=sha(path)
    upstream=a.output/'upstream-units'
    if a.include_unit_tests:
        commands += [dict(label='upstream-units-configure',argv=['cmake','-S',str(HERE.parent/'CoreUnits'),
            '-B',str(upstream),'-G','Ninja',*common,'-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            '-DORBITER_ENGINE_SOURCE='+str(ROOT),'-DORBITER_ENGINE_BUILD='+str(engine),
            '-DORBITER_CATCH_SOURCE='+str(a.catch_source)]),
            dict(label='upstream-units-build',argv=['cmake','--build',str(upstream),'--parallel',str(a.jobs)])]
    a.output.mkdir(parents=True)
    report=dict(status='building',source_base=source,source_sha256_lf={name:before[name] for name in ledger},
        dependency_sha256_lf={name:value for name,value in before.items() if name not in ledger},source_guard_inputs=len(before),
        configuration=a.configuration,math_profile=a.math_profile,instrumentation='address,undefined' if a.sanitizers else 'none',
        commands=commands,builder_sha256=sha(Path(__file__)),archive_sha256=archive_hashes,
        math_development_inputs_sha256=math_inputs,
        native_admission_qualified=False,phase6_complete=False)
    if physics_proof:report.update(physics_version=a.physics_version,physics_source_proof=physics_proof)
    if physics_proof:report['native_bootstrap_version']=physics_proof['native_bootstrap_version']
    manifest=a.output/'build.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        generated=None
        for command in commands:
            log=a.output/(command['label']+'.log')
            with log.open('w') as stream:process=subprocess.run(command['argv'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            if process.returncode:
                print('\n'.join(log.read_text(errors='replace').splitlines()[-70:]),flush=True);process.check_returncode()
            print(command['label'],'passed',flush=True)
            if command['label']=='engine-configure':
                generated=generated_inputs(engine,source,a.output/'generated-source-before.log')
                report['generated_source_files_sha256']=generated;save()
            elif command['label'] in ('engine-build','renderer-build'):
                require(generated==generated_inputs(engine,source,a.output/(command['label']+'-generated-source-after.log')),
                        'Actual generated source inputs changed during compilation')
        require(before=={name:sha_lf(ROOT/name) for name in before},'Owning source changed during fresh build')
        require(archive_hashes=={name:sha(Path(name)) for name in archive_hashes},'Dependency archive changed during build')
        cache=dict(line.split('=',1) for line in (engine/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith(('#','//')))
        require(cache['CMAKE_BUILD_TYPE:STRING']==a.configuration and cache['ORBITER_MATH_FORCE_SSE2:BOOL']==('ON' if a.math_profile=='sse2' else 'OFF'),
                'Actual configuration/math profile differs')
        for language in ('C','CXX'):
            require(('-fsanitize=address,undefined' in cache['CMAKE_'+language+'_FLAGS:STRING'])==a.sanitizers,'Actual sanitizer flags differ')
        for name in ('HST','SolarSail','Quadcopter','Dragonfly'):
            module=engine/'NativeModules/Vessel'/(name+'.so');require(module.is_file(),'Original native module absent: '+name)
            symbols=subprocess.check_output(['nm','-D','--defined-only',str(module)],text=True)
            require(any(line.split()[-1]=='OrbiterNativeQuery' for line in symbols.splitlines()),'Actual checked SDK entry absent: '+name)
            if name=='Dragonfly':
                demangled=subprocess.check_output(['nm','-DC','--defined-only',str(module)],text=True)
                require(not any(value in demangled for value in ('typeinfo for Tank','vtable for Tank','Tank::')),
                        'Private Dragonfly tank symbols would collide with the actual engine scenery Tank')
            if name=='SolarSail':
                require(not any(len(line.split())>=3 and line.split()[-2]=='u' for line in symbols.splitlines()),
                        'GNU-unique symbols would prevent real solar-sail module unload')
            linked=subprocess.check_output(['readelf','-d',str(module)],text=True)
            require(('libasan.so' in linked)==a.sanitizers and ('libubsan.so' in linked)==a.sanitizers,'Actual module sanitizer linkage differs')
        candidates=[engine/'production_atlantis_diagnostic',engine/'production_remaining_stock_diagnostic']
        require(all(path.is_file() for path in candidates),'Real diagnostic host absent')
        runtime=[engine/'orbiter-production',engine/'CMakeCache.txt',engine/'compile_commands.json',*sorted(engine.rglob('*.so'))]
        if a.include_unit_tests:
            listing=a.output/'registered-unit-tests.json'
            command=['ctest','--test-dir',str(engine),'--show-only=json-v1']
            data=json.loads(subprocess.check_output(command,text=True))
            require(data['tests'] and len({test['name'] for test in data['tests']})==len(data['tests']) and
                    all(test.get('command') and Path(test['command'][0]).is_file() for test in data['tests']),
                    'Complete existing registered test binaries/commands required')
            listing.write_text(json.dumps(data,indent=2)+'\n')
            report['registered_unit_tests']=dict(path=str(listing),sha256=sha(listing),
                command=command,registered_processes=len(data['tests']),executed=False,
                scope='Actual CTest registration only; upstream Catch cases, portable tests and standalone fixtures remain separately required')
            runtime += [listing,*sorted({Path(test['command'][0]) for test in data['tests']
                                        if engine in Path(test['command'][0]).parents})]
            command=['ctest','--test-dir',str(upstream),'--show-only=json-v1']
            data=json.loads(subprocess.check_output(command,text=True))
            require({test['name'] for test in data['tests']}=={'Lua.Interpreter','Collision.CollisionCore'} and
                    all(Path(test['command'][0]).is_file() for test in data['tests']),
                    'Both unchanged upstream unit processes required')
            listing=a.output/'upstream-registered-unit-tests.json'
            listing.write_text(json.dumps(data,indent=2)+'\n')
            report['upstream_unit_tests']=dict(path=str(listing),sha256=sha(listing),
                command=command,registered_processes=2,executed=False,build=str(upstream),
                catch_source=str(a.catch_source),
                catch_commit=subprocess.check_output(['git','-C',str(a.catch_source),'rev-parse','HEAD'],text=True).strip(),
                scope='Existing upstream C++/Lua bodies; runtime case discovery, execution and assertions remain required')
            runtime += [listing,*[Path(test['command'][0]) for test in data['tests']],
                        *sorted((upstream/'assets').rglob('*.lua'))]
        if physics_proof:
            sdk_header=engine/'native-sdk/OrbiterNativeBuild.h'
            require(sdk_header.is_file(),'Exact generated v2 SDK input required')
            runtime.append(sdk_header)
        notice=engine/'NativeModules/Licenses/implot-LICENSE.txt'
        require(sha_lf(notice)==sha_lf(ROOT/'Tests/Production/Licenses/implot-LICENSE'),'ImPlot notice differs')
        require(all(sha(Path(name))==value for name,value in math_inputs.items()),
                'Explicit MPFR development inputs changed during the build')
        report.update(status='built',owning_sources_unchanged=True,implot_notice_sha256_lf=sha_lf(notice),
            solar_sail_gnu_unique_symbols=False,
            dragonfly_private_tank_symbols_exported=False,
            candidate_runtime_files_sha256={path.relative_to(ROOT).as_posix():sha(path) for path in candidates},
            runtime_files_sha256={path.relative_to(ROOT).as_posix():sha(path) for path in runtime},
            scope='Fresh original-source native modules and real diagnostic host; complete Windows/native state/camera/frame, '
                  'interaction, lifecycle, stock admission and full Phase 6 qualification remain required.')
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
