"""Run full or explicitly diagnostic original-Windows persistence profiles locally."""
import datetime,hashlib,json,os,runpy,shutil,subprocess,sys,threading,time,traceback
from pathlib import Path
from win_local_process_v1 import context
from static_binary_link_staging_v1 import BinaryLinks
from runtime_descriptor_v2 import preflight, validate, capture_selection
REQUEST=Path(sys.argv[1]);cfg=json.loads(REQUEST.read_text());SHARE=Path(cfg['roots']['share']);SOURCE=Path(cfg['source']);OUTPUT=Path(cfg['output']);name=cfg['name'];seq=0;lock=threading.RLock();done=threading.Event();links=None
report=dict(status='running',name=name,source=cfg['source_commit'],configuration=cfg['configuration'],math_profile=cfg['math_profile'],context=context(),cloud_builds_used=False,native_admission_qualified=False,phase6_complete=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(stage):
 global seq
 with lock:
  seq+=1;report.update(stage=stage,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());text=json.dumps(report,indent=2)+'\n';(SHARE/f'{name}-status-{seq:04d}.json').write_text(text)
  temporary=SHARE/'worker-result.tmp';temporary.write_text(text);temporary.replace(SHARE/'worker-result.json')
def monitor():
 previous=None
 while not done.wait(10):
  current={}
  for phase,folder in [('stock','remaining-stock-repaired'),('reload','remaining-stock-persistence')]:
   p=OUTPUT/folder/'capture.json'
   if p.exists():
    try:
     d=load(p);current[phase]=dict(status=d['status'],cases=len(d['cases']),failures=d['failures'])
    except (OSError,ValueError):continue
  if current!=previous:
   with lock:report['capture_progress']=current;save('observing-complete-original-scope')
   previous=current

def run_source(relative,args,label):
 log=OUTPUT/(label+'.log')
 with log.open('wb') as f:
  child=subprocess.Popen([sys.executable,'-B',str(SOURCE/relative),*map(str,args)],cwd=SOURCE,stdout=f,stderr=subprocess.STDOUT);code=child.wait()
 assert code==0,label+': '+log.read_text(errors='replace')[-4000:]
 (SHARE/(name+'-'+label+'.log')).write_bytes(log.read_bytes())

def original_main(relative,args):
 prior=list(sys.argv);prior_path=list(sys.path);sys.argv=[str(SOURCE/relative),*map(str,args)];sys.path.insert(0,str((SOURCE/relative).parent))
 try:runpy.run_path(str(SOURCE/relative),run_name='__main__')
 finally:sys.argv=prior;sys.path[:]=prior_path

try:
 assert report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop'])
 selection=capture_selection(cfg);ids=selection['cases'];diagnostic=selection['diagnostic_only'];selection_args=selection['arguments']
 assert 'remaining_stock_003' in ids,'The unchanged real-input mutation controls require scene003 in the selected scope'
 report.update(diagnostic_only=diagnostic,cases_requested=ids,scene_workers=selection['scene_workers'])
 assert cfg['cohort']=='original-windows','Current-Windows needs its matching runtime adapter; original-SDK reader cannot certify it'
 report['root_preflight']=preflight(cfg);report['roles']=cfg['roles'];report['transport_protocol']=cfg['transport_protocol']
 assert sha(Path(cfg['worker_script']).parent/'static_binary_link_staging_v1.py')==cfg['staging_script_sha256']
 assert not OUTPUT.exists(),'Fresh output required'
 os.environ.update(PATH=str(Path(cfg['git']).parent)+';'+str(Path(sys.executable).parent)+';'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1',LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
 if cfg['math_profile']=='sse2':os.environ['ORBITER_TEST_OBSERVER_SSE2']='1'
 else:os.environ.pop('ORBITER_TEST_OBSERVER_SSE2',None)
 assert subprocess.check_output([cfg['git'],'-C',SOURCE,'rev-parse','HEAD'],text=True).strip()==cfg['source_commit']
 build=Path(cfg['build']);built=load(build/'build.json');runtime=build/'runtime';assert built['status']=='built-awaiting-runtime-and-independent-audit' and built['producer_commit']==cfg['source_commit']
 assert all(sha(runtime/n)==v for n,v in built['runtime_files_sha256'].items())
 provider=Path(cfg['mesa']);mesa=load(provider/'mesa-runtime.json');immutable={str(runtime/n):v for n,v in built['runtime_files_sha256'].items()};immutable.update({str(provider/n):v['sha256'] for n,v in mesa['files'].items()})
 OUTPUT.mkdir();links=BinaryLinks(immutable,OUTPUT);report['staging_controls']=links.controls(provider);links.install();report.update(request_sha256=sha(REQUEST),build_manifest_sha256=sha(build/'build.json'),original_source_files_unchanged=True,reference_variant=cfg['reference_variant'],static_staging_policy='Exact pinned DLL/EXE bytes are linked on NTFS; original copy behavior remains for all other inputs and any unavailable link. Original source, runtime assertions, every declared scene, both repeats and all clock/numerical/camera/image budgets unchanged.');save('running-original-input-controls')
 run_source('Tests/Production/RemainingStock/Execution.Test.py',[],'execution-controls');run_source('Tests/Production/RemainingStock/Resources.Test.py',[],'resource-controls');run_source('Tests/Production/RemainingStockRepaired/capture.py',['--verify-inputs','--protocol','remaining-stock-matched-clock-v2'],'complete-input-selection-controls')
 watcher=threading.Thread(target=monitor,daemon=True);watcher.start();stock=OUTPUT/'remaining-stock-repaired';reload=OUTPUT/'remaining-stock-persistence';data=Path(cfg['data']);planets=Path(cfg['planets'])
 save('running-declared-original-writers-twice')
 original_main('Tests/Production/RemainingStockRepaired/capture.py',['--executable',runtime/'Orbiter.exe','--data',data,'--planets',planets,'--mesa',provider,'--configuration',cfg['configuration'],'--math-profile',cfg['math_profile'],'--output',stock,'--protocol','remaining-stock-matched-clock-v2','--workers',selection['scene_workers'],*selection_args])
 parent=load(stock/'capture.json');assert parent['status']==('captured-diagnostic-only' if diagnostic else 'captured-awaiting-independent-audit') and parent['diagnostic_only'] is diagnostic and set(parent['cases'])==set(ids) and not parent['failures']
 case=stock/'remaining_stock_003-1'
 for script,args,label in [
  ('RemainingStockRepaired/Gate.Test.py',['--capture',case,'--output',stock/'gate-control.json','--protocol','remaining-stock-matched-clock-v2'],'gate-controls'),
  ('RemainingStock/Clock.Test.py',['--capture',case,'--output',stock/'clock-control.json'],'clock-controls'),
  ('RemainingStockRepaired/MatchedClock.Test.py',['--capture',case,'--output',stock/'matched-clock-control.json'],'matched-clock-controls'),
  ('RemainingStockRepaired/ConfigurationInput.Test.py',['--capture',case,'--output',OUTPUT/'configuration-input-controls.json'],'configuration-controls'),
  ('RemainingStockPersistence/SavedInputs.Test.py',['--parent-capture',stock,'--output',OUTPUT/'saved-input-controls.json'],'saved-input-controls')]:run_source('Tests/Production/'+script,args,label)
 save('running-declared-exact-original-save-reloads-twice')
 original_main('Tests/Production/RemainingStockPersistence/capture_windows.py',['--parent-capture',stock,'--build',build,'--preserved',cfg['preserved'],'--data',data,'--planets',planets,'--mesa',provider,'--configuration',cfg['configuration'],'--math-profile',cfg['math_profile'],'--output',reload,'--workers',selection['scene_workers'],*selection_args])
 reloaded=load(reload/'capture.json');assert reloaded['status']==('captured-diagnostic-only' if diagnostic else 'captured-awaiting-independent-persistence-audit') and set(reloaded['cases'])==set(ids) and not reloaded['failures'] and reloaded['diagnostic_only'] is diagnostic
 # Every collected run has the unmodified execution reader's real PID/exit receipt.
 actual=[]
 for phase,root in [('stock',stock),('reload',reload)]:
  for identity,case_record in load(root/'capture.json')['cases'].items():
   assert len(case_record['runs'])==2
   for repeat in (1,2):
    folder=root/(identity+'-'+str(repeat));timing=load(folder/'process-timing.json');assert timing['actual_returncode']==0 and timing['timed_out'] is False and timing['timeout_seconds']==900;actual.append(dict(phase=phase,case=identity,repeat=repeat,folder=str(folder),timing=timing))
 assert len(actual)==selection['expected_processes']
 done.set();watcher.join(timeout=15);links.close();report['static_binary_link_count']=len(links.links);report['static_binary_copy_fallbacks']=links.fallback
 (OUTPUT/'local-static-binary-links.json').write_text(json.dumps(dict(inputs=links.inputs,links=links.links,fallbacks=links.fallback),default=str,indent=2)+'\n')
 # Export closed raw evidence to the host; immutable runtime/data caches stay local in C:.
 export=Path(cfg['export']);assert not export.exists();export.mkdir()
 for p in OUTPUT.iterdir():
  if p.is_file():shutil.copy2(p,export/p.name)
 for foldername in ('remaining-stock-repaired','remaining-stock-persistence'):
  root=OUTPUT/foldername;dest=export/foldername;dest.mkdir();capture=load(root/'capture.json')
  for p in root.iterdir():
   if p.is_file():shutil.copy2(p,dest/p.name)
  for identity,case_record in capture['cases'].items():
   for repeat,run in enumerate(case_record['runs'],1):
    source=root/(identity+'-'+str(repeat));target=dest/source.name;target.mkdir();paths=set(run['files_sha256']);paths.update(p.relative_to(source).as_posix() for sub in ('Scenarios','Flights') for p in (source/sub).rglob('*') if p.is_file());paths.update(n for n in ('scene.png','process-timing.json') if (source/n).is_file())
    for n in paths:
     q=target/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/n,q)
 report.update(status=('completed-local-Windows-selected-stock-and-exact-save-reload-diagnostic-only' if diagnostic else 'completed-local-Windows-all38-stock-and-exact-save-reload-candidate'),actual_processes=len(actual),successful_presents=selection['expected_presents'],actual_process_receipts=actual,export=str(export),export_files_sha256={str(p.relative_to(export)):sha(p) for p in export.rglob('*') if p.is_file()},independent_full_persistence_audit_pending=True,local_transport_admission_pending=True,script_sha256=sha(__file__));save('completed')
except BaseException as error:report.update(status='failed',error=str(error),traceback=traceback.format_exc());save('failed');raise
finally:
 done.set()
 if links and shutil.copy2 is not links.original:links.close()
print(report['status'],flush=True)
