"""Run matching complete-scene diagnostics on an immutable ordinary native package."""
import argparse,csv,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('owner','build','build-record','assets','data','planets','tools','gtk-plugin','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
p.add_argument('--library',type=lambda v:Path(v).resolve(),action='append',required=True)
a=p.parse_args()
# Bind the build reader before importing scene helpers: its inventory ROOT must
# name the exact owning checkout, not the independent diagnostic checkout.
sys.path.insert(0,str(a.owner/'Tests/Production/StockScenarios'))
from intentional_exit import build_identity
build=json.loads(a.build_record.read_text());source=build['source_base']
identity=build_identity(a.build/'orbiter-production',a.build/'NativeModules',a.build_record,source)
from common import HERE,ROOT,require,sha,rows,settings,scenario,configuration,summarize
sys.path.insert(0,str(ROOT/'Tests/Production/WaylandInput'))
from compositor import Compositor
require(identity['sanitizer_linked'] and not a.output.exists(),'Sanitized matching package and fresh diagnostic output required');a.output.mkdir(parents=True)
guards={str(a.owner/n):sha(a.owner/n) for group in ('source_sha256_lf','dependency_sha256_lf','generated_source_files_sha256','runtime_files_sha256','candidate_runtime_files_sha256') for n in build[group]}
for folder in (a.assets,HERE):
    for path in folder.rglob('*'):
        if path.is_file():guards[str(path)]=sha(path)
for directory in a.library:
    for path in directory.glob('*.so*'):
        if path.is_file():guards[str(path)]=sha(path)
for path in (a.gtk_plugin,a.build_record,ROOT/'Tests/Production/WaylandInput/compositor.py',a.tools/'test-tools.json'):guards[str(path)]=sha(path)
report=dict(status='running',runtime_source=source,runtime_identity=identity,cases={},guarded_files_sha256=guards,native_admission_qualified=False,phase6_complete=False)
def save():(a.output/'diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
def write_csv(path,fields,records):
    with path.open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)
save()
try:
    with Compositor(a.tools,a.output/'compositor',1,'pixman') as display:
        for case in settings()['cases']:
            results=[]
            for repeat in (1,2):
                folder=a.output/(case['id']+'-'+str(repeat));folder.mkdir();body,expected=scenario(case)
                (folder/'scene.scn').write_bytes(body);(folder/'Orbiter.cfg').write_text(configuration((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text())+'\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n')
                (folder/'instrument-evidence.enabled').write_text('Complete-scene diagnostic observation only\n')
                argv=[str(a.build/'orbiter-production'),'--assets',str(a.assets),'--data',str(a.data),'--planets',str(a.planets),'--modules',str(a.build/'NativeModules'),'--scenario',str(folder/'scene.scn'),'--config',str(folder/'Orbiter.cfg'),'--evidence',str(folder),'--frames','60','--fixed-step','0.25','--fixed-system-step','0.25','--frame-delay-ms','120','--run']
                env=dict(display.environment,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),LD_LIBRARY_PATH=':'.join(map(str,[a.build,*a.library])))
                env.pop('LD_PRELOAD',None)
                with (folder/'console.log').open('w') as log:child=subprocess.run(argv,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                (folder/'process-result.json').write_text(json.dumps(dict(returncode=child.returncode,argv=argv),indent=2)+'\n');require(child.returncode==0,'Actual complete-scene native diagnostic failed')
                text=(folder/'console.log').read_text(errors='replace');require(not any(v in text for v in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','Production teardown:')),'Native runtime/sanitizer error')
                cockpit=rows(folder/'cockpit-state.csv');flight=rows(folder/'flight-state.csv');physical=rows(folder/'production-state.csv')
                require({r['object']:r['class'] for r in flight}==expected,'Actual complete native graph differs')
                write_csv(folder/'named-hud-state.csv',['tick','seconds','mjd','object','cockpit','hud','left_mfd','right_mfd','vessels'],[dict({k:r[k] for k in ('tick','seconds','mjd','object','cockpit','hud','left_mfd','right_mfd')},vessels='8') for r in cockpit])
                actual_classes={(r['tick'],r['object']):r['class'] for r in flight}
                fields=['tick','object','class','x','y','z','vx','vy','vz','mass','fuel'];records=[]
                for r in physical:
                    if r['object'] not in expected:continue
                    key=(r['step'],r['object']);require(key in actual_classes,'Actual initial/finalized class sample missing')
                    records.append(dict(tick=r['step'],object=r['object'],**{'class':actual_classes[key]},**{k:r[k] for k in fields if k not in ('tick','object','class')}))
                write_csv(folder/'named-vessel-state.csv',fields,records)
                results.append(summarize(folder,case))
            for key in ('raw_state_sha256','raw_vessel_state_sha256','hud_changes','second_DG_visual_registration_frames','nonfinite_text_labels','nonfinite_text_values'):require(results[0][key]==results[1][key],'Native diagnostic repeat differs: '+key)
            report['cases'][case['id']]=dict(runs=results);save()
    require(all(sha(n)==v for n,v in guards.items()),'An owning runtime, provider or diagnostic input changed')
    report.update(status='completed-matching-native-full-scene-diagnostics',owning_bytes_unchanged=True)
except BaseException as error:report.update(status='failed',error=str(error));raise
finally:save()
print(report['status'],identity['profile'],flush=True)
