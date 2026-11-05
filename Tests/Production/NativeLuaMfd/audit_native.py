#!/usr/bin/env python3
"""Independently inspect a closed real Terminal MFD physical-input regression."""
import argparse,csv,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production/StockScenarios'))
from inventory import ships

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return list(csv.DictReader(path.read_text().splitlines()))
def require(value,message):
 if not value:raise ValueError(message)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 d=a.capture.resolve();record=d/'verification.json';x=json.loads(record.read_text())
 require(not a.output.exists(),'Fresh independent output required')
 require(x['status']=='passed-development-original-Terminal-MFD-real-Wayland-input-AAP-and-twenty-busy-page-lifetimes' and x['actual_exitcode']==0,'Complete clean real application run required')
 require(x['native_admission_qualified'] is False and x['phase6_complete'] is False,'Interaction regression must not claim full qualification')
 require(x['working_tree_changes'] is False and x['runtime_identity']['sanitizer_linked'],'Immutable instrumented package required')
 expected=ships((ROOT/'Scenarios/Delta-glider/Atmospheric autopilot.scn').read_text())
 require(len(expected)==8 and x['actual_original_objects']==expected and ships((d/'saved.scn').read_text())==expected,'Complete original scene and saved roster required')
 for name,value in x['guarded_files_sha256'].items():require(sha(name)==value,'Owning input changed: '+name)
 actual={p.relative_to(d).as_posix() for p in d.rglob('*') if p.is_file() and p.name!='verification.json'}
 require(actual==set(x['raw_files_sha256']),'Closed raw evidence closure differs')
 for name,value in x['raw_files_sha256'].items():require(sha(d/name)==value,'Closed raw evidence changed: '+name)
 require(json.loads((d/'compositor/lifecycle.json').read_text())['returncode']==0,'Compositor did not close cleanly')
 life=json.loads((d/'graphics-lifecycle.json').read_text());require(life==x['lifecycle'] and life['context_deleted'] and life['successful_presents']==life['rendered_frames']>50,'Actual presentations or context teardown incomplete')
 require([v['repeat'] for v in x['page_cycles']]==list(range(1,21)) and all(v['created_page'] and v['deleted_while_script_yielded'] and v['remaining_original_page']=='Term 1/1' for v in x['page_cycles']),'All twenty busy page lifetimes required')
 require([v['text'] for v in x['commands']]==['print(V:get_name())','aap.spd(300)']+['proc.wait_simdt(1000)']*20,'Actual command schedule differs')
 console=(d/'console.log').read_text(errors='replace')
 require(not any(v in console for v in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL','LeakSanitizer has encountered','LuaCall (','Lua error:','Production teardown:','Orbiter native production:')),'Application, Lua or sanitizer diagnostic')
 wire=[(int(k),int(v)) for k,v in re.findall(r'wl_keyboard[@#]\d+\.key\(\s*\d+,\s*\d+,\s*(\d+),\s*(\d+)\s*\)',console)]
 require(wire==[(v['code'],int(v['down'])) for v in x['key_deliveries']],'Actual Wayland key edges differ from sent input')
 text=[bytes.fromhex(v['text_hex']).decode('utf-8',errors='replace') for v in rows(d/'instrument-text.csv')]
 require(all(v in text for v in ('GL-01S','Term 1/1','Term 2/2','busy')),'Actual MFD did not render Lua output and busy pages')
 flight=rows(d/'flight-state.csv');require({v['object']:v['class'] for v in flight}==expected,'Actual simulation roster differs')
 max_speed=max(float(v['airspeed']) for v in flight if v['object']=='GL-01S');max_main=max(float(v['main']) for v in rows(d/'thrust-state.csv') if v['object']=='GL-01S')
 require(max_speed>10 and max_main>0,'Real AAP acceleration was not observed')
 require((d/'instrument-50.rgba').stat().st_size==1280*720*4,'Actual framebuffer capture incomplete')
 report=dict(status='passed-independent-real-Terminal-physical-input-AAP-twenty-busy-pages-and-full-save',capture=str(d),capture_sha256=sha(record),actual_pid=x['actual_pid'],actual_exitcode=0,successful_presents=life['successful_presents'],guarded_files=len(x['guarded_files_sha256']),raw_files=len(actual),key_edges=len(wire),page_lifetimes=20,full_original_objects=8,max_observed_airspeed=max_speed,max_observed_main=max_main,scope='One complete application session and twenty terminal-page lifetimes; full tutorial, original Windows interaction comparison, all-profile/full-session lifetime and Phase6 acceptance remain required.',native_admission_qualified=False,phase6_complete=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
