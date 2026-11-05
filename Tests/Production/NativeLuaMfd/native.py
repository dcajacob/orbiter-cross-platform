"""Exercise the real stock Lua Terminal with Wayland keys in the complete tutorial scene."""
from pathlib import Path
import argparse,csv,hashlib,json,os,re,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'Tests/Production/WaylandInput'),str(ROOT/'Tests/Production/Flight'),str(ROOT/'Tests/Production/StockScenarios'),str(ROOT/'Tests/Production/RemainingStockRepaired')]
from compositor import Compositor
from keyboard_smoke import wait,require
from inventory import ships
from intentional_exit import build_identity
import data_inputs
parser=argparse.ArgumentParser(description=__doc__)
for name in ('build','build-record','assets','data','planets','compositor-tools','gtk-plugin','output'):
 parser.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
parser.add_argument('--library',type=lambda value:Path(value).resolve(),action='append',default=[])
a=parser.parse_args()
ENGINE=a.build;ASSETS=a.assets;OUT=a.output
assert not OUT.exists(),'Fresh output required'
record=json.loads(a.build_record.read_text())
identity=build_identity(ENGINE/'orbiter-production',ENGINE/'NativeModules',a.build_record,record['source_base'])
assert identity['sanitizer_linked'],'Actual ASan/UBSan package required'
for name,value in record['dependency_sha256_lf'].items():
 assert hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==value,name
collector_producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
for helper in (Path(__file__),Path(data_inputs.__file__),ROOT/'Tests/Production/WaylandInput/compositor.py',ROOT/'Tests/Production/Flight/keyboard_smoke.py'):
 body=subprocess.check_output(['git','-C',str(ROOT),'show',collector_producer+':'+helper.relative_to(ROOT).as_posix()])
 assert hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==hashlib.sha256(helper.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),str(helper)
