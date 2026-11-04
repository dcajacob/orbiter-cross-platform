"""Bind the actual failed Ctrl-S boundary to four complete corrected physical-input flows."""
import argparse,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__)
for name in ('failed','matrix','source-record','output'):parser.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def rows(path):
 with path.open() as stream:return list(csv.DictReader(stream))
protected={}
def check(path,value=None):
 value=value or sha(path);require(sha(path)==value,'Actual regression input changed: '+str(path));protected[str(path)]=value
manifest=args.matrix
matrix=json.loads(manifest.read_text());check(manifest);check(Path(__file__))
require(matrix['status']=='passed-current-four-profile-capture-synchronized-x11-input' and set(matrix['profiles'])=={'Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'},'Complete four-profile corrected input matrix required')
target=args.output;require(not target.exists(),'Fresh regression output required')
report=dict(status='failed',profiles={},native_admission_qualified=False,phase6_complete=False,scope='Exact observed old input-capture/save race and complete same-assertion corrected X11 target, parameter, cancel, keyboard capture and save flows in four current profiles.')
try:
 source=ROOT/'Tests/Production/CockpitUI/mouse_smoke.py'
 source_record=json.loads(args.source_record.read_text());check(args.source_record)
 before_helper=Path(source_record['original']);generated=Path(source_record['generated'])
 require(sha(before_helper)==source_record['original_sha256']=='4aedacb0fa546567a2fc279f121f944a610651d7485a3f2d567e46f2b2fe0600','Original c20135 helper bytes differ')
 require(sha(generated)==source_record['generated_sha256'],'Actual corrected executed helper differs')
 original=before_helper.read_text();actual=generated.read_text();check(source);check(before_helper);check(generated)
 added="                def released_capture():\n                    with (out/'ui-state.csv').open() as stream:states=list(csv.DictReader(stream))\n                    if not states:return None\n                    latest=states[-1]\n                    return latest if not latest['popup_hex'] and latest['capture_keyboard']=='0' and latest['capture_mouse']=='0' else None\n                boundary=wait(released_capture,'Original input dialog did not release capture before the save shortcut')\n                with (out/'gui-save-boundaries.jsonl').open('a') as stream:stream.write(json.dumps(dict(gui_frame=gui_frame(),observed_ui_state=boundary))+'\\n')\n"
 require(actual.count(added)==1,'Exact capture-release synchronization source missing')
 restored=actual.replace(added,'',1).replace('HERE=Path('+repr(str(before_helper.parent))+');ROOT=HERE.parents[2]','HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]',1)
 require(restored==original,'Corrected helper changed original input routes or assertions')
 require(source.read_text()==actual.replace('HERE=Path('+repr(str(before_helper.parent))+');ROOT=HERE.parents[2]','HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]',1),'Repository helper differs from the actual four-profile corrected helper')
 failed=args.failed
 old_wrapper=failed.with_name(failed.name+'-wrapper.json');old=json.loads(old_wrapper.read_text());check(old_wrapper)
 require(old['status']=='failed' and old['driver_returncode']==1 and old['runtime_source']=='d255d79176c9fffccf7f50b0af96bdab11f34fe3' and old['profile']=='Debug-automatic','Actual matching old failed process required')
 require(not (failed/'saved.scn').exists(),'Old process unexpectedly produced the requested save')
 old_ui=rows(failed/'ui-state.csv');opened=next(i for i,r in enumerate(old_ui) if r['popup_hex']);closed=next(r for r in old_ui[opened:] if not r['popup_hex'])
 old_keys=rows(failed/'input-events.csv');releases=[r for r in old_keys if r['key']=='31' and r['down']=='0']
 require(releases and not any(r['key']=='31' and r['down']=='1' for r in old_keys),'Actual old Ctrl-S press was not captured by the popup')
 require(int(releases[0]['tick'])<int(closed['tick']),'Old save shortcut did not precede actual popup release')
 require(json.loads((failed/'graphics-lifecycle.json').read_text())['context_deleted'],'Failed fixture did not close normally')
 report['actual_failed_boundary']=dict(save_release_tick=int(releases[0]['tick']),popup_first_observed_closed_tick=int(closed['tick']),save_file_absent=True,filtered_save_press=True)
 for name in ('ui-state.csv','input-events.csv','graphics-lifecycle.json','failure-window.png','console.log'):check(failed/name)
 for profile,entry in matrix['profiles'].items():
  require(entry['returncode']==0 and entry['status']=='passed-current-source-x11-gui-flow','Corrected profile did not finish cleanly')
  folder=Path(entry['path']);sidecar=Path(entry['wrapper_report']);check(sidecar,entry['wrapper_report_sha256']);wrapper=json.loads(sidecar.read_text())
  require(wrapper['status']=='passed-current-source-x11-gui-flow' and wrapper['driver_returncode']==0 and wrapper['owning_bytes_unchanged'] and wrapper['profile']==profile and wrapper['runtime_source']==old['runtime_source'],'Actual current corrected process differs')
  require(wrapper['sanitizer_environment']==old['sanitizer_environment']==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),'Actual sanitizer configuration changed')
  require(wrapper['asset_files_sha256']==old['asset_files_sha256'],'Actual input assets changed')
  if profile=='Debug-automatic':require(wrapper['runtime_identity']==old['runtime_identity'],'Actual failed/fixed executable package differs')
  require(wrapper['guarded_files_sha256'][str(generated)]==sha(generated),'Corrected process did not execute the capture-release helper')
  for name,value in wrapper['guarded_files_sha256'].items():check(Path(name),value)
  for name,value in wrapper['evidence_files_sha256'].items():check(folder/name,value)
  saved=(folder/'saved.scn').read_text()
  require('TARGET ISS' in saved.split('BEGIN_MFD Left',1)[1].split('END_MFD',1)[0] and 'LISTLEN 3' in saved.split('BEGIN_MFD Right',1)[1].split('END_MFD',1)[0],'Corrected target/parameter/cancel result differs')
  boundaries=[json.loads(line) for line in (folder/'gui-save-boundaries.jsonl').read_text().splitlines()];require(len(boundaries)==3,'All three actual save boundaries required')
  ui=rows(folder/'ui-state.csv');keys=rows(folder/'input-events.csv');saves=[r for r in keys if r['key']=='31' and r['down']=='1'];require(len(saves)==3,'All three original physical save shortcuts required')
  for boundary,key in zip(boundaries,saves):
   state=boundary['observed_ui_state'];require(state in ui and state['popup_hex']=='' and state['capture_keyboard']==state['capture_mouse']=='0' and boundary['gui_frame']>0 and int(state['tick'])<=int(key['tick']),'Save shortcut preceded actual capture release')
  flight=[r for r in keys if r['key']=='17'];require([r['down'] for r in flight]==['1','0'] and int(flight[0]['tick'])>=int(boundaries[-1]['observed_ui_state']['tick']),'Typing reached flight controls or flight did not resume/release')
  life=json.loads((folder/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']>0,'Corrected input context incomplete')
  console=(folder/'console.log').read_text(errors='replace');require(not any(s in console for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','LeakSanitizer has encountered')),'Corrected input sanitizer diagnostic')
  report['profiles'][profile]=dict(actual_save_boundaries=boundaries,successful_presents=life['successful_presents'],context_deleted=True)
 require(all(sha(Path(n))==v for n,v in protected.items()),'Actual old/new evidence changed during regression audit')
 report.update(status='passed-actual-capture-release-regression-and-four-profile-input',actual_processes=4,successful_presents=sum(r['successful_presents'] for r in report['profiles'].values()),protected_files_sha256=protected,original_assertions_and_routes_unchanged=True)
except BaseException as error:report.update(error=str(error));raise
finally:target.write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],report.get('actual_processes'),flush=True)
