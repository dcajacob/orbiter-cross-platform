"""Run one focused native macOS desktop check, preserving inputs and receipts."""
import argparse
import csv
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT/'Tests/Production/StockScenarios'))
from inventory import ships

STOCK = 'Scenarios/Delta-glider/DG Mk4 in orbit.scn'
EDITED = 'NewVessel'
CONFIG = ROOT/'Tests/Production/NativeScene/Orbiter.cfg'
START_OPTIONS = ('0.25','6','1','1')
CHANGED_OPTIONS = ('0.35','7','1.1','0')
RENDERER = 'Apple Software Renderer'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def execution(argv, output, frames, env=None, logname='console.log'):
    with (output/logname).open('w') as log:
        process = subprocess.Popen([str(elt) for elt in argv], cwd=output, stdout=log,
                                   stderr=subprocess.STDOUT, env=env)
        try:
            code = process.wait(timeout=210)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            (output/(logname+'.process.json')).write_text(json.dumps(
                dict(pid=process.pid, returncode=process.returncode))+'\n')
    require(code==0, f'Process {process.pid} returned {code} in {output.name}')
    log = (output/logname).read_text(errors='replace')
    require(not any(marker in log for marker in ('AddressSanitizer', 'LeakSanitizer',
                                                'runtime error:', 'Orbiter native production:')),
            'Simulator reported an error')
    return process.pid


def graphics(output, frames):
    life = json.loads((output/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=frames,successful_presents=frames,context_deleted=True),
            'Native render/present/cleanup incomplete')
    geometry=json.loads((output/'native-window.json').read_text())
    require((geometry['backend'], geometry['framebuffer_width'], geometry['framebuffer_height'])
            ==('cocoa',1280,720),'The previously verified Cocoa viewport changed')
    renderer=json.loads((output/'renderer-info.json').read_text())
    require(RENDERER in renderer['renderer'],'Unexpected hosted renderer')
    return life


def flight(a, name, config, commands, frames=40, *, scenario=None, running=False, sound=None, menus=False):
    output = a.output/name
    output.mkdir()
    scenario = scenario or a.stock
    original = digest(scenario)
    replay = output/'replay.csv'
    replay.write_text('tick,phase,action,value\n'+
                      ''.join(f'{tick},before,{command},{value}\n' for tick,command,value in commands))
    if menus:
        (output/'menu-evidence.enabled').touch()
    save = output/'Flight.scn'
    argv = [a.engine/'orbiter-production','--assets',a.assets,'--data',a.data,
            '--modules',a.engine/'NativeModules','--planets',a.planets,'--config',config,
            '--scenario',scenario,'--evidence',output,'--save',save,'--frames',frames,
            '--fixed-step','0.0625','--fixed-system-step','0.0625','--fixed-ui-clock','--replay',replay]
    if running:
        argv.append('--run')
    if sound:
        argv.extend(('--xrsound-assets',sound,'--frame-delay-ms','22'))
    (output/'invocation.json').write_text(json.dumps([str(value) for value in argv],indent=2)+'\n')
    pid=execution(argv,output,frames)
    lifetime=graphics(output,frames)
    require(digest(scenario)==original,'Input scenario changed')
    require('Production DeltaGlider flight.' in (output/'console.log').read_text(errors='replace'),
            'The real stock Delta-glider did not start')
    return output,save,dict(pid=pid,input_sha256=original,lifecycle=lifetime)


def tap(tick,code):
    return [(tick,'key',code),(tick+1,'key',-code)]


def clicks(tick, x, y):
    return [(tick,'ui',f'move {x} {y} -'),
            (tick+1,'ui',f'left_down {x} {y} -'),
            (tick+2,'ui',f'left_up {x} {y} -')]


def dialog_origin(path,title):
    found=[row for row in read_csv(path/'menu-windows.csv') if title in row['name']]
    require(found,f'Expected dialog did not render: {title}')
    return int(float(found[-1]['x'])),int(float(found[-1]['y']))


