"""Run actual source-bound normal-host paused startup checks; no full mission acceptance."""
import csv,hashlib,json,math,os,pathlib,subprocess,sys,time
import argparse
p=argparse.ArgumentParser(description=__doc__)
for name in ('package','assets','data','planets','compositor-tools','fontconfig','gdk','gtk-plugin','output'):
 p.add_argument('--'+name,type=lambda value:pathlib.Path(value).resolve(),required=True)
p.add_argument('--saved-ascent',type=lambda value:pathlib.Path(value).resolve())
p.add_argument('--runtime-owner',type=lambda value:pathlib.Path(value).resolve())
p.add_argument('--collector-source',help='Immutable commit owning this test when kept separately from the runtime')
args=p.parse_args();ROOT=args.runtime_owner or pathlib.Path(__file__).resolve().parents[3]
collector_source=args.collector_source or subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
assert len(collector_source)==40 and all(c in '0123456789abcdef' for c in collector_source)
assert pathlib.Path(__file__).read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',collector_source+':Tests/Production/NativePausedAttachments/Startup.Test.py'])
OUT=args.output;OUT.mkdir(parents=True,exist_ok=False)
sys.path[:0]=[str(ROOT/'Tests/Production/WaylandInput'),str(ROOT/'Tests/Production/Closeout'),str(ROOT/'Tests/Production/RemainingStockPersistence'),str(ROOT/'Tests/Production/StockScenarios')]
from compositor import Compositor
from processes import OwnedProcess
from saved_state import parse_saved,content_differences
from inventory import ships
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
from intentional_exit import build_identity
assets=args.assets;initial=load(args.package/'build.json')
assert initial['status']=='built' and initial['native_bootstrap_version']=='paused-attachments-v2'
identity=build_identity(args.package/'engine/orbiter-production',args.package/'engine/NativeModules',args.package/'build.json',initial['source_base'],ROOT)
guards={str(ROOT/n):sha(ROOT/n) for group in ('source_sha256_lf','dependency_sha256_lf','generated_source_files_sha256','runtime_files_sha256','candidate_runtime_files_sha256') for n in initial[group]}
resources=load(assets/'remaining-vessels-resources.json')['staged_files_sha256']
assert all(sha(assets/n)==h for n,h in resources.items())
guards.update({str(assets/n):sha(assets/n) for n in resources})
for folder in (args.fontconfig,args.gdk):
 for file in folder.glob('*.so*'):
  if file.is_file():guards[str(file)]=sha(file)
for file in (pathlib.Path(__file__),args.package/'build.json',args.gtk_plugin,assets/'remaining-vessels-resources.json'):
 guards[str(file)]=sha(file)
