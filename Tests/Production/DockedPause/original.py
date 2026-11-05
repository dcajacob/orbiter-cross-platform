"""Measure original paused docked save/read/write tokens without a tolerance waiver."""
import argparse,csv,json,math,sys
from pathlib import Path
from inputs import HERE,ROOT,require,sha,settings,scenario,configuration
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'Client'),str(HERE.parent/'Cockpit'),str(HERE.parent/'RemainingStockPersistence')]
from stage import run as stage
from run_client import mesa_files
from saved_state import parse_saved,content_differences

def rows(path):
    with Path(path).open() as f:return list(csv.DictReader(f))

def inspect(folder,case,phase,config,expected,parent=None,expected_binaries=None):
    frames=case['pause_tick']+config['paused_frames'] if phase=='writer' else config['paused_frames']
    require(not (folder/'pause-failure.txt').exists(),'Original paused SDK diagnostic failed: '+((folder/'pause-failure.txt').read_text() if (folder/'pause-failure.txt').exists() else ''))
    require((folder/'pause-complete.txt').read_text().strip()==str(frames),'Original paused process did not complete')
    clock=rows(folder/'pause-clock.csv');want=list(range(frames+1)) if phase=='writer' else list(range(1,frames+1))
    require([int(r['frame']) for r in clock]==want,'Incomplete original running/paused clock observations')
    elapsed=0.0
    for row in clock:
        frame=int(row['frame']);running=phase=='writer' and frame<=case['pause_tick']
        if frame and running:elapsed+=config['fixed_step']
        require(float(row['seconds'])==elapsed and row['running']==str(int(running)) and row['paused']==str(int(not running)),'Original exact pause boundary or physics clock differs')
        require(row['object']=='GL-02' and math.isfinite(float(row['mjd'])),'Original focus or clock differs')
    paused=[r for r in clock if r['paused']=='1'];require(len(paused)==8 and len({r['mjd'] for r in paused})==1 and len({r['seconds'] for r in paused})==1,'Original paused clock advanced')
    witness=rows(folder/'pause-saved-clock.csv');require(len(witness)==1 and witness[0]['seconds']==paused[0]['seconds'] and witness[0]['mjd']==paused[0]['mjd'],'Actual save was not at the observed paused clock')
    if parent is not None:require(float(paused[0]['mjd'])==float(parse_saved(parent)['mjd']),'Original reload did not retain its actual saved epoch')
    physical=rows(folder/'pause-vessels.csv');require(len(physical)==len(want)*6,'Incomplete actual six-object snapshots')
    for frame in want:
        batch=[r for r in physical if int(r['frame'])==frame]
        require(len(batch)==6 and {r['object']:r['class'] for r in batch}==expected,'An original object was dropped, duplicated or replaced')
        for row in batch:
            require(all(math.isfinite(float(v)) for k,v in row.items() if k not in ('object','class')),'Nonfinite original SDK physical state')
            require(int(row['api_version'])==(3 if row['class'] in ('DeltaGlider','ShuttleA') else 0),'A real source-built original vessel interface was replaced')
    renderer=json.loads((folder/'renderer-info.json').read_text());require('llvmpipe' in renderer['renderer'].lower(),'Original pinned software renderer missing: '+json.dumps(renderer))
    life=json.loads((folder/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']==frames,'Original render lifecycle incomplete')
    errors=folder/'graphics-errors.txt';require(not errors.exists() or not errors.read_text().strip(),'Original real renderer reported errors')
    # The frozen renderer emits its own DLL list only at its delayed graphics
    # capture. These paused runs stop before that time, so the diagnostic takes
    # a read-only Win32 module snapshot exactly when the real SDK save occurs.
    mapped=[Path(s).resolve() for s in (folder/'pause-loaded-modules.txt').read_text().splitlines()]
    modules={p.name.casefold() for p in mapped}
    required={'orbiter.exe','productioncockpitdriver.dll','opengl32.dll','libgallium_wgl.dll','oglclient.dll','deltaglider.dll','shuttlea.dll'}
    require(required<=modules,'Actual original application/observer/client/provider/vessel DLL missing')
    bindings=json.loads((folder/'mesa-bindings.json').read_text());effective={n.casefold():v for n,v in bindings['bindings'].items()};mesa={n.casefold():v for n,v in bindings['runtime']['files'].items()}
    expected_paths={n.casefold():v for n,v in expected_binaries.items()};loaded=[]
    for name in sorted(required):
        paths=[p for p in mapped if p.name.casefold()==name];require(len(paths)==1,'Required actual module path is missing or ambiguous: '+name)
        path=paths[0];require(folder.resolve() in path.parents,'Required original module came from outside the staged runtime: '+str(path))
        relative=path.relative_to(folder.resolve()).as_posix().casefold();value=sha(path)
        if name in mesa:expected_hash=effective.get(name,{}).get('effective_sha256',mesa[name]['sha256'])
        else:require(relative in expected_paths,'Executed original module is unrecorded: '+relative);expected_hash=expected_paths[relative]
        require(value==expected_hash,'Executed original module bytes differ: '+name);loaded.append(dict(path=str(path),sha256=value))
    saved=folder/'Scenarios/PausedResult.scn';state=parse_saved(saved);require({n:v['class_name'] for n,v in state['ships'].items()}==expected and state['focus']=='GL-02','Actual original saved graph/focus differs')
    math_profile=(folder/'pause-math.txt').read_text().strip();require(math_profile in ('sse2','fma3'),'Original CRT profile missing')
    return dict(frames=frames,paused_frames=8,paused_seconds=paused[0]['seconds'],paused_mjd=paused[0]['mjd'],successful_presents=life['successful_presents'],actual_vessels=expected,actual_math=math_profile,clock_sha256=sha(folder/'pause-clock.csv'),vessel_state_sha256=sha(folder/'pause-vessels.csv'),saved_sha256=sha(saved),saved_state=state,saved_path=str(saved),renderer=renderer,actual_loaded_required_modules=loaded,physics_steps=case['pause_tick'] if phase=='writer' else 0)

def run(a):
    import os
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    config=settings();require(not a.output.exists(),'Fresh original paused diagnostic output required');a.output.mkdir(parents=True)
    manifest=json.loads((a.orbiter.parent/'test-runtime.json').read_text());inputs=json.loads((a.orbiter.parent/'named-original-inputs.json').read_text())
    require(manifest['source_commit']==inputs['application_source']==config['application_source'] and inputs['configuration']==a.configuration,'Exact already accepted original runtime/SDK required')
    require(all(sha(a.orbiter.parent/n)==v for n,v in manifest['files'].items()) and all(sha(a.orbiter.parent/n)==v for n,v in inputs['original_client_files_sha256'].items()),'An original application/SDK/client file changed')
    expected_binaries={**manifest['files'],**inputs['original_client_files_sha256'],'Modules/Plugin/ProductionCockpitDriver.dll':sha(a.orbiter.parent/'Modules/Plugin/ProductionCockpitDriver.dll')}
    report=dict(status='running',diagnostic_source=__import__('subprocess').check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),application_source=config['application_source'],configuration=a.configuration,math_profile=a.math_profile,cases={},native_admission_qualified=False,phase6_complete=False,scope='Original paused save/read/write diagnostic at the observed native pause ticks in both unchanged complete docked-ISS entry points. Every saved semantic token difference is retained. No numerical tolerance, frozen reference, original physics, source module or acceptance budget is changed; no evidence archive, SDK, runtime or provider is uploaded.')
    report_file=a.output/'diagnostic.json'
    def save():report_file.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for case in config['cases']:
            body,expected=scenario(case);results=[]
            for repeat in (1,2):
                pair={};parent=None
                for phase in ('writer','reload'):
                    folder=a.output/(case['id']+'-'+str(repeat)+'-'+phase);run_body=body if parent is None else parent.read_bytes()
                    def configure(directory):
                        cfg=configuration((directory/'Orbiter.cfg').read_text());cfg=cfg.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient');(directory/'Orbiter.cfg').write_text(cfg)
                        (directory/'Scenarios/Behavior.scn').write_bytes(run_body)
                        (directory/'pause-case.txt').write_text(f"{phase} {case['pause_tick']} {case['cockpit']} {a.math_profile}\n")
                        (directory/'pause-vessels.txt').write_text(''.join(n+' '+v+'\n' for n,v in expected.items()))
                        (directory/'ogl-evidence.enabled').write_text('Exact original complete docked paused save diagnostic\n')
                        mesa_files(a.mesa.resolve(),directory)
                    frames=case['pause_tick']+8 if phase=='writer' else 8
                    try:stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),folder,dict(frames=frames,fixed_step=config['fixed_step']),configure)
                    except BaseException:
                        failure=folder/'pause-failure.txt';print('ORIGINAL_DOCKED_PAUSE_FAILURE='+json.dumps(dict(case=case['id'],phase=phase,error=failure.read_text() if failure.exists() else 'See actual original process exit',console_tail=(folder/'console.txt').read_text(errors='replace')[-2000:] if (folder/'console.txt').exists() else '')),flush=True);raise
                    actual=inspect(folder,case,phase,config,expected,parent,expected_binaries);require(a.math_profile!='sse2' or actual['actual_math']=='sse2','Actual original SSE2 CRT selection differs');pair[phase]=actual;parent=Path(actual['saved_path'])
                pair['exact_semantic_differences']=content_differences(pair['writer']['saved_state'],pair['reload']['saved_state'])
                results.append(pair)
            for phase in ('writer','reload'):
                for key in ('clock_sha256','vessel_state_sha256','saved_sha256'):require(results[0][phase][key]==results[1][phase][key],'Original paused diagnostic repeat differs: '+phase+'/'+key)
            require(results[0]['exact_semantic_differences']==results[1]['exact_semantic_differences'],'Original paused semantic deltas differ between repetitions')
            report['cases'][case['id']]=dict(scenario=case['scenario'],scenario_sha256_lf=case['sha256_lf'],pause_tick=case['pause_tick'],runs=results,repeated_original_semantic_changes_identical=True);save()
        require(all(sha(a.orbiter.parent/n)==v for n,v in manifest['files'].items()) and all(sha(a.orbiter.parent/n)==v for n,v in inputs['original_client_files_sha256'].items()),'Owning original runtime/SDK/client changed during execution')
        report['owning_original_runtime_sdk_client_unchanged']=True
        report['status']='completed-original-paused-docked-roundtrip-diagnostic'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    compact=dict(status=report['status'],application_source=report['application_source'],configuration=a.configuration,math_profile=a.math_profile,actual_processes=8,cases={n:dict(scenario=v['scenario'],pause_tick=v['pause_tick'],original_vessels=v['runs'][0]['writer']['actual_vessels'],writer_paused_seconds=v['runs'][0]['writer']['paused_seconds'],writer_paused_mjd=v['runs'][0]['writer']['paused_mjd'],reload_paused_seconds=v['runs'][0]['reload']['paused_seconds'],reload_paused_mjd=v['runs'][0]['reload']['paused_mjd'],reload_physics_steps=v['runs'][0]['reload']['physics_steps'],exact_original_semantic_differences=v['runs'][0]['exact_semantic_differences'],repetitions_identical=True) for n,v in report['cases'].items()},native_admission_qualified=False,phase6_complete=False)
    print('ORIGINAL_DOCKED_PAUSE_DIAGNOSTIC='+json.dumps(compact,sort_keys=True),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True);run(p.parse_args())
