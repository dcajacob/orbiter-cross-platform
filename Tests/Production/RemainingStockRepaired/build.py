#!/usr/bin/env python3
"""Build an explicit fresh Windows module/client variant without changing the preserved package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parent/'Client')]
from prepare_sources import BASE,git
from pe_symbols import PE


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def require(value,message):
    if not value:raise ValueError(message)


def runtime_changes(before,after):
    changes={name:dict(original_sha256=before.get(name),variant_sha256=value)
             for name,value in after.items() if before.get(name)!=value}
    replaced={'Modules/Atlantis_Tank.dll','Modules/Dragonfly.dll','Modules/Plugin/OGLClient.dll',
              'Modules/Plugin/ProductionCockpitDriver.dll'}
    sidecars={str(Path(name).with_suffix(suffix)).replace('\\','/')
              for name in replaced for suffix in ('.pdb','.ilk')}
    require(replaced<=set(changes) and set(before)<=set(after),'Missing replacement or original file removed')
    unexpected=sorted(name for name in changes if name not in replaced|sidecars and not name.startswith('Modules/OGLClient/'))
    require(not unexpected,'Undeclared original runtime change: '+', '.join(unexpected))
    return changes


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('preserved','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    a=p.parse_args()
    require(sys.platform=='win32','The repaired preserved-runtime build requires native Windows')
    require(not a.output.exists(),'Fresh variant output required; replacement forbidden')
    metadata=json.loads((a.preserved/'test-runtime.json').read_text())
    client=json.loads((a.preserved/'control-reference-runtime.json').read_text())
    require(metadata['source_commit']==client['application_source']==BASE,'Wrong original application/SDK source')
    protected={**metadata['files'],**client['client_files_sha256']}
    require(all(sha(a.preserved/name)==value for name,value in protected.items()),'Original package bytes differ')
    before=files(a.preserved)
    require(set(before)==set(protected)|{'test-runtime.json','control-reference-runtime.json'},
            'Unmanifested input in preserved package')
    producer=git('rev-parse','HEAD').decode().strip()
    paths=set(git('ls-tree','-r','--name-only',producer,'--','OVP/OGLClient',
                  'Tests/Production/RemainingStockRepaired','Tests/Production/RemainingStock').decode().splitlines())
    ledger=json.loads((HERE.parent/'phase3-extraction.lock.json').read_text())
    paths.update(ledger['files'])
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if ROOT in path.parents and path.suffix=='.py':paths.add(path.relative_to(ROOT).as_posix())
    paths.update(('LICENSE','Extern/imgui/imconfig.h','Tests/Production/phase3-extraction.lock.json',
                  'Tests/Production/Client/pe_symbols.py','Tests/Production/StockVessels/Observation.h',
                  'Tests/Production/ApplicationObservation.h','Tests/Production/production-source.lock.json',
                  '.github/workflows/repaired-remaining-stock.yml'))
    require({str(path.relative_to(ROOT).as_posix()) for path in HERE.iterdir() if path.is_file()}<=paths,
            'Builder has uncommitted inputs')
    sources={name:sha_lf(ROOT/name) for name in sorted(paths)}
    for name,value in sources.items():
        require(hashlib.sha256(git('show',producer+':'+name).replace(b'\r\n',b'\n')).hexdigest()==value,
                'Builder input differs from producer: '+name)
    a.output.mkdir(parents=True)
    runtime=a.output/'runtime';shutil.copytree(a.preserved,runtime)
    report=dict(schema=1,status='building',protocol='remaining-stock-repaired-v1',
        producer_commit=producer,original_application_and_sdk_source=BASE,configuration=a.configuration,
        preserved_package_sha256=before,source_sha256_lf=sources,commands=[],
        native_admission_qualified=False,phase6_complete=False)
    manifest=a.output/'build.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    def run(argv,label):
        report['commands'].append(argv);save()
        path=a.output/(label+'.log')
        with path.open('w') as log:
            process=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
        if process.returncode:
            print('\n'.join(path.read_text(errors='replace').splitlines()[-80:]),flush=True)
            process.check_returncode()
    save()
    try:
        source_variant=a.output/'module-sources'
        run([sys.executable,'-B',str(HERE/'prepare_sources.py'),'--output',str(source_variant)],'prepare')
        staged=json.loads((source_variant/'source-variant.json').read_text())
        require(staged['producer_commit']==producer,'Module source producer differs')
        original=git('show',producer+':Tests/Production/RemainingStock/Driver.cpp').replace(b'\r\n',b'\n')
        old=b'require(frames==60,"Incomplete original stock observation")'
        require(original.count(old)==1,'Original observer frame contract differs')
        observer=a.output/'observer/Driver.cpp';observer.parent.mkdir()
        observer.write_bytes(original.replace(old,b'require(frames==960,"Incomplete repaired stock observation")'))
        report['observer_source_variant']=dict(original_sha256=hashlib.sha256(original).hexdigest(),
            compiled_sha256=sha(observer),only_change='Validate 960 finalized ticks instead of 60; all observation calls and delays unchanged')
        build=a.output/'cmake'
        run(['cmake','-S',str(HERE),'-B',str(build),'-G','Ninja',
             '-DCMAKE_BUILD_TYPE='+a.configuration,'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
             '-DORBITER_TEST_RUNTIME='+str(runtime),'-DORBITER_REPAIRED_SOURCES='+str(source_variant/'source'),
             '-DORBITER_REPAIRED_OBSERVER='+str(observer)],'configure')
        run(['cmake','--build',str(build),'--parallel','2'],'compile')
        srb=build/'import-only/Atlantis_SRB.dll'
        require(PE(srb).exports()==PE(a.preserved/'Modules/Atlantis_SRB.dll').exports(),
                'Rebuilt import-only SRB exports differ from actual preserved SRB')
        require(sha(runtime/'Modules/Atlantis_SRB.dll')==before['Modules/Atlantis_SRB.dll'],
                'Import-only SRB replaced the actual original SRB')
        for name in ('Modules/Atlantis_Tank.dll','Modules/Dragonfly.dll'):
            require(PE(runtime/name).exports()==PE(a.preserved/name).exports(),
                    'Repaired module public export spellings differ: '+name)
        after=files(runtime)
        report['observed_runtime_files_sha256']=after;save()
        changed=runtime_changes(before,after)
        require(before==files(a.preserved),'Original package changed during variant build')
        require(sources=={name:sha_lf(ROOT/name) for name in sources},'Producer sources changed during build')
        require(staged['staged_files_sha256']==files(source_variant/'source'),'Staged module sources changed during build')
        report.update(status='built-awaiting-runtime-and-independent-audit',preserved_package_unchanged=True,
            runtime_files_sha256=after,declared_runtime_changes=changed,
            module_source_manifest_sha256=sha(source_variant/'source-variant.json'),
            compile_commands_sha256=sha(build/'compile_commands.json'),cmake_cache_sha256=sha(build/'CMakeCache.txt'),
            import_only_srb_sha256=sha(srb),import_only_srb_exports_match_preserved=True,
            repaired_module_public_export_spellings_unchanged=True,
            scope='Explicit repaired tank, Dragonfly and current real graphics client/observer in a fresh copy. '
                  'Original application, SDK, all other modules and all existing scene/data bytes retained. '
                  'This build creates no accepted reference or native admission.')
        (runtime/'runtime-variant.json').write_text(json.dumps(report,indent=2)+'\n')
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print('Built explicitly identified Windows module/client variant; original application/SDK retained unchanged')


if __name__=='__main__':main()