base_guards=dict(guards)
cases=[('Carina-original','Space Shuttle Atlantis/Atlantis satellite.scn','Carina','STS-101',0.0),('Leonardo-original','Space Shuttle Atlantis/Atlantis ISS Resupply.scn','Leonardo','STS-101',.4),('free-vessel-control','Delta-glider/DG Mk4 in orbit.scn',None,None,0.0)]
if args.saved_ascent:cases.append(('Carina-complete-ascent-save',args.saved_ascent,'Carina','STS-101',0.0))
results=[]
for tag,entry,child,parent,offset in cases:
 scenario=entry if isinstance(entry,pathlib.Path) else assets/'Scenarios'/entry
 if isinstance(entry,str):assert scenario.read_bytes()==(ROOT/'Scenarios'/entry).read_bytes()

 expected=ships(scenario.read_text())
 for variant in ('candidate',):
  engine=args.package/'engine';target=OUT/(tag+'-'+variant);target.mkdir(exist_ok=False)
  cfg=(ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()
  for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):assert cfg.count(line)==1;cfg=cfg.replace(line,'')
  (target/'Orbiter.cfg').write_text(cfg+'\nFPS = 0\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n')
  (target/'control-evidence.enabled').touch();(target/'instrument-evidence.enabled').touch()
  (target/'replay.csv').write_text('tick,phase,action,value\n63,after,save,0\n')
  libs=[args.fontconfig,args.gdk];plugin=args.gtk_plugin
  argv=[str(engine/'orbiter-production'),'--assets',str(assets),'--data',str(args.data),'--planets',str(args.planets),'--modules',str(engine/'NativeModules'),'--config',str(target/'Orbiter.cfg'),'--scenario',str(scenario),'--evidence',str(target),'--save',str(target/'actual-paused-save.scn'),'--replay',str(target/'replay.csv'),'--ticks','64','--render-every','1','--fixed-step',repr(1/60),'--capture-time','0']
  guards={**base_guards,str(scenario):sha(scenario),str(target/'Orbiter.cfg'):sha(target/'Orbiter.cfg'),str(target/'replay.csv'):sha(target/'replay.csv'),str(engine/'orbiter-production'):sha(engine/'orbiter-production'),str(__file__):sha(__file__)}
  with Compositor(args.compositor_tools,target/'compositor',1,'gl',repeat_rate=0) as display:
   env=dict(display.environment,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LD_LIBRARY_PATH=':'.join(map(str,[engine,*libs])),LIBDECOR_PLUGIN_DIR=str(plugin.parent))
   for name in ('LD_PRELOAD','LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER','LP_NUM_THREADS','__EGL_VENDOR_LIBRARY_FILENAMES'):env.pop(name,None)
   with (target/'console.log').open('x') as log:
    owned=OwnedProcess(['nice','-n','10','ionice','-c','3',*argv],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT)
    deadline=time.monotonic()+180
    try:
     while owned.process.poll() is None:
      owned.discover();assert time.monotonic()<deadline
      time.sleep(.1)
    finally:
     if owned.process.poll() is None:owned.cancel()
  console=(target/'console.log').read_text(errors='replace');assert owned.process.returncode==0
  assert not any(s in console for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','Suppressions used:','Production teardown:','LeakSanitizer has encountered'))
  assert load(target/'graphics-lifecycle.json')==dict(rendered_frames=64,successful_presents=64,context_deleted=True)
  renderer=load(target/'renderer-info.json');assert 'intel' in renderer['renderer'].lower() and not any(s in renderer['renderer'].lower() for s in ('llvmpipe','softpipe','software'))
  rows=list(csv.DictReader((target/'flight-state.csv').open()));assert len(rows)==len(expected) and {r['object']:r['class'] for r in rows}==expected
  assert all(int(r['tick'])==0 and float(r['seconds'])==0 and all(math.isfinite(float(v)) for k,v in r.items() if k not in ('object','class','dock','focus','attached')) for r in rows)
  state={r['object']:r for r in rows};parsed=parse_saved(target/'actual-paused-save.scn');assert {n:v['class_name'] for n,v in parsed['ships'].items()}==expected
  globals={r['object']:r for r in csv.DictReader((target/'production-state.csv').open())}
  assert set(expected)<=set(globals)
  errors={}
  if child:
   assert parent+';' in state[child]['attached'] and child+';' in state[parent]['attached']
   a,b=globals[child],globals[parent]
   predicted=[float(b[k])+offset*float(b[axis]) for k,axis in (('x','m12'),('y','m22'),('z','m32'))]
   errors['position_m']=math.dist([float(a[k]) for k in ('x','y','z')],predicted)
   errors['velocity_components_equal']=all(a[k]==b[k] for k in ('vx','vy','vz'))
   errors['rotation_components_equal']=all(a[f'm{i}{j}']==b[f'm{i}{j}'] for i in (1,2,3) for j in (1,2,3))
   errors['angular_velocity_components_equal']=all(a[k]==b[k] for k in ('wx','wy','wz'))
   # Expected child/parent transforms come from the unchanged original attachment definitions.
   # No serialization or trajectory tolerance is used: every component must agree exactly.
   valid=errors['position_m']==0 and all(errors[k] for k in ('velocity_components_equal','rotation_components_equal','angular_velocity_components_equal'))
   assert valid,(tag,variant,errors)
  else:valid=True
  if tag=='Carina-complete-ascent-save':
   assert not content_differences(parse_saved(scenario),parsed),content_differences(parse_saved(scenario),parsed)
  assert all(sha(p)==h for p,h in guards.items())
  result=dict(case=tag,variant=variant,actual_application_returncode=owned.process.returncode,process_receipt=owned.receipt(),scenario_sha256=sha(scenario),expected_vessels=expected,actual_finalized_physics_steps=0,actual_paused_presents=64,actual_MJD=parsed['mjd'],attachment_pose_exactly_initialized=valid,attachment_errors=errors,actual_renderer=renderer,guarded_files_sha256=guards,qualification_granted=False)
  (target/'verification.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result);print(tag,variant,'expected result verified',flush=True)
assert all(sha(p)==h for p,h in base_guards.items())
report=dict(status='passed-source-bound-paused-attachment-startup-controls',runtime_identity=identity,runtime_source=initial['source_base'],collector_source_commit=collector_source,native_bootstrap_version=initial['native_bootstrap_version'],actual_processes=len(results),actual_paused_presents=64*len(results),actual_physics_steps=0,results=results,full_original_Ascent_F5_qualification_granted=False,original_guards_captures_and_tolerances_unchanged=True)
(OUT/'paused-startup-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
