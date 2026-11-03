#!/usr/bin/env python3
"""Send X11 mouse/keyboard events only to this test's native Orbiter window."""
import argparse,ctypes as C,ctypes.util,csv,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Flight')]
from reference import fixture
from keyboard_smoke import KeyEvent,Event,require,wait
from frozen_controls import metadata
from mesa_runtime import digest
DRIVER_SHA256=digest(Path(__file__))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    cases=json.loads((HERE/'cases.json').read_text())['cases']
    p.add_argument('--case',choices=[case['id'] for case in cases],default=cases[0]['id'])
    p.add_argument('--frozen',type=Path)
    p.add_argument('--configuration',choices=('Debug','Release'),default='Debug')
    p.add_argument('--mechanisms',action='store_true',help='Also operate and quicksave all seven DG mechanisms with real keys')
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();require(not out.exists(),'Mouse output exists; replacement is forbidden');out.mkdir(parents=True)
    case=next(case for case in cases if case['id']==a.case)
    require(not a.mechanisms or case['cockpit']!=1,'Mechanism input requires a DG panel or VC')
    points=[(85,136),(54,136)]
    reference=None
    if case['cockpit']!=1:
        require(a.frozen,'DG panel/VC input checks require the accepted Windows click coordinates')
        pins=metadata()
        require(json.loads((a.frozen/'provenance.json').read_text())==pins,'Staged original controls differ')
        source=Path(a.configuration)/(case['id']+'-1')/'control-inputs.csv'
        checksum=pins['reference_files_sha256'][a.configuration][source.relative_to(a.configuration).as_posix()]
        require(digest(a.frozen/source)==checksum,'Frozen original click file differs')
        clicks=[r for r in csv.DictReader((a.frozen/source).open()) if r['event']=='left_down']
        require(len(clicks)==2 and [int(r['tick']) for r in clicks]==[10,30],'Frozen original mode click schedule differs')
        points=[(int(r['x']),int(r['y'])) for r in clicks]
        reference=dict(run=pins['run_id'],configuration=a.configuration,file=source.as_posix(),sha256=checksum)
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
    # Other desktop windows can disappear while the owned-window tree is read.
    # Match the keyboard harness: ignore only BadWindow, retain every other error.
    x_errors=[]
    class XError(C.Structure):
        _fields_=[('type',C.c_int),('display',C.c_void_p),('resourceid',C.c_ulong),('serial',C.c_ulong),('error_code',C.c_ubyte),('request_code',C.c_ubyte),('minor_code',C.c_ubyte)]
    callback=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(XError))
    @callback
    def xerror(display,event):
        if event.contents.error_code!=3:x_errors.append(int(event.contents.error_code))
        return 0
    x.XSetErrorHandler.argtypes=[callback];x.XSetErrorHandler(xerror)
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
    text=fixture(case)
    if case['cockpit']==1:
        start=text.index('PB:ShuttlePB\n');end=text.index('\nEND\n',start)
        text=text[:end]+'\n  RCSMODE 1'+text[end:]
    text=text.replace('BEGIN_SHIPS',
        'BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\nBEGIN_MFD Right\n  TYPE Surface\nEND_MFD\nBEGIN_SHIPS')
    (out/'cockpit.scn').write_text(text)
    (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
    (out/'control-evidence.enabled').write_text('Actual owned X11 window mouse transport\n')
    argv=[str(a.executable.resolve())]
    for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
    keymap=ROOT/'Tests/Production/Flight'/('keymap-dg-laptop.cfg' if a.mechanisms else 'keymap-laptop.cfg')
    argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'cockpit.scn'),'--evidence',str(out),'--keymap',str(keymap),'--run']
    if a.mechanisms:argv+=['--save',str(out/'current.scn')]
    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
    def latest_state():
        path=out/'cockpit-state.csv'
        if not path.exists():return None
        with path.open() as stream:
            complete=[row for row in csv.DictReader(stream) if row.get('rcs_mode') and all(value is not None for value in row.values())]
        return complete[-1] if complete else None
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'XDG_SESSION_TYPE':'x11'})
        try:
            window=wait(lambda:owned(process.pid),'Owned native cockpit did not initialize')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display)
            # The window title exists before the first panel/VC frame. Wait for
            # finalized cockpit state before delivering the first real click.
            def ready():
                row=latest_state()
                return row and int(row['tick'])>=2 and row['object']==case['target'] and int(row['cockpit'])==case['cockpit']
            wait(ready,'Requested real cockpit did not finish initialization')
            wait(lambda:'RCS ROT 0%' in title(window),'Original initial vessel RCS mode differs')
            def thrust(down):
                if down and a.mechanisms:key(window,'Alt_L',True)
                key(window,'w',down)
                if not down and a.mechanisms:key(window,'Alt_L',False)
            if a.mechanisms:
                sys.path.insert(0,str(HERE.parent/'DeltaGlider'))
                from window_keys import input_state
                key(window,'w',True)
                def bare_held():
                    state=input_state(out)
                    return state if state and state[1][0x11] and not (state[1][0x38] or state[1][0xb8]) else None
                before=wait(bare_held,'Bare W did not reach the real input snapshot')[0]
                wait(lambda:(state:=bare_held()) and state[0]>=before+2,'Bare W did not remain held for finalized samples')
                require('RCS ROT 0%' in title(window),'Bare W bypassed the DG RCS modifier')
                key(window,'w',False)
                wait(lambda:(state:=input_state(out)) and not state[1][0x11],'Bare W release did not reach the engine')
            # Keep long mechanism travel in the stable initial fixture, then
            # restore 1x before the separate manual-thrust/focus-loss checks.
            mechanisms=None
            if a.mechanisms:
                from window_keys import operate
                mechanisms=operate(out,window,key,title)
            for (px,py),mode in zip(points,('LIN','ROT')):
                button(window,px,py,True);wait(lambda:'RCS '+mode+' 0%' in title(window),'Actual GLFW/Pane click did not select '+mode)
                button(window,px,py,False);time.sleep(.1)
                require('RCS '+mode+' 0%' in title(window),'Releasing mode switch activated thrust')
                thrust(True);wait(lambda:'RCS '+mode+' 100%' in title(window),'Clicked RCS mode did not accept held keyboard thrust')
                time.sleep(.15);thrust(False);wait(lambda:'RCS '+mode+' 0%' in title(window),'Thrust persisted after release in clicked mode')
            if a.mechanisms:
                key(window,'Shift_L',True);thrust(True)
                wait(lambda:'RCS ROT 10%' in title(window),'DG Alt+Shift precision RCS did not select one-tenth thrust')
                time.sleep(.15);thrust(False);key(window,'Shift_L',False)
                wait(lambda:'RCS ROT 0%' in title(window),'Precision RCS thrust persisted after release')
            thrust(True);wait(lambda:'RCS ROT 100%' in title(window),'Focus-loss setup failed')
            x.XSetInputFocus(display,root,1,0);x.XFlush(display)
            wait(lambda:'RCS ROT 0%' in title(window),'RCS stayed on after focus loss')
            thrust(False);x.XSetInputFocus(display,window,1,0);x.XFlush(display);time.sleep(.2)
            require('RCS ROT 0%' in title(window),'Thrust reactivated on focus regain')
            def left_mode():
                row=latest_state()
                return int(row['left_mfd']) if row else -1
            def click(px,py):
                button(window,px,py,True);time.sleep(.1);button(window,px,py,False);time.sleep(.1)
            if case['cockpit']==1:
                require(left_mode()==1,'Original initial Orbit MFD is missing')
                click(155,703);wait(lambda:left_mode()==0,'Actual MFD power button did not turn the instrument off')
                click(155,703);wait(lambda:left_mode()==1,'Actual MFD power button did not restore Orbit')
                click(216,703);click(20,445);wait(lambda:left_mode()==2,'Actual MFD mode page did not select Surface')
                click(216,703);click(20,395);wait(lambda:left_mode()==1,'Actual MFD mode page did not restore Orbit')
                points.extend([(155,703),(155,703),(216,703),(20,445),(216,703),(20,395)])
            sys.path.insert(0,str(HERE.parent/'CockpitUI'))
            from window_capture import capture
            capture(x,display,window,out/'owned-cockpit.png')
            (out/'loaded-maps.txt').write_text(Path(f'/proc/{process.pid}/maps').read_text())
            key(window,'Escape',True);require(process.wait(timeout=15)==0,'Actual native mouse session failed')
            if mechanisms:
                from window_keys import verify_completed
                verify_completed(out,mechanisms)
            inputs=list(csv.DictReader((out/'control-inputs.csv').open()))
            require([(r['event'],int(r['x']),int(r['y'])) for r in inputs]==[(kind,px,py) for px,py in points for kind in ('left_down','left_up')],'Actual GLFW events or framebuffer coordinates differ')
            state=list(csv.DictReader((out/'cockpit-state.csv').open()));require({int(r['rcs_mode']) for r in state}=={1,2},'Finalized actual vessel modes were not observed')
            require(all(int(r['cockpit'])==case['cockpit'] and r['object']==case['target'] and r['class']==case.get('class','ShuttlePB') for r in state),'Requested vessel class or panel/VC changed during real input')
            levels=list(csv.DictReader((out/'thrust-state.csv').open()))
            keys={int(r['tick']):bytes.fromhex(r['keys']) for r in csv.DictReader((out/'input-state.csv').open())};released=0;bare=0;full=0;precision=0
            for row in levels:
                sample=keys.get(int(row['input_tick']))
                if int(row['tick']) and sample is not None:
                    alt=bool(sample[0x38] or sample[0xb8])
                    held=bool(sample[0x11]) and (alt if a.mechanisms else True)
                    if not held:
                        require(float(row['rcs'])==0 and float(row['exhaust'])==0,'Finalized RCS jets persisted without the declared manual input');released+=1
                    if a.mechanisms and sample[0x11] and not alt:bare+=1
                    if a.mechanisms and held:
                        if sample[0x2a] or sample[0x36]:precision+=float(row['rcs'])==.1
                        else:full+=float(row['rcs'])==1
            if a.mechanisms:require(bare>=2,'Bare W neutrality was not observed in finalized vessel samples')
            if a.mechanisms:require(full>=2 and precision>=2,'Full and one-tenth manual RCS were not observed in finalized samples')
            require(released>=10,'Insufficient finalized thrust-release samples')
            require(json.loads((out/'native-window.json').read_text())['backend']=='x11','Wrong actual window backend')
            life=json.loads((out/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']>0,'Mouse session did not present/shut down normally')
            errors=out/'graphics-errors.txt';require(not errors.exists() or not errors.read_text().strip(),'Mouse session OpenGL errors')
            require(not x_errors,'Unexpected X11 protocol errors: '+str(x_errors))
            report=dict(status='passed',transport='X11 targeted events and real server cursor, GLFW callback, original Pane',
                case=case['id'],cockpit=case['cockpit'],reference=reference,
                driver_sha256=DRIVER_SHA256,
                actual_rcs_mode_buttons=True,mfd_power_off_on=case['cockpit']==1,mfd_mode_surface_orbit=case['cockpit']==1,
                momentary_keyboard_rcs=True,focus_loss_release=True,finalized_release_samples=released,mouse_events=inputs,
                lifecycle=life,screenshot_sha256=digest(out/'owned-cockpit.png'),mechanisms=mechanisms,
                keymap=keymap.relative_to(ROOT).as_posix(),keymap_sha256=digest(keymap))
            if a.mechanisms:report.update(bare_key_neutrality_samples=bare,precision_rcs=True,full_rcs_samples=full,precision_rcs_samples=precision)
            (out/'mouse-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
        finally:
            if process.poll() is None:
                current=owned(process.pid)
                if current:
                    key(current,'Escape',True)
                    try:process.wait(timeout=15)
                    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
                else:process.terminate();process.wait(timeout=10)
            x.XCloseDisplay(display)
if __name__=='__main__':main()