SCENARIO=ASSETS/'Scenarios/Delta-glider/Atmospheric autopilot.scn'
OUT.mkdir(parents=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
 if not p.exists():return []
 try:return [r for r in csv.DictReader(p.read_text().splitlines()) if None not in r and all(v is not None for v in r.values())]
 except (OSError,UnicodeError):return []
config=(ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()
for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):assert config.count(line)==1;config=config.replace(line,'')
(OUT/'Orbiter.cfg').write_text(config+'\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\nACTIVE_MODULES\n  LuaMFD\nEND_MODULES\n')
for name in ('instrument-evidence','control-evidence','ui-evidence','menu-evidence'):(OUT/(name+'.enabled')).touch()
assert SCENARIO.read_bytes()==(ROOT/'Scenarios/Delta-glider/Atmospheric autopilot.scn').read_bytes()
expected=ships(SCENARIO.read_text());assert len(expected)==8
for source,target in (('Script/Demos/AtmAutopilot.lua','Script/Demos/AtmAutopilot.lua'),('Src/Vessel/DeltaGlider/Script/aap.lua','Script/DG/aap.lua')):
 assert (ASSETS/target).read_bytes().replace(b'\r\n',b'\n')==(ROOT/source).read_bytes().replace(b'\r\n',b'\n'),target
original_data=data_inputs.inspect(a.data,a.planets)
ledger=json.loads((ROOT/'Tests/Production/phase3-extraction.lock.json').read_text())
guards={str(ROOT/n):sha(ROOT/n) for n in ledger['files']}
guards.update({str(p):sha(p) for p in ASSETS.rglob('*') if p.is_file()})
for p in (Path(data_inputs.__file__),ROOT/'Tests/Production/StockScenarios/intentional_exit.py',ROOT/'Tests/Production/WaylandInput/compositor.py',ROOT/'Tests/Production/Flight/keyboard_smoke.py'):
 guards[str(p)]=sha(p)
for p in [a.build_record,a.gtk_plugin,*(p for directory in a.library for p in directory.glob('*.so*') if p.is_file()),ENGINE/'orbiter-production',ENGINE/'liborbiter_production_boundary.so',ENGINE/'liborbiter_production_vessels.so',ENGINE/'native-sdk/OrbiterNativeBuild.h',*(ENGINE/'NativeModules').rglob('*.so'),SCENARIO,ASSETS/'Script/Demos/AtmAutopilot.lua',OUT/'Orbiter.cfg',Path(__file__)]:guards[str(p)]=sha(p)
report=dict(status='running',scope='Development regression of original Terminal MFD inside the unchanged complete eight-object atmospheric-autopilot scene. Real private Wayland keyboard/input box, AAP throttle and terminal-page worker lifetimes. Not a completed guided tutorial, immutable qualified package, original Windows runtime comparison or Phase6 acceptance.',source_base_commit=record['source_base'],working_tree_changes=False,collector_producer_commit=collector_producer,runtime_identity=identity,actual_original_simulation_data=original_data,expected_original_objects=expected,guarded_files_sha256=guards,commands=[],page_cycles=[],key_deliveries=[],native_admission_qualified=False,phase6_complete=False)
def save():(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
def texts():
 values=[]
 for r in rows(OUT/'instrument-text.csv'):
  try:values.append((r,bytes.fromhex(r['text_hex']).decode('utf-8',errors='replace')))
  except (ValueError,KeyError,TypeError):pass
 return values

def title():
 values=[text for _,text in texts() if text.startswith('Term ')];return values[-1] if values else ''
def popup():
 values=rows(OUT/'ui-state.csv')
 if not values:return False
 tick=values[-1].get('tick')
 for r in values:
  if r.get('tick')!=tick:continue
  try:
   if bytes.fromhex(r.get('popup_hex','')).decode().startswith('##Popup_') and r.get('capture_keyboard')=='1':return True
  except (ValueError,TypeError):pass
 return False
assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,' (): _" for text in ('print(V:get_name())','aap.spd(300)','proc.wait_simdt(1000)') for c in text)
process=None;save()
try:
 with Compositor(a.compositor_tools,OUT/'compositor',1,'gl') as display:
  env=dict(display.environment,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LD_LIBRARY_PATH=':'.join(map(str,[ENGINE,*a.library])),LIBDECOR_PLUGIN_DIR=str(a.gtk_plugin.parent),WAYLAND_DEBUG='client')
  argv=list(map(str,[ENGINE/'orbiter-production','--assets',ASSETS,'--data',a.data,'--planets',a.planets,'--modules',ENGINE/'NativeModules','--scenario',SCENARIO,'--config',OUT/'Orbiter.cfg','--evidence',OUT,'--save',OUT/'saved.scn','--run']))
  with (OUT/'console.log').open('w') as log:
   process=subprocess.Popen(argv,cwd=OUT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);report.update(actual_pid=process.pid,argv=argv,environment={k:env[k] for k in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS','LD_LIBRARY_PATH','LIBDECOR_PLUGIN_DIR')});save()
   try:
    wait(lambda:process.poll() is not None or display.surface(process.pid),'Complete tutorial window did not map',60)
    if process.poll() is not None:
     report['actual_exitcode']=process.returncode;save();raise RuntimeError((OUT/'console.log').read_text()[-3000:])
    display.command('focus '+str(process.pid));assert display.command('state')['keyboard_pid']==process.pid
    wait(lambda:title()=='Term 1/1','Original Terminal MFD did not render',60)
    state=rows(OUT/'cockpit-state.csv')[-1];assert state['object']=='GL-01S' and int(state['left_mfd'])>10
    report['initial_terminal_state']=state;save()
    codes={'Shift':42,'Enter':28,'Escape':1,'Space':57,'Control':29,'F5':63,'i':23,'n':49,'d':32,'s':31}
    letters=dict(zip('qwertyuiop',[16,17,18,19,20,21,22,23,24,25]));letters.update(dict(zip('asdfghjkl',[30,31,32,33,34,35,36,37,38])));letters.update(dict(zip('zxcvbnm',[44,45,46,47,48,49,50])))
    digits=dict(zip('1234567890',range(2,12)))
    def wire():return [(int(k),int(v)) for k,v in re.findall(r'wl_keyboard[@#]\d+\.key\(\s*\d+,\s*\d+,\s*(\d+),\s*(\d+)\s*\)',(OUT/'console.log').read_text(errors='replace'))]
    def gui_frame():
     values=[]
     for line in (OUT/'ui-frames.csv').read_text().splitlines():
      try:values.append(int(line))
      except ValueError:pass
     return values[-1] if values else 0
    def key(code,down):
     display.command(f'key {process.pid} {code} {int(down)}');event=dict(code=code,down=bool(down),monotonic_ns=time.monotonic_ns());report['key_deliveries'].append(event)
     wait(lambda:wire()==[(e['code'],int(e['down'])) for e in report['key_deliveries']],'Actual client key delivery differs')
     if code==1 and down:return
     after_delivery=gui_frame();wait(lambda:gui_frame()>=after_delivery+2,'Actual GUI did not process the delivered key')
     event['client_delivery_then_gui_frame']=gui_frame()
    def tap_code(code):key(code,True);time.sleep(.045);key(code,False);time.sleep(.045)
    def shifted(name):
     key(42,True);time.sleep(.045);tap_code(codes[name]);key(42,False);time.sleep(.06)
    def type_text(text):
     for char in text:
      shift=False
      if char.isalpha():code=letters[char.lower()];shift=char.isupper()
      elif char in digits:code=digits[char]
      elif char in {'.':52,',':51,"'":40,' ':57}:code={'.':52,',':51,"'":40,' ':57}[char]
      elif char in {'(':10,')':11,':':39,'_':12}:code={'(':10,')':11,':':39,'_':12}[char];shift=True
      else:raise ValueError('Unsupported physical test character '+repr(char))
      if shift:key(42,True);time.sleep(.025)
      tap_code(code)
      if shift:key(42,False);time.sleep(.025)
    def command(text):
     shifted('i');wait(popup,'Original INP shortcut did not open its real input box');report['last_actual_popup_observation']=rows(OUT/'ui-state.csv')[-1];type_text(text);tap_code(28);wait(lambda:not popup(),'Original terminal input box did not close');report['commands'].append(dict(text=text,monotonic_ns=time.monotonic_ns()));save()
    command('print(V:get_name())');wait(lambda:any(t=='GL-01S' for _,t in texts()),'Terminal did not execute the real vessel-bound Lua print command')
    before=rows(OUT/'flight-state.csv')[-1];command('aap.spd(300)')
    wait(lambda:any(r.get('object')=='GL-01S' and float(r['main'])>0 for r in rows(OUT/'thrust-state.csv')),'Original terminal AAP did not drive the real DG-S engines',30)
    wait(lambda:any(r.get('object')=='GL-01S' and float(r['airspeed'])>10 for r in rows(OUT/'flight-state.csv')),'Actual glider did not start rolling under terminal AAP',30)
    report['AAP_throttle_and_roll_observed']=True;save()
    for repeat in range(1,21):
     shifted('n');wait(lambda:title()=='Term 2/2','NEW shortcut did not create a second real terminal page')
     before_frame=max(int(r['frame']) for r,t in texts());command('proc.wait_simdt(1000)');wait(lambda:any(t=='busy' and int(r['frame'])>before_frame for r,t in texts()),'This page did not render its own yielded busy script')
     old=rows(OUT/'cockpit-state.csv')[-1]['seconds'];wait(lambda:rows(OUT/'cockpit-state.csv')[-1]['seconds']!=old,'Busy terminal blocked simulation')
     shifted('d');wait(lambda:title()=='Term 1/1','Deleting the busy page did not rejoin its worker and return to page one')
     report['page_cycles'].append(dict(repeat=repeat,created_page=True,deleted_while_script_yielded=True,remaining_original_page=title()));save()
    tap_code(57);time.sleep(.2)
    assert len({r['seconds'] for r in rows(OUT/'cockpit-state.csv')[-3:]})==1
    key(29,True);tap_code(31);key(29,False);wait(lambda:(OUT/'saved.scn').exists(),'Actual Ctrl-S did not save the complete tutorial scene')
    assert ships((OUT/'saved.scn').read_text())==expected
    tap_code(57);wait(lambda:(OUT/'instrument-50.rgba').exists() and (OUT/'instrument-50.rgba').stat().st_size==1280*720*4,'No actual presented terminal frame50 capture',20)
    key(1,True);process.wait(timeout=60);report['actual_exitcode']=process.returncode
   finally:
    if process.poll() is None:process.terminate();process.wait(timeout=15)
    report['actual_exitcode']=process.returncode;save()
  assert process.returncode==0
  sys.path.insert(0,str(ROOT/'Tests/Production/Client'));from run_client import png
  png(OUT/'scene.png',(OUT/'instrument-50.rgba').read_bytes(),1280,720)
  report['representative_image_source']='instrument-50.rgba: actual presented frame50, no fixed-time numerical reference claim'
  console=(OUT/'console.log').read_text(errors='replace');assert not any(s in console for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','LuaCall (','Lua error:','Production teardown:'))
  life=json.loads((OUT/'graphics-lifecycle.json').read_text());assert life['context_deleted'] and life['successful_presents']>0
  actual={r['object']:r['class'] for r in rows(OUT/'flight-state.csv')};assert actual==expected
  wire=[(int(k),int(v)) for k,v in re.findall(r'wl_keyboard[@#]\d+\.key\(\s*\d+,\s*\d+,\s*(\d+),\s*(\d+)\s*\)',console)]
  assert wire==[(e['code'],int(e['down'])) for e in report['key_deliveries']]
  assert all(sha(p)==v for p,v in guards.items())
  report.update(status='passed-development-original-Terminal-MFD-real-Wayland-input-AAP-and-twenty-busy-page-lifetimes',lifecycle=life,actual_original_objects=actual,all_guarded_bytes_unchanged=True,actual_keyboard_protocol_matches_every_sent_key=True)
 assert data_inputs.inspect(a.data,a.planets)==original_data
 assert json.loads((OUT/'compositor/lifecycle.json').read_text())['returncode']==0
 report['raw_files_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='verification.json'}
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:save()
print(report['status'],flush=True)
