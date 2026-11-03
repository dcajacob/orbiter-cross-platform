#!/usr/bin/env python3
"""Record through the original UI, then load the resulting real flight streams."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from focus_bars import scenario,require

def click(actions,tick,x,y):
    for offset,event in enumerate(('move','left_down','left_up')):
        actions.append((tick+offset,'ui',f'{event} {x} {y} -'))

def control(actions,tick,key):
    actions.extend([(tick,'key','29'),(tick,'key',str(key)),
                    (tick+1,'key',str(-key)),(tick+1,'key','-29')])

def launch(args,name,source,actions,frames=80):
    out=args.output/name;out.mkdir()
    for marker in ('playback.enabled','menu-evidence.enabled','instrument-evidence.enabled'):
        (out/marker).touch()
    config=out/'Orbiter.cfg'
    config.write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+
                      '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\n')
    replay=out/'replay.csv'
    replay.write_text('tick,phase,action,value\n'+''.join(
        f'{t},pre,{action},{value}\n' for t,action,value in sorted(actions,key=lambda x:x[0])))
    command=[str(args.executable),'--config',str(config),'--scenario',str(source),
        '--save',str(out/'saved.scn'),'--evidence',str(out),'--replay',str(replay),
        '--frames',str(frames),'--fixed-step','0.25','--fixed-ui-clock','--frame-delay-ms','60','--run']
    for key in ('assets','data','modules','planets'):command+=['--'+key,str(getattr(args,key))]
    (out/'invocation.json').write_text(json.dumps(command,indent=2)+'\n')
    with (out/'console.log').open('w') as log:
        subprocess.run(command,cwd=out,env=os.environ,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    lifecycle=json.loads((out/'graphics-lifecycle.json').read_text())
    require(lifecycle['successful_presents']==frames and lifecycle['context_deleted'],'Incomplete recorder lifecycle')
    with (out/'playback-state.csv').open() as stream:states=list(csv.DictReader(stream))
    return out,states

def verify_streams(out):
    flight=out/'Flights/test_record'
    counts={}
    for vessel in ('dg','dg2','iss'):
        for extension in ('pos','att','atc'):
            path=flight/(vessel+'.'+extension)
            require(path.is_file(),'Missing actual vessel recording '+str(path))
            rows=path.read_text().splitlines()
            data=[line for line in rows if line and line[0].isdigit()]
            require(len(data)>=2,'Missing recorder samples '+str(path))
            timestamps=[float(line.split()[0]) for line in data]
            require(timestamps==sorted(timestamps),'Recorder time went backwards')
            counts[path.name]=len(data)
    events=(flight/'system.dat').read_text().splitlines()
    require(any(' TACC 2.000000' in x for x in events),'Time acceleration was not recorded')
    require(any(' FOCUS DG2' in x for x in events),'Focus change was not recorded')
    saved=out/'Playback/test_record.scn'
    require(saved.read_text().count('FLIGHTDATA')==3,'Saved playback did not mark every original vessel')
    return saved,counts,events

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('executable','assets','data','modules','planets','output'):
        parser.add_argument('--'+key,type=lambda x:Path(x).resolve(),required=True)
    args=parser.parse_args();args.output.mkdir()
    source=args.output/'initial.scn';source.write_text(scenario())
    actions=[]
    control(actions,3,63) # Ctrl+F5 opens the original recorder dialog.
    click(actions,8,90,117) # REC
    click(actions,13,377,71)
    actions.extend([(16,'main','.3'),(20,'warp','2'),(26,'focus','DG2'),
                    (40,'warp','1'),(50,'main','0')])
    control(actions,65,46) # Ctrl+C stops and flushes all streams.
    recorded,_=launch(args,'record',source,actions)
    saved,counts,events=verify_streams(recorded)
    played,states=launch(args,'playback',saved,[],frames=70)
    require(states[0]['playback']=='1','New flight did not enter actual vessel playback')
    require(any(row['object']=='DG2' for row in states),'Recorded focus was not replayed')
    require(any(float(row['warp'])==2 for row in states),'Recorded speed was not replayed')
    require(states[-1]['playback']=='0','Playback did not reach its end and release streams')
    actions=[]
    control(actions,3,63)
    click(actions,8,90,245) # Editor
    click(actions,13,90,590) # Insert NOTE
    click(actions,17,145,614) # Insert CAMERA using current camera mode
    click(actions,21,90,638) # Delete selected CAMERA (must release its event)
    click(actions,25,575,634) # Commit
    click(actions,29,145,590) # Insert NOTEOFF
    click(actions,33,710,634) # Discard uncommitted NOTEOFF
    click(actions,37,948,71) # Close editor
    control(actions,42,46) # Return to free flight
    edited,states=launch(args,'editor',saved,actions,frames=55)
    copied=edited/'Flights/test_record'
    edited_events=(copied/'system.dat').read_text().splitlines()
    require(len(edited_events)==len(events)+1 and sum(' NOTE New note' in x for x in edited_events)==1,
            'Playback editor did not commit the inserted note')
    require(not any(' CAMERA ' in x or ' NOTEOFF' in x for x in edited_events),
            'Playback editor did not delete or discard uncommitted events')
    require((recorded/'Flights/test_record/system.dat').read_text().splitlines()==events,
            'Editing modified the source flight instead of the user copy')
    for filename in counts:
        require((copied/filename).read_bytes()==(recorded/'Flights/test_record'/filename).read_bytes(),
                'Editor changed a vessel motion or event stream')
    require((edited/'Playback/test_record.scn').is_file(),'Edited flight lacks its initial playback scenario')
    require(states[-1]['playback']=='0','Editor prevented manual return to free flight')
    _,states=launch(args,'edited-playback',edited/'Playback/test_record.scn',[],frames=35)
    require(states[0]['playback']=='1' and any(row['object']=='DG2' for row in states),
            'Edited flight did not reload in a fresh process')
    actions=[];control(actions,3,46)
    shutdown,states=launch(args,'record-until-exit',source,actions,frames=20)
    for vessel in ('dg','dg2','iss'):
        rows=(shutdown/'Flights/initial'/(vessel+'.pos')).read_text().splitlines()
        samples=[line for line in rows if line and line[0].isdigit()]
        require(len(samples)>=2 and float(samples[-1].split()[0])>=4,
                'Exit did not flush the last vessel sample')
    report=dict(samples=counts,system_events=events,replayed_focus=True,replayed_warp=True,
                playback_ended=True,editor_committed=True,editor_deleted=True,editor_discarded=True,
                recording_scenario=str(saved),exit_flushed=True,lifecycle=True)
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
