"""Check stock vessel-control and pause shortcuts through real Wayland input."""
from pathlib import Path
import argparse,csv,hashlib,json,os,subprocess,sys,time,traceback
R=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__)
for name in ('build','build-record','assets','data','planets','compositor-tools','gtk-plugin','output'):
 parser.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
parser.add_argument('--library',type=lambda value:Path(value).resolve(),action='append',default=[])
args=parser.parse_args();O=args.output;E=args.build;A=args.assets;assert not O.exists()
scenario='Scenarios/Delta-glider/DG Mk4 in orbit.scn'
sys.path[:0]=[str(R/'Tests/Production/WaylandInput'),str(R/'Tests/Production/StockScenarios'),str(R/'Tests/Production/RemainingStockRepaired')]
from compositor import Compositor
from inventory import ships
from intentional_exit import build_identity
import data_inputs
built=json.loads(args.build_record.read_text());assert built['status']=='built';identity=build_identity(E/'orbiter-production',E/'NativeModules',args.build_record,built['source_base'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert (A/scenario).read_bytes()==(R/scenario).read_bytes();expected=ships((A/scenario).read_text());assert len(expected)==8
O.mkdir();config=(R/'Tests/Production/NativeScene/Orbiter.cfg').read_text()
for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
 assert config.count(line)==1;config=config.replace(line,'')
(O/'Orbiter.cfg').write_text(config+'\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
for name in ['menu-evidence','ui-evidence','control-evidence','instrument-evidence']:(O/(name+'.enabled')).touch()
for n,value in built['source_sha256_lf'].items():assert hashlib.sha256((R/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==value,'Owning package source differs: '+n
guards={str(R/n):sha(R/n) for n in built['source_sha256_lf']};guards.update({str(R/n):v for n,v in built['runtime_files_sha256'].items()})
for q in [args.gtk_plugin,*(p for folder in args.library for p in folder.glob('*.so*') if p.is_file()),Path(__file__),args.build_record,O/'Orbiter.cfg',A/scenario,R/'Tests/Production/WaylandInput/compositor.py',R/'Tests/Production/StockScenarios/inventory.py',R/'Tests/Production/StockScenarios/intentional_exit.py']:guards[str(q)]=sha(q)
original_data=data_inputs.inspect(args.data,args.planets);guards[str(Path(data_inputs.__file__))]=sha(Path(data_inputs.__file__))
report=dict(actual_original_simulation_data=original_data,status='running',scope='Real left/right Ctrl+Space vessel controls and bare Space/original Ctrl+P pause bindings in the unchanged eight-object DG orbit scene. One configuration/math profile; not full named-mission or Phase6 qualification.',runtime_identity=identity,expected_objects=expected,guarded_files_sha256=guards,actions=[],observations=[],phase6_complete=False)
def save():(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
def tailrows(name):
 p=O/name
 if not p.exists():return []
 with p.open('rb') as f:
  header=f.readline().decode();end=f.seek(0,2);offset=max(len(header),end-65536);f.seek(offset)
  if offset>len(header):f.readline()
  lines=f.read().decode(errors='replace').splitlines()
 return [v for v in csv.DictReader([header.rstrip(),*lines]) if None not in v and all(x is not None for x in v.values())]
def latest():
 values=[v for v in tailrows('flight-state.csv') if v['object']=='GL-01'];return values[-1] if values else None
def gui():
 p=O/'ui-frames.csv';lines=p.read_text().splitlines() if p.exists() else [];return int(lines[-1]) if lines else 0
def controls():
 values=tailrows('menu-windows.csv');return [v for v in values if v['frame']==values[-1]['frame'] and 'DG Controls' in v['name']] if values else []
def wait(f,message,timeout=60):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  assert p.poll() is None,('Application exited',p.returncode)
  value=f()
  if value:return value
  time.sleep(.1)
 raise RuntimeError(message)
p=None;save()
try:
 with Compositor(args.compositor_tools,O/'compositor',1,'gl',repeat_rate=0) as display:
  env=dict(display.environment,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LD_LIBRARY_PATH=':'.join(map(str,[E,*args.library])),LIBDECOR_PLUGIN_DIR=str(args.gtk_plugin.parent),WAYLAND_DEBUG='client')
  argv=list(map(str,[E/'orbiter-production','--assets',A,'--data',args.data,'--planets',args.planets,'--modules',E/'NativeModules','--scenario',A/scenario,'--config',O/'Orbiter.cfg','--evidence',O,'--save',O/'saved.scn','--run']))
  with (O/'console.log').open('w') as log:
   p=subprocess.Popen(argv,cwd=O,env=env,stdout=log,stderr=subprocess.STDOUT);report.update(actual_pid=p.pid,argv=argv);save()
   try:
    wait(lambda:display.surface(p.pid),'Owned DG window did not map');display.command('focus '+str(p.pid));wait(lambda:gui()>60 and latest(),'DG scene did not initialize')
    def key(code,down):
     display.command(f'key {p.pid} {code} {int(down)}');report['actions'].append(dict(code=code,down=bool(down),monotonic_ns=time.monotonic_ns()));time.sleep(.15)
    def tap(code,ctrl=False):
     if ctrl:key(29,True)
     key(code,True);key(code,False)
     if ctrl:key(29,False)
    def click(x,y):
     display.command(f'move {p.pid} {x} {y}');time.sleep(.1)
     for down in [1,0]:
      display.command(f'button {p.pid} 272 {down}');time.sleep(.15)
    for modifier,label in [(29,'left Ctrl+Space'),(97,'right Ctrl+Space')]:
     before=latest();wait(lambda:float(latest()['seconds'])>float(before['seconds'])+.2,'Flight was not running before '+label)
     key(modifier,True);tap(57);key(modifier,False)
     window=wait(lambda:next(iter(controls()),None),'Original DG Controls did not open for '+label)
     opened=latest();wait(lambda:float(latest()['seconds'])>float(opened['seconds'])+.2,label+' incorrectly paused flight')
     report['observations'].append(dict(action=label,before=before,opened=opened,window=window,after=latest()));save()
     click(int(float(window['x'])+float(window['width']))-12,int(float(window['y']))+11)
     wait(lambda:not controls(),'Original DG Controls did not close')
     display.command(f'move {p.pid} 1270 680');time.sleep(.2)
    for code,modifier,label in [(57,False,'bare Space'),(25,True,'original Ctrl+P')]:
     tap(code,modifier);frame=gui();wait(lambda:gui()>frame+15,'GUI stopped during '+label)
     first=latest();time.sleep(1);second=latest();assert first['seconds']==second['seconds'],label+' did not pause flight'
     tap(code,modifier);wait(lambda:float(latest()['seconds'])>float(second['seconds'])+.2,label+' did not resume flight')
     report['observations'].append(dict(action=label,paused_first=first,paused_second=second,resumed=latest()));save()
    tap(31,True);wait(lambda:(O/'saved.scn').exists(),'Normal complete scene save absent')
    assert ships((O/'saved.scn').read_text())==expected
    key(29,True);key(16,True);report['actual_exitcode']=p.wait(timeout=60);assert p.returncode==0
   finally:
    if p.poll() is None:
     display.command(f'key {p.pid} 1 1')
     try:p.wait(timeout=15)
     except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=30)
    report['actual_exitcode']=p.returncode;save()
 life=json.loads((O/'graphics-lifecycle.json').read_text());assert life['context_deleted'] and life['successful_presents']>60
 events=list(csv.DictReader((O/'input-events.csv').open()))
 assert any(e['key']=='57' and e['down']=='1' and e['lctrl']=='1' for e in events)
 assert any(e['key']=='57' and e['down']=='1' and e['rctrl']=='1' for e in events)
 console=(O/'console.log').read_text();assert not any(v in console for v in ['ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','Production teardown:'])
 assert data_inputs.inspect(args.data,args.planets)==original_data
 assert all(sha(p)==v for p,v in guards.items()),'Guarded input changed'
 report.update(status='passed-real-vessel-controls-and-original-pause-shortcuts',lifecycle=life,all_guarded_inputs_unchanged=True,all_original_saved_objects=expected,sanitizer_suppressions=False);save();print(report['status'],p.pid,flush=True)
except BaseException as error:report.update(status='failed',error=str(error),traceback=traceback.format_exc());save();raise