def verify_options(a):
    config=a.output/'Orbiter.cfg'
    config.write_text(CONFIG.read_text()+
        '\nInstrumentUpdateInterval = 0.25\nGenericMFDSize = 6\nPanelScale = 1.0\nUnlimitedFuel = FALSE\n')
    # Position is observed on this renderer before exercising the actual controls.
    probe,_,_=flight(a,'position',config,tap(2,64),frames=10,menus=True)
    x,y=dialog_origin(probe,'Orbiter: Options')
    keys=('refresh','size','panel_scale','limited_fuel')
    def options(row):
        return tuple(row[key] for key in keys)
    commands=tap(2,64)
    for tick,dx,dy in ((8,480,58),(14,480,82),(20,480,202),(26,40,58),(32,276,58)):
        commands.extend(clicks(tick,x+dx,y+dy))
    first,_,edit=flight(a,'edit',config,commands,frames=38,menus=True)
    rows=read_csv(first/'options-state.csv')
    require(options(rows[0])==START_OPTIONS and options(rows[-1])==CHANGED_OPTIONS,
            'Live Options did not record all four edits')
    expected=('InstrumentUpdateInterval = 0.35','GenericMFDSize = 7',
              'PanelScale = 1.1','UnlimitedFuel = TRUE')
    require(set(expected)<=set(config.read_text().splitlines()),'Updated Options were not saved')
    config_before=digest(config)
    second,_,reload=flight(a,'reload',config,[],frames=4,menus=True)
    restored=options(read_csv(second/'options-state.csv')[-1])
    require(restored==CHANGED_OPTIONS and digest(config)==config_before,'Restart lost the saved Options')
    require(edit['pid']!=reload['pid'],'Options reload requires a new process')
    return dict(first=edit,restarted=reload,settings=dict(zip(keys,restored)),config_sha256=config_before)


def saved_state(path):
    data=path.read_text(encoding='cp1252')
    epoch=re.search(r'^\s*Date MJD\s+(\S+)',data,re.M)
    require(epoch is not None, 'Saved scenario is missing its epoch')
    return data,ships(data),epoch[1]


def vessel_fields(data):
    match=re.search(r'^NewVessel:ShuttlePB\n(.*?)^END\s*$', data, re.M|re.S)
    require(match is not None,'Edited ShuttlePB is missing')
    return dict(line.strip().split(maxsplit=1) for line in match[1].splitlines() if line.strip())


def coordinates(fields,key):
    values=tuple(map(float,fields[key].split()))
    require(len(values)==3 and all(math.isfinite(v) for v in values), 'Invalid saved vector '+key)
    return values


