#!/usr/bin/env python3
"""Send X11 mouse/keyboard events only to this test's native Orbiter window."""
import argparse,ctypes as C,ctypes.util,csv,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Flight')]
from reference import fixture
from keyboard_smoke import KeyEvent,Event,require,wait

def verify_menu(out,click,advance,button,key,move,window,title,process):
    def geometry(label):
        with (out/'menu-windows.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        return next((r for r in reversed(rows) if r.get('height') and label in r['name'] and r['frame']==rows[-1]['frame']),None)
    def dialog(label):
        return wait(lambda:geometry(label),'Missing stock dialog '+label)
    cfg=out/'ScriptFiles/config/menuinfobar.cfg'
    names=[v.split(' = ')[1] for v in cfg.read_text().splitlines() if 'Enabled' not in v]
    bar=dialog('##MenuInfoBar')
    move(640,360)
    def tap(name):
        key(window,name,True);advance();key(window,name,False);advance()
    tap('F4')
    wait(lambda:float(dialog('##MenuInfoBar')['y']) < -15,'F4 did not retract the menu')
    tap('F4')
    wait(lambda:float(dialog('##MenuInfoBar')['y']) == 0,'F4 did not show the menu')

    def command(name):
        # Stock sizes are 35 px, with an 18 px gap. Use the live menu's location.
        x=int(float(bar['x']))+18+8+17+53*names.index(name)
        click(x,25)
    command('Pause')
    wait(lambda:'PAUSED' in title(window),'Menu did not pause flight')
    command('Pause')
    wait(lambda:'RUNNING' in title(window),'Menu did not resume flight')
    command('Speed')
    speed=dialog('Time acceleration')
    click(int(float(speed['x']))+150,int(float(speed['y']))+38)
    wait(lambda:' | x10.000' in title(window),'Stock 10x speed button did not change the simulation clock')
    command('Ship')
    focus=dialog('Select spacecraft')
    x,y=int(float(focus['x'])),int(float(focus['y']))
    click(x+42,y+115)
    click(x+228,y+99)
    wait(lambda:' | DG2 | ' in title(window),'Menu ship selection did not change the focused vessel')
    help_requests=out/'help/requests.jsonl'
    help_enabled=(out/'help-probe.enabled').exists()
    def help_count():
        return len(help_requests.read_text().splitlines()) if help_requests.exists() else 0
    if help_enabled:
        command('Help')
        wait(lambda:help_count()==1,'Help menu did not launch the desktop viewer')
        move(1270,300)
        key(window,'Alt_L',True);tap('F1');key(window,'Alt_L',False);advance()
        wait(lambda:help_count()==2,'Alt-F1 did not launch help')
    command('Function')
    functions=dialog('Custom functions')
    fx,fy=int(float(functions['x'])),int(float(functions['y']))
    events=out/'custom-function-events.txt'
    if events.exists():
        click(fx+80,fy+38)
        wait(lambda:'first:context:self-unregister:reallocate:replace' in events.read_text(),'First SDK function did not run')
        if help_enabled:
            dialog('##NOTIF0')
            require(not geometry('##NOTIF1'),'Repeated Help failure was not deduplicated')
            time.sleep(.6);advance() # Let the original half-second fade complete.
            from PIL import ImageGrab
            ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(out/'help-notification.png')
            notice=dialog('##NOTIF0')
            click(int(float(notice['x']))+135,int(float(notice['y']))+15)
            wait(lambda:not geometry('##NOTIF0'),'Help error dismissal did not expire the original notification')
        click(fx+80,fy+38)
        wait(lambda:'second:context:remove-other:self-unregister' in events.read_text(),'Second SDK function did not run')
    click(fx+int(float(functions['width']))-12,fy+11)
    move(1270,300)
    key(window,'Control_L',True);tap('F4');key(window,'Control_L',False);advance()
    functions=dialog('Custom functions')
    click(int(float(functions['x']))+int(float(functions['width']))-12,int(float(functions['y']))+11)
    command('Record')
    recorder=dialog('Flight recorder/player')
    rx,ry=int(float(recorder['x'])),int(float(recorder['y']))
    click(rx+30,ry+57)
    recorded=out/'Playback/test_record.scn'
    wait(recorded.is_file,'Record menu did not save a playback scenario')
    for _ in range(12):advance()
    click(rx+30,ry+57)
    streams=out/'Flights/test_record'
    require(all((streams/(name+'.pos')).is_file() for name in ('dg','dg2','iss')),'Record menu did not write each vessel stream')
    before_record={p.name:p.read_bytes() for p in streams.iterdir() if p.is_file()}
    click(rx+30,ry+57)
    warning=dialog('Warning')
    wx,wy=int(float(warning['x'])),int(float(warning['y']))
    click(wx+110,wy+57)
    advance()
    require({p.name:p.read_bytes() for p in streams.iterdir() if p.is_file()}==before_record,
            'Cancel overwrote an existing recording')
    initial_scenario=recorded.read_bytes()
    click(rx+30,ry+57)
    warning=dialog('Warning')
    click(int(float(warning['x']))+42,int(float(warning['y']))+57)
    wait(lambda:recorded.read_bytes()!=initial_scenario,'Confirmed overwrite did not start a new flight recording')
    for _ in range(12):advance()
    click(rx+30,ry+57)
    require((streams/'dg.pos').read_bytes()!=before_record['dg.pos'],'Restart retained the old position stream')
    click(rx+int(float(recorder['width']))-12,ry+11)
    move(1270,300)
    key(window,'Control_L',True);tap('F5');key(window,'Control_L',False);advance()
    recorder=dialog('Flight recorder/player')
    click(int(float(recorder['x']))+int(float(recorder['width']))-12,int(float(recorder['y']))+11)
    command('Camera')
    camera=dialog('Orbiter: Camera')
    if help_enabled:
        click(int(float(camera['x']))+int(float(camera['width']))-55,int(float(camera['y']))+10)
        wait(lambda:help_count()==3,'Original camera dialog help button did not launch its topic')
    command('Options')
    options=dialog('Orbiter: Options')
    ox,oy=int(float(options['x'])),int(float(options['y']))
    def settings():
        with (out/'options-state.csv').open() as stream:return list(csv.DictReader(stream))[-1]
    click(ox+480,oy+58)
    wait(lambda:abs(float(settings()['refresh'])-.35)<1e-8,'MFD refresh option did not change')
    click(ox+480,oy+202)
    wait(lambda:abs(float(settings()['panel_scale'])-1.1)<1e-8,'Panel scale option did not change')
    click(ox+40,oy+58)
    click(ox+276,oy+58)
    wait(lambda:settings()['limited_fuel']=='0','Limited-fuel option did not reach the live configuration')
    for page in range(2,10):
        click(ox+80,oy+40+page*18)
    click(ox+int(float(options['width']))-12,oy+11)
    move(1270,300)
    tap('F8');tap('F8')
    before_width=int(settings()['mfd_width'])
    tap('F6')
    options=dialog('Orbiter: Options')
    click(ox+40,oy+40)
    click(ox+480,oy+82)
    wait(lambda:settings()['size']=='7' and int(settings()['mfd_width'])>before_width,
         'Glass cockpit MFD option did not resize the actual render target')
    resized_width=int(settings()['mfd_width'])
    click(ox+int(float(options['width']))-12,oy+11)
    move(1270,300)
    key(window,'Control_L',True);tap('F9');key(window,'Control_L',False);advance()
    options=dialog('Orbiter: Options')
    click(ox+int(float(options['width']))-12,oy+11)
    command('Info')
    dialog('Object info')
    command('Map')
    dialog('Orbiter: Map')
    button(window,640,24,True,3)
    advance()
    button(window,640,24,False,3)
    advance()
    dialog('Configure menu bars')
    command('Save')
    save=out/'Quicksave/cockpit 0001.scn'
    wait(save.is_file,'Stock menu quicksave missing')
    require('Ship DG2' in save.read_text() and 'BEGIN_CAMERA' in save.read_text(),'Quicksave lost the selected vessel or camera')
    # Exit destroys the window, so release cannot wait for another GUI frame.
    before_names=names[:]
    start=int(float(bar['x']))+43+53*names.index('Ship')
    button(window,start,25,True)
    advance()
    for offset in (8,18,30,44,57,68):
        move(start+offset,25)
    button(window,start+68,25,False)
    advance()
    def reordered():
        saved=[v.split(' = ')[1] for v in cfg.read_text().splitlines() if 'Enabled' not in v]
        return saved if len(saved)==len(names) and saved!=before_names else None
    names=wait(reordered,'Dragging a stock menu item did not persist its new order')
    require(sorted(names)==sorted(before_names),'Reordering lost a menu command')
    if help_enabled:
        requests=[json.loads(line) for line in help_requests.read_text().splitlines()]
        from urllib.parse import urlsplit,parse_qs
        topics=[parse_qs(urlsplit(r['url']).query)['topic'][0] for r in requests]
        require(topics[:2]==['mainmenu.htm','mainmenu.htm'] and topics[2].startswith('cam_'), 'Help opened the wrong original topic')
        for request in requests:
            def rendered():
                reports=list((out/'help'/str(request['pid'])).glob('*.json'))
                if not reports:return False
                report=json.loads(reports[0].read_text())
                return report['url']==request['url'] and not report['errors']
            wait(rendered,'Desktop viewer did not render the actual requested help URL')
            context=parse_qs(urlsplit(request['url']).query)
            require('vessel' in context and 'scenario' in context,'Help omitted original vessel/scenario context')
            require('dg-s.htm' in context['vessel'][0] and 'quickstart.htm' in context['scenario'][0],'Help used stale focus or scenario context')
        (out/'help-verification.json').write_text(json.dumps(dict(menu=True,keyboard=True,dialog=True,topics=topics,contexts=True,rendered=True,
            visible_missing_book=events.exists(),deduplicated=events.exists(),dismissed=events.exists()),indent=2)+'\n')
    (out/'loaded-maps.txt').write_text(Path(f'/proc/{process.pid}/maps').read_text())
    exit_x=int(float(bar['x']))+43+53*names.index('Exit')
    button(window,exit_x,25,True)
    advance()
    button(window,exit_x,25,False)
    require(process.wait(timeout=15)==0,'Menu exit failed')
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life['successful_presents'] and life['context_deleted'],'Menu did not close the graphics context')
    persisted=(out/'Orbiter.cfg').read_text()
    require('InstrumentUpdateInterval = 0.35' in persisted and 'GenericMFDSize = 7' in persisted and 'UnlimitedFuel = TRUE' in persisted,
            'Live options were not persisted at shutdown')
    reloaded=out/'options-reloaded';reloaded.mkdir()
    (reloaded/'menu-evidence.enabled').touch()
    argv=json.loads((out/'invocation.json').read_text())
    argv[argv.index('--scenario')+1]=str(save)
    argv[argv.index('--evidence')+1]=str(reloaded)
    argv+=['--frames','2']
    with (reloaded/'console.log').open('w') as log:
        subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    with (reloaded/'options-state.csv').open() as stream:restored=list(csv.DictReader(stream))[-1]
    require(restored['refresh']=='0.35' and restored['size']=='7' and restored['panel_scale']=='1.1'
            and restored['limited_fuel']=='0' and int(restored['mfd_width'])==resized_width,
            'Saved options did not restore the actual cockpit on the next launch')
    if events.exists():
        require(events.read_text().splitlines()==['registered:duplicate-labels','first:context:self-unregister:reallocate:replace',
                'second:context:remove-other:self-unregister','unregistered:teardown'],'Custom function callback/lifetime trace differs')
    report=dict(recording=True,recording_overwrite_cancelled=True,recording_overwrite_confirmed=True,custom_functions=events.exists(),options=dict(refresh=.35,panel_scale=1.1,limited_fuel=False,mfd_width_before=before_width,mfd_width_after=resized_width,
                             pages_visited=10,keyboard_shortcuts=True,persisted=True,reloaded=True),commands=before_names,persisted_order=names,focus='DG2',warp=10,quicksave=save.name,configuration_dialog=True,lifecycle=life)
    (out/'menu-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stock-menu",action="store_true")
    p.add_argument("--function-probe",action="store_true")
    p.add_argument("--help-probe",action="store_true")
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();require(not out.exists(),'Mouse output exists; replacement is forbidden');out.mkdir(parents=True)
    launch_env=dict(os.environ,XDG_SESSION_TYPE='x11')
    if a.help_probe:
        require(a.stock_menu,'Help probe requires the stock menu flow')
        (out/'help-probe.enabled').touch()
        # Exercise real xdg-open, with an isolated browser selected for the test.
        app=out/'xdg-data/applications';app.mkdir(parents=True)
        xdg_config=out/'xdg-config';xdg_config.mkdir()
        launcher=HERE.parent/'Help/launch_browser.py'
        import shlex
        binaries=out/'browser-bin';binaries.mkdir()
        wrapper=binaries/'orbiter-help-browser'
        wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(launcher))+' "$@"\n')
        wrapper.chmod(0o755)
        (app/'orbiter-help-test.desktop').write_text('[Desktop Entry]\nType=Application\nName=Orbiter help test\n'
            'Exec=orbiter-help-browser %u\nMimeType=text/html;x-scheme-handler/file;\nTerminal=false\n')
        (xdg_config/'mimeapps.list').write_text('[Default Applications]\ntext/html=orbiter-help-test.desktop\nx-scheme-handler/file=orbiter-help-test.desktop\n')
        launch_env.update(BROWSER=str(launcher),ORBITER_HELP_EVIDENCE=str(out/'help'),ORBITER_TEST_HELP_FAILURE='1',
            XDG_CURRENT_DESKTOP='X-Generic',XDG_CONFIG_HOME=str(xdg_config),XDG_DATA_HOME=str(app.parent),
            PATH=str(binaries)+os.pathsep+os.environ['PATH'])
        selected=subprocess.check_output(['xdg-mime','query','default','text/html'],env=launch_env,text=True).strip()
        require(selected=='orbiter-help-test.desktop','Isolated desktop did not select the test browser')
    if a.function_probe:
        require(a.stock_menu,'Function probe requires the stock menu flow')
        from custom_functions import build_probe
        launch_env.update(build_probe(a.executable.resolve().parent,out))
    x=C.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    display=x.XOpenDisplay(None);require(display,'An owned X11 test display is required')
    x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong;root=x.XDefaultRootWindow(display)
    x.XInternAtom.argtypes=[C.c_void_p,C.c_char_p,C.c_int];x.XInternAtom.restype=C.c_ulong;pidAtom=x.XInternAtom(display,b'_NET_WM_PID',False)
    x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
    x.XGetWindowProperty.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))]
    x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_void_p)];x.XFree.argtypes=[C.c_void_p]
    x.XStringToKeysym.argtypes=[C.c_char_p];x.XStringToKeysym.restype=C.c_ulong
    x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint
    x.XSendEvent.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_long,C.POINTER(Event)]
    x.XWarpPointer.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_int,C.c_int]
    x.XFlush.argtypes=[C.c_void_p];x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong];x.XCloseDisplay.argtypes=[C.c_void_p]
    # KeyEvent's keycode occupies the identical unsigned-int button field in
    # XButtonEvent. Both are the full X11 event wire layout, not engine calls.
    def title(window):
        value=C.c_void_p()
        if not x.XFetchName(display,window,C.byref(value)) or not value:return ''
        result=C.string_at(value).decode(errors='replace');x.XFree(value);return result
    def owned(pid):
        pending=[root]
        while pending:
            window=pending.pop();r=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
            if x.XQueryTree(display,window,C.byref(r),C.byref(parent),C.byref(children),C.byref(count)):
                pending.extend(children[i] for i in range(count.value))
                if children:x.XFree(children)
            actual=C.c_ulong();form=C.c_int();items=C.c_ulong();remaining=C.c_ulong();data=C.POINTER(C.c_ubyte)()
            x.XGetWindowProperty(display,window,pidAtom,0,1,False,6,C.byref(actual),C.byref(form),C.byref(items),C.byref(remaining),C.byref(data))
            value=C.cast(data,C.POINTER(C.c_ulong))[0] if data and items.value and form.value==32 else 0
            if data:x.XFree(data)
            if value==pid and title(window).startswith('Orbiter | '):return window
    def send(window,kind,code,state=0,px=1,py=1):
        event=Event();event.key=KeyEvent(kind,0,True,display,window,root,0,0,px,py,0,0,state,code,True)
        require(x.XSendEvent(display,window,False,{2:1,3:2,4:4,5:8}[kind],C.byref(event))!=0,'Cannot send input to owned window');x.XFlush(display)
    def key(window,name,down):
        code=x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode()));require(code,'Unknown keyboard test key')
        send(window,2 if down else 3,code)
    def button(window,px,py,down,number=1):
        # GLFW reads the real server cursor; the event coordinates alone would
        # not test its framebuffer-coordinate conversion.
        x.XWarpPointer(display,0,window,0,0,0,0,px,py);x.XFlush(display);time.sleep(.05)
        send(window,4 if down else 5,number,0 if down else 1<<(7+number),px,py)
    case=json.loads((HERE/'cases.json').read_text())['cases'][0]
    text=fixture(case);start=text.index('PB:ShuttlePB\n');end=text.index('\nEND\n',start)
    text=(text[:end]+'\n  RCSMODE 1'+text[end:]).replace('BEGIN_SHIPS',
        'BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\nBEGIN_MFD Right\n  TYPE OSync\n  TARGET ISS\n  LISTLEN 5\nEND_MFD\nBEGIN_SHIPS')
    if a.stock_menu:
        from focus_bars import scenario
        text=scenario().replace('BEGIN_SHIPS','BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\nBEGIN_MFD Right\n  TYPE Surface\nEND_MFD\nBEGIN_SHIPS')
        if a.help_probe:text=text.replace('BEGIN_ENVIRONMENT','BEGIN_ENVIRONMENT\n  Help Default\\Checklists\\Quickstart,Quickstart')
        (out/'menu-evidence.enabled').touch()
        (out/'instrument-evidence.enabled').touch()
    (out/'cockpit.scn').write_text(text)
    (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+f'\nFPS = 0\nMenubarMode = {0 if a.stock_menu else 1}\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
    (out/'ui-evidence.enabled').write_text('UI popup observation\n')
    (out/'control-evidence.enabled').write_text('Actual owned X11 window mouse transport\n')
    argv=[str(a.executable.resolve())]
    for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
    argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'cockpit.scn'),'--evidence',str(out),'--keymap',str(ROOT/'Tests/Production/Flight/keymap-laptop.cfg'),'--save',str(out/'saved.scn'),'--run']
    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=launch_env)
        try:
            window=wait(lambda:owned(process.pid),'Owned native cockpit did not initialize')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display)
            if not a.stock_menu:wait(lambda:'RCS ROT 0%' in title(window),'Original initial vessel RCS mode differs')
            def gui_frame():
                path=out/'ui-frames.csv'
                lines=path.read_text().splitlines() if path.exists() else []
                return int(lines[-1]) if lines else 0
            def advance():
                before=gui_frame()
                wait(lambda:gui_frame()>before+1,'Native GUI stopped rendering')
            advance()
            def click(px,py):
                for down,event in ((True,'left_down'),(False,'left_up')):
                    before=len(list(csv.DictReader((out/'control-inputs.csv').open())))
                    button(window,px,py,down)
                    def processed():
                        records=list(csv.DictReader((out/'control-inputs.csv').open()))
                        return len(records)>before and records[-1].get('event')==event and records[-1].get('x')==str(px) and records[-1].get('y')==str(py)
                    wait(processed,'GLFW did not process the declared mouse event')
                    advance()
            if a.stock_menu:
                def move(px,py):
                    x.XWarpPointer(display,0,window,0,0,0,0,px,py);x.XFlush(display);advance()
                verify_menu(out,click,advance,button,key,move,window,title,process)
                return
            click(20,495)
            click(51,535)
            # W is an actual RCS binding and must remain text while input owns focus.
            key(window,'w',True);time.sleep(.2)
            require('RCS ROT 0%' in title(window),'Typing activated flight thrust')
            key(window,'w',False)
            key(window,'BackSpace',True);key(window,'BackSpace',False);time.sleep(.1)
            for char in ('i','s','s'):
                key(window,char,True);key(window,char,False);time.sleep(.1)
            key(window,'Return',True);key(window,'Return',False);time.sleep(.25)
            x.XWarpPointer(display,0,window,0,0,0,0,640,360);x.XFlush(display);time.sleep(.2)
            def save():
                previous=(out/'saved.scn').stat().st_mtime_ns if (out/'saved.scn').exists() else 0
                x.XWarpPointer(display,0,window,0,0,0,0,640,360);x.XFlush(display);advance()
                key(window,'Control_L',True);key(window,'s',True);advance()
                key(window,'s',False);key(window,'Control_L',False)
                wait(lambda:(out/'saved.scn').exists() and (out/'saved.scn').stat().st_mtime_ns!=previous,'Native UI result was not saved')
                return (out/'saved.scn').read_text()
            require('TARGET ISS' in save().split('BEGIN_MFD Left',1)[1].split('END_MFD',1)[0],
                    'Target typed through original native dialog was not saved')
            click(866,495)
            key(window,'3',True);key(window,'3',False);advance()
            key(window,'Return',True);key(window,'Return',False);advance()
            require('LISTLEN 3' in save(),'Native Sync parameter entry did not persist')
            click(866,495)
            key(window,'7',True);key(window,'7',False);advance()
            rows=list(csv.DictReader((out/'ui-state.csv').open()))
            popup=next(row for row in reversed(rows) if row.get('popup_hex'))
            click(int(float(popup['x']))+80,int(float(popup['y']))+65)
            require('LISTLEN 3' in save(),'Cancelling a parameter edit changed the instrument')
            key(window,'w',True);wait(lambda:'RCS ROT 100%' in title(window),'Flight input did not resume after dialog')
            key(window,'w',False);wait(lambda:'RCS ROT 0%' in title(window),'Flight input persisted after key release')
            (out/'loaded-maps.txt').write_text(Path(f'/proc/{process.pid}/maps').read_text())
            key(window,'Escape',True);require(process.wait(timeout=15)==0,'Native UI session failed')
            life=json.loads((out/'graphics-lifecycle.json').read_text())
            require(life['context_deleted'] and life['successful_presents']>0,'Native UI lifecycle failed')
            errors=out/'graphics-errors.txt'
            require(not errors.exists() or not errors.read_text().strip(),'Native UI OpenGL errors')
            report=dict(status='passed',target='ISS',parameter_entry=True,parameter_cancel=True,text_captures_flight_key=True,flight_resumes_after_dialog=True,lifecycle=life)
            (out/'ui-verification.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
        finally:
            if process.poll() is None:
                current=owned(process.pid)
                if current:
                    key(current,'Escape',True)
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
                else:process.terminate();process.wait(timeout=10)
            x.XCloseDisplay(display)
if __name__=='__main__':main()
