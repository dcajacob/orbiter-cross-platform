"""Observe two complete-scene cases without changing frozen acceptance pins."""
import argparse,json,os,sys
from pathlib import Path
from common import HERE,ROOT,require,sha,rows,settings,scenario,configuration,summarize
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'Client'),str(HERE.parent/'Cockpit')]
from stage import run as stage
from run_client import mesa_files

def inspect(folder,case):
    require(not (folder/'named-failure.txt').exists(),'Original SDK diagnostic failed')
    require((folder/'named-complete.txt').read_text().strip()=='60','Original process did not complete')
    info=json.loads((folder/'renderer-info.json').read_text());require('llvmpipe' in info['renderer'].lower(),'Pinned real original software renderer missing: '+json.dumps(info,sort_keys=True))
    require(not (folder/'graphics-errors.txt').exists() or not (folder/'graphics-errors.txt').read_text().strip(),'Original renderer errors')
    result=summarize(folder,case);result['actual_math']=(folder/'named-math.txt').read_text().strip();result['renderer']=info;return result

def run(a):
    # Match the accepted original cockpit reference's actual Mesa selection.
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    config=settings();require(not a.output.exists(),'Fresh original diagnostic output required');a.output.mkdir(parents=True)
    runtime=json.loads((a.orbiter.parent/'test-runtime.json').read_text());inputs=json.loads((a.orbiter.parent/'named-original-inputs.json').read_text())
    require(runtime['source_commit']==inputs['application_source']==config['application_source'] and inputs['configuration']==a.configuration,'Exact frozen original package required')
    require(all(sha(a.orbiter.parent/n)==v for n,v in runtime['files'].items()),'Original runtime or SDK changed before observation')
    require(all(sha(a.orbiter.parent/n)==v for n,v in inputs['original_client_files_sha256'].items()),'Captured original client changed')
    report=dict(status='running',application_source=config['application_source'],configuration=a.configuration,math_profile=a.math_profile,cases={},native_admission_qualified=False,phase6_complete=False,scope='Two full eight-object derived-scene diagnostics; no new frozen reference or unchanged named-mission acceptance. No evidence archives or binaries are uploaded.')
    path=a.output/'diagnostic.json'
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for case in config['cases']:
            runs=[]
            for repeat in (1,2):
                folder=a.output/(case['id']+'-'+str(repeat));body,expected=scenario(case)
                def configure(directory):
                    cfg=configuration((directory/'Orbiter.cfg').read_text());cfg=cfg.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient');(directory/'Orbiter.cfg').write_text(cfg)
                    (directory/'Scenarios/Behavior.scn').write_bytes(body)
                    (directory/'named-case.txt').write_text(f"{case['target']} {case['cockpit']} {case['hud']} {a.math_profile}\n")
                    (directory/'named-vessels.txt').write_text(''.join(n+' '+v+'\n' for n,v in expected.items()))
                    for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):(directory/name).write_text('Complete eight-object original SDK diagnostic\n')
                    mesa_files(a.mesa.resolve(),directory)
                stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),folder,dict(frames=60,fixed_step=.25),configure)
                result=inspect(folder,case);require(result['actual_math'] in ('sse2','fma3') and (a.math_profile!='sse2' or result['actual_math']=='sse2'),'Actual original CRT profile differs');runs.append(result)
            for key in ('raw_state_sha256','raw_vessel_state_sha256','hud_changes','second_DG_visual_registration_frames','nonfinite_text_labels','nonfinite_text_values'):
                require(runs[0][key]==runs[1][key],'Original repeat differs: '+key)
            report['cases'][case['id']]=dict(runs=runs,identical_discrete_and_vessel_repeats=True);save()
        report['status']='completed-original-full-scene-diagnostics'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    # Normal concise CI test output only. Full runtime/SDK/provider/trace archives
    # are intentionally absent from this workflow; accepted pins stay unchanged.
    compact=dict(status=report['status'],application_source=report['application_source'],configuration=a.configuration,math_profile=a.math_profile,actual_processes=4,cases={name:value['runs'][0] for name,value in report['cases'].items()},native_admission_qualified=False,phase6_complete=False)
    print('ORIGINAL_NAMED_SCENE_DIAGNOSTIC='+json.dumps(compact,sort_keys=True),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--math-profile',choices=('automatic','sse2'),required=True);run(p.parse_args())