def verify_editor(a):
    config=a.output/'Orbiter.cfg'
    config.write_bytes(CONFIG.read_bytes())
    _,original,epoch=saved_state(a.stock)
    commands=tap(2,65)
    probe,_,_=flight(a,'position',config,commands,frames=10,menus=True)
    x,y=dialog_origin(probe,'Scenario editor')
    add=commands+clicks(8,x+45,y+135)
    added,added_save,_=flight(a,'add',config,add+[(17,'save',0)],frames=20)
    added_text,added_roster,added_epoch=saved_state(added_save)
    expected=dict(original,NewVessel='ShuttlePB')
    require(added_roster==expected and abs(float(added_epoch)-float(epoch))<1e-7,
            'The paused add changed the stock roster or epoch')
    added_fields=vessel_fields(added_text)

    move=add+clicks(15,x+80,y+242)
    move.extend([(19,'ui','text 0 0 4000000'),(21,'ui','key_down 13 0 -'),
                 (22,'ui','key_up 13 0 -')])
    move+=clicks(27,x+48,y+313)
    _,moved_save,moved=flight(a,'move',config,move+[(36,'save',0)],frames=40)
    moved_text,moved_roster,moved_epoch=saved_state(moved_save)
    moved_fields=vessel_fields(moved_text)
    require(moved_roster==expected and moved_epoch==added_epoch,'Moving changed the stock roster or paused epoch')
    require(moved_fields['STATUS']==added_fields['STATUS']=='Orbiting Earth' and
        coordinates(moved_fields,'RPOS')==(4000000.0,*coordinates(added_fields,'RPOS')[1:]) and
        moved_fields['RVEL']==added_fields['RVEL'] and moved_fields.get('PRPLEVEL')==added_fields.get('PRPLEVEL'),
        'The editor did not apply the requested position while preserving velocity and fuel')

    _,restored_save,restored=flight(a,'reload-moved',config,[(2,'save',0)],frames=5,scenario=moved_save)
    restored_text,restored_roster,restored_epoch=saved_state(restored_save)
    restored_fields=vessel_fields(restored_text)
    require(restored_roster==expected and restored_epoch==moved_epoch and
            restored_fields['STATUS']==moved_fields['STATUS'] and
            restored_fields.get('PRPLEVEL')==moved_fields.get('PRPLEVEL'),'Reload lost vessel metadata')
    for key,limit in (('RPOS',.001),('RVEL',.0001)):
        require(all(abs(pos-original_pos)<=limit for pos,original_pos in
                    zip(coordinates(restored_fields,key),coordinates(moved_fields,key))), 'Reload changed '+key)
    require(restored['pid']!=moved['pid'] and restored['input_sha256']==digest(moved_save),
            'Edited save was not reopened by another process')

    # Repeat the same short GUI edit so the new vessel remains selected for deletion.
    remove=move+clicks(35,x+133,y+313)+clicks(43,x+65,y+357)
    _,removed_save,removed=flight(a,'remove',config,remove+[(52,'save',0)],frames=56)
    _,removed_roster,removed_epoch=saved_state(removed_save)
    require(removed_roster==original and removed_epoch==moved_epoch,'Removal changed other vessels or paused epoch')
    _,final_save,final=flight(a,'reload-removed',config,[(2,'save',0)],frames=5,scenario=removed_save)
    _,last_roster,last_epoch=saved_state(final_save)
    require(last_roster==original and last_epoch==removed_epoch and final['pid']!=removed['pid']
            and final['input_sha256']==digest(removed_save),'Deletion did not persist on restart')
    return dict(added=added_roster,position=coordinates(moved_fields,'RPOS'),moved=moved,reloaded=restored,
                removed=removed,removal_reloaded=final,
                position_tolerance_m=.001,velocity_tolerance_mps=.0001)


def verify_launchpad(a):
    require(a.launcher is not None,'The native Qt launcher fixture is required')
    config=a.output/'Orbiter.cfg'
    config.write_bytes(CONFIG.read_bytes())
    # QProcess launches this test-only wrapper, which records Qt's chosen arguments
    # and execs the real binary in the same process with a short normal exit limit.
    wrapper=a.output/'orbiter-short-check'
    wrapper.write_text('''#!/bin/sh
set -eu
printf '%s\\n' "$@" > "$ORBITER_MAC_QT_ARGUMENTS"
exec "$ORBITER_MAC_QT_ENGINE" "$@" --frames 12 --evidence "$ORBITER_MAC_QT_EVIDENCE"
''')
    wrapper.chmod(0o755)
    profile=a.output/'profile.json'
    profile.write_text(json.dumps(dict(mode='native',executable=str(wrapper),assets=str(a.assets),
        data=str(a.data),modules=str(a.engine/'NativeModules'),planets=str(a.planets),
        config=str(config),saves=str(a.output/'saves'))))
    original=digest(a.stock)
    env=dict(os.environ,QT_QPA_PLATFORM='cocoa',ORBITER_LAUNCHPAD_TEST_SETTINGS=str(a.output/'settings'),
             ORBITER_LAUNCHPAD_TEST_RECEIPT=str(a.output/'launchpad-events.txt'),
             ORBITER_MAC_QT_ENGINE=str(a.engine/'orbiter-production'),
             ORBITER_MAC_QT_ARGUMENTS=str(a.output/'launch-arguments.txt'),ORBITER_MAC_QT_EVIDENCE=str(a.output))
    execution([a.launcher,'--profile',profile],a.output,12,env,'launcher.log')
    args=(a.output/'launch-arguments.txt').read_text().splitlines()
    require(args[args.index('--scenario')+1]==str(a.stock) and digest(a.stock)==original,
            'Qt did not launch the exact original scenario')
    events=(a.output/'launchpad-events.txt').read_text().splitlines()
    require(events==['selected-and-launched-stock-scenario','launcher-hidden-during-flight',
                     'launcher-returned-with-selection'],'Qt Launchpad did not restore the selected flight on exit')
    session_log=a.output/'orbiter-session.log'
    require('Production DeltaGlider flight.' in session_log.read_text(errors='replace'),
            'Qt did not launch the production simulation')
    return dict(launchpad_events=events,source_input_sha256=original,lifecycle=graphics(a.output,12),
                process='Qt selected the original scenario; test wrapper execed the native binary with a 12-frame limit')


