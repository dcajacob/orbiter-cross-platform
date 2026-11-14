"""Exercise the stock Win32 editor, in-flight Options and XRSound with short sessions."""
import argparse
import csv
import json
import sys
from pathlib import Path
import shutil

PRODUCTION = Path.cwd() / 'Tests/Production'
sys.path[:0] = [str(PRODUCTION/'RemainingStock'), str(PRODUCTION/'Client')]
from inputs import ROOT, digest, require, sha_lf
from run_client import mesa_files
from stage_original import run as stage
from inventory import ships

STOCK = 'Scenarios/Delta-glider/DG Mk4 in orbit.scn'
EDITED = 'Phase7-ShuttlePB'


def cfg_value(case, key, default=None):
    lines = (case/'Orbiter.cfg').read_text().splitlines()
    matches = [line.partition('=')[2].strip() for line in lines
               if line.partition('=')[0].strip().casefold()==key.casefold()]
    require(len(matches)<=1, f'Duplicate configuration key {key}')
    return matches[0] if matches else default


def scn_state(path):
    return ships(path.read_bytes().decode('cp1252'))


def check_state(path, expected_present):
    state = scn_state(path)
    base = scn_state(ROOT/STOCK)
    expected = {**base,EDITED:'ShuttlePB'} if expected_present else base
    require(state==expected,'Editor save lost or changed a stock vessel or the edited vessel')
    if expected_present:
        block = path.read_text(encoding='cp1252').split(EDITED+':ShuttlePB',1)[1].split('END',1)[0]
        values = {line.split(maxsplit=1)[0]:line.split(maxsplit=1)[1] for line in block.splitlines()
                  if len(line.split(maxsplit=1))==2}
        require(values['STATUS']=='Orbiting Earth','Edited vessel orbit/reference changed')
        for key, vector, budget in (('RPOS',(6801234,200,300),.01),('RVEL',(3,-20,7600),1e-5)):
            observed = list(map(float,values[key].split()))
            require(len(observed)==3 and all(abs(a-b)<=budget for a,b in zip(observed,vector)),key)
    return digest(path)


def options_check(case, second):
    want = (.45,8,1.2,'FALSE') if second else (.35,7,1.1,'TRUE')
    actual = (float(cfg_value(case,'InstrumentUpdateInterval',.25)),
              int(cfg_value(case,'GenericMFDSize',6)),float(cfg_value(case,'PanelScale',1)),
              cfg_value(case,'UnlimitedFuel','FALSE'))
    require(all(abs(a-b)<1e-8 for a,b in zip(actual[:3],want[:3])) and actual[3].upper()==want[3],
            f'Live Options clicks did not persist: got {actual}, expected {want}')
    return actual


def audio_check(case, events):
    log = (case/'XRSound.log').read_text(errors='replace')
    backend = next((line.split('initialized using sound driver ',1)[1].split('.',1)[0]
                    for line in log.splitlines() if 'initialized using sound driver ' in line),None)
    require(backend,'XRSound backend did not initialize')
    for sound in (10004,10008):
        require(any(f'soundID = {sound},' in line and 'PlayWav playing sound' in line and 'GL-01' in line
                    for line in log.splitlines()),f'No successful Delta-glider sound playback event for {sound}')
    require(not any(marker in log for marker in ('Cannot open audio device','could not initialize default sound device',
                                               'could not play sound','Access Violation')), 'XRSound reported a runtime error')
    want = ['main-on','pause-requested','sim-paused','main-resumed','rcs-playing','thrust-idle']
    require([row['event'] for row in events]==want,'Audio action evidence incomplete')
    return {'backend':backend, 'engine_and_rcs_voice_verified':True, 'physical_audio_endpoint_verified':False}


