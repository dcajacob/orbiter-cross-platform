#!/usr/bin/env python3
"""Reuse exact hosted userspace/provider/asset setup for three diagnostic observer worlds."""
import os
from pathlib import Path
import sys
from contracts import ROOT,require,load,sha,atomic_json
import capture_hosted_native_writer_runtime as runtime
import rejection_input_bundle as bundle


def prepared_body():
    body=runtime.prepared_body()
    for old,new,count in [("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-numerical-observer-renewal-v1'",1),("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-numerical-observer'",1),("ROOT/'out/native-writer-container.json'","ROOT/'out/numerical-observer-container.json'",2)]:
        require(body.count(old)==count,'Original complete userspace/preflight setup anchor differs');body=body.replace(old,new)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r'''
        from numerical_observer_equivalence import source_identity
        report['source_identity']=source_identity();save()
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/Closeout/numerical_observer_equivalence.py','--profile',a.profile,
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--gtk-build-record',str(providers/'libdecor-candidate/build.json')]
        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('original-save-baseline-and-observer-off-on',argv,3000,environment)
        result=load(ROOT/'out/numerical-observer-renewal'/a.profile/'collection.json')
        require(result['status']=='captured-and-original-audited-three-world-observer-equivalence-only' and result['three_world_inspection']['actual_processes']==3 and source_identity()==report['source_identity'],'All three unchanged-source worlds and original audit must complete')
        report['three_world_inspection']=result['three_world_inspection'];save()
'''.lstrip('\n')
    body=body[:start]+replacement+body[end:]
    old="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    require(body.count(old)==1,'Exact original setup completion anchor differs')
    return body.replace(old,"        report.update(status='captured-and-original-audited-three-world-observer-equivalence-only',actual_processes=3,published_raw_independent_audit_pending=True,complete_numerical_reload_gate_qualified=False,hands_on_ready=False)",1)


def preserve(profile):
    folder=ROOT/'out/numerical-observer-renewal'/profile;output=ROOT/'out/hosted-numerical-observer'/profile
    require(folder.is_dir(),'Actual fresh observer component directory required')
    paths={p for directory in (folder,output) if directory.exists() for p in directory.rglob('*') if p.is_file() or p.is_symlink()}
    record=folder/'collection.json'
    if record.exists():paths.update(Path(n) for n in load(record)['guarded_files_sha256'])
    proof=load(folder/'proof.json');sdk=proof['original_SDK_header_derivation']
    for key in ('original_sources_sha256','original_binary_and_cache_sha256'):paths.update(Path(n) for n in sdk[key])
    paths.add(Path(sdk['header']))
    for directory in ('Tests/Production/Closeout','Tests/Production/ReloadMath','Tests/Production/RemainingStockPersistence','Tests/Production/RemainingVessels','Tests/Production/RemainingStock','Tests/Production/RemainingStockRepaired','Tests/Production/WaylandInput','Tests/Production/StockScenarios','Tests/Production/StockVessels','Tests/Production/NativeScene','Tests/Production/CockpitUI','Tests/Production/Dragonfly','Tests/Production/Math'):
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update({ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'Tests/Production/phase3-extraction.lock.json',ROOT/'Tests/Production/stock-data.lock.json',ROOT/'Tests/Production/standard-planets.lock.json',Path(__file__),Path(bundle.__file__)})
    output.mkdir(parents=True,exist_ok=True)
    retained=bundle.pack(ROOT,paths,output/'raw-original-inputs.tar.gz',output/'raw-index.json')
    if record.exists() and load(record)['status']=='captured-and-original-audited-three-world-observer-equivalence-only':require(not retained['missing_guarded_paths'],'Completed three-world capture cannot omit any guarded byte')


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted worker only')
    require('--profile' in sys.argv and sys.argv[sys.argv.index('--profile')+1]=='Debug-automatic','Only affected exact-original-save numerical scope')
    profile='Debug-automatic';failure=None
    try:exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
    except BaseException as error:failure=error;raise
    finally:
        try:preserve(profile)
        except BaseException as error:
            folder=ROOT/'out/hosted-numerical-observer'/profile;folder.mkdir(parents=True,exist_ok=True)
            atomic_json(folder/'packing-failure.json',dict(error=str(error),original_error=str(failure),qualified=False,phase6_complete=False))
            if failure is None:raise


if __name__=='__main__':main()