def audio_receipt(path):
    log=(path/'XRSound.log').read_text(errors='replace')
    line=next((line for line in log.splitlines() if 'initialized using sound driver ' in line),'')
    backend=line.partition('initialized using sound driver ')[2].partition('.')[0]
    require(backend.casefold()=='core audio' or backend.casefold()=='coreaudio',
            'Native Core Audio backend was unavailable')
    owned=[line for line in log.splitlines() if '[GL-01]' in line]
    def index(verb,sound):
        return next((i for i,line in enumerate(owned) if verb in line and f'soundID = {sound},' in line),-1)
    positions=[index('PlayWav playing sound',10004),index('StopWavImpl: stopping sound',10004),
               index('PlayWav playing sound',10008),index('StopWavImpl: stopping sound',10008)]
    require(positions[0]>=0 and all(left<right for left,right in zip(positions,positions[1:])),
            'Main engine and RCS voices did not start and stop in order')
    require(not any(marker in log for marker in ('could not initialize default sound device',
                'could not play sound','Cannot open audio device')), 'Audio reported a runtime error')
    return backend


def verify_audio(a):
    config=a.output/'Orbiter.cfg'
    config.write_bytes(CONFIG.read_bytes())
    assets=a.output/'sound'
    shutil.copytree(ROOT/'Sound/XRSound/assets/XRSound',assets/'XRSound')
    settings=assets/'XRSound/XRSound.cfg'
    old=settings.read_text(encoding='cp1252')
    require(old.count('EnableVerboseLogging = 0')==1,'Unexpected stock audio configuration')
    settings.write_text(old.replace('EnableVerboseLogging = 0','EnableVerboseLogging = 1'),encoding='cp1252')
    commands=[(12,'main',1),(29,'pause',1),(38,'pause',0),(57,'main',0)]
    commands.extend((tick,'rcs3',1) for tick in range(64,83))
    commands.append((95,'save',0))
    first,saved,original=flight(a,'original',config,commands,frames=100,running=True,sound=assets)
    second,_,reload=flight(a,'reload',config,commands,frames=100,running=True,sound=assets,scenario=saved)
    require(original['pid']!=reload['pid'] and reload['input_sha256']==digest(saved),
            'XRSound reload did not start from the exact save in a fresh process')
    drivers=[audio_receipt(path) for path in (first,second)]
    return dict(first=original,reloaded=reload,drivers=drivers,physical_audio_endpoint_verified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','assets','data','planets','output'):
        parser.add_argument('--'+name,type=lambda path:Path(path).resolve(),required=True)
    parser.add_argument('--launcher',type=lambda path:Path(path).resolve())
    parser.add_argument('--source',required=True)
    parser.add_argument('--check',choices=('options','editor','xrsound','launchpad'),required=True)
    a=parser.parse_args()
    a.output.mkdir(parents=True)
    a.stock=a.assets/STOCK
    locks=json.loads((ROOT/'Tests/Production/production-source.lock.json').read_text())
    original=next(case['sha256'] for case in locks['scenarios'] if case['path']==STOCK)
    require(sha256(a.stock.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==original and
            digest(a.stock)==digest(ROOT/STOCK),'Original stock scene source changed')
    cases={'options':verify_options,'editor':verify_editor,'xrsound':verify_audio,'launchpad':verify_launchpad}
    receipt=dict(source=a.source,check=a.check,scenario=STOCK,status='failed',full_runs_invoked=False)
    try:
        receipt.update(details=cases[a.check](a),status='passed')
    except Exception as failure:
        receipt['error']=str(failure)
        raise
    finally:
        (a.output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