def invoke(a, mode, incoming=None, previous_options=None):
    directory = a.output/mode
    is_audio = mode.startswith('audio')
    is_editor = mode.startswith('editor')
    frames = 96 if is_audio else 48
    entry = Path(STOCK) if incoming is None else Path('Scenarios')/incoming.name
    scenario = ROOT/STOCK if incoming is None else incoming
    input_sha = digest(scenario)
    cases = {'scenario_entry_point':entry.as_posix(),'scenario':entry.relative_to('Scenarios').as_posix(),
             'playback_vessels':[]}

    def configure(out):
        cfg=out/'Orbiter.cfg'
        text=cfg.read_text() if previous_options is None else previous_options.read_text()
        if previous_options is None:
            modules = ['Phase7Driver','OGLClient']
            if is_editor:
                modules.append('ScnEditor')
            if is_audio:
                modules.insert(0,'XRSound')
            text=text.replace('  ProductionBehaviorDriver',''.join(f'  {name}\n' for name in modules).rstrip('\n'))
            if not is_audio:
                text=text.replace('StartPaused = FALSE','StartPaused = TRUE')
            text+='\nInstrumentUpdateInterval = 0.25\nGenericMFDSize = 6\nPanelScale = 1.0\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\n'
        cfg.write_text(text,encoding='ascii')
        path=out/entry
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(scenario,path)
        (out/'phase7-mode.txt').write_text(mode+'\n')
        (out/'ogl-evidence.enabled').touch()
        mesa_files(a.mesa,out)
        if is_audio:
            shutil.copytree(a.sound_assets/'XRSound',out/'XRSound')
            sound_cfg=out/'XRSound/XRSound.cfg'
            body=sound_cfg.read_text(encoding='cp1252')
            require(body.count('EnableVerboseLogging = 0')==1,'Stock verbose setting differs')
            sound_cfg.write_text(body.replace('EnableVerboseLogging = 0','EnableVerboseLogging = 1'),encoding='cp1252')

    stage(a.runtime/'Orbiter.exe',a.data,a.planets,directory,{'fixed_step':.0625,'frames':frames,'delivery_repairs':[]},
          cases,configure,process_timeout=150)
    require((directory/'phase7-complete.txt').read_text().split()==[mode,str(frames)],'Windows probe completion differs')
    require(digest(directory/entry)==input_sha==digest(scenario),'Scenario input changed')
    lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text())
    require(lifecycle==dict(rendered_frames=frames,successful_presents=frames,context_deleted=True),'Render lifecycle incomplete')
    with (directory/'phase7-events.csv').open(newline='') as stream:
        events=list(csv.DictReader(stream))
    result=dict(source_input_sha256=input_sha,lifecycle=lifecycle,events=events)
    if is_editor:
        require(all(row['paused']=='1' and float(row['seconds'])==0 for row in events),'Editor advanced simulation time')
    if mode.startswith('options'):
        require(sum(row['event']=='options-click' for row in events)==5,'Options control input incomplete')
        result['configuration']=options_check(directory,incoming is not None or previous_options is not None)
    if mode=='editor-first':
        result['saved_sha256']=check_state(directory/'Scenarios/Phase7Edited.scn',True)
    if mode=='editor-reload':
        result['saved_sha256']=check_state(directory/'Scenarios/Phase7Removed.scn',False)
        require([row['event'] for row in events].count('position-verified')==1,'Edited live position was not restored')
    if mode=='editor-removed':
        require([row['event'] for row in events]==['deletion-reloaded'],'Removal reload evidence incomplete')
    if is_audio:
        result.update(audio_check(directory,events))
    return result



def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','data','planets','mesa','output','sound-assets'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--source',required=True)
    a=p.parse_args()
    require(sys.platform=='win32','A native Windows runner is required')
    manifest=json.loads((a.runtime/'test-runtime.json').read_text())
    require(manifest['source_commit']==a.source,'Windows SDK provenance differs')
    lock=json.loads((PRODUCTION/'production-source.lock.json').read_text())
    require(sha_lf(ROOT/STOCK)==next(case['sha256'] for case in lock['scenarios'] if case['path']==STOCK),
            'The selected stock scenario changed')
    for name in ('Orbiter.exe','Modules/Plugin/ScnEditor.dll','Modules/Plugin/XRSound.dll'):
        require(digest(a.runtime/name)==manifest['files'][name],f'Staged binary differs: {name}')
    a.output.mkdir(parents=True)
    report={'source':a.source,'status':'running','full_runs_invoked':False,'checks':{}}
    suites={
        'options':[
            ('options-first',None,None),
            ('options-reload',None,a.output/'options-first/Orbiter.cfg'),
        ],
        'editor':[
            ('editor-first',None,None),
            ('editor-reload',a.output/'editor-first/Scenarios/Phase7Edited.scn',None),
            ('editor-removed',a.output/'editor-reload/Scenarios/Phase7Removed.scn',None),
        ],
        'xrsound':[
            ('audio-first',None,None),
            ('audio-reload',a.output/'audio-first/Scenarios/Phase7Audio.scn',None),
        ],
    }
    for name, cases in suites.items():
        records=[]
        try:
            for mode, incoming, config in cases:
                records.append({'mode':mode,**invoke(a,mode,incoming,config)})
                print(mode,'passed',flush=True)
            report['checks'][name]={'status':'passed','sessions':records}
        except Exception as error:
            report['checks'][name]={'status':'failed','error':str(error),'sessions':records}
            print(name,'failed:',error,flush=True)
        (a.output/'phase7-ui-report.json').write_text(json.dumps(report,indent=2)+'\n')
    report['status']='passed' if all(c['status']=='passed' for c in report['checks'].values()) else 'failed'
    (a.output/'phase7-ui-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    sys.exit(main())
