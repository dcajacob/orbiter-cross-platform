#!/usr/bin/env python3
"""Send X11 mouse/keyboard events only to this test's native Orbiter window."""
import argparse,ctypes as C,ctypes.util,csv,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Flight')]
from reference import fixture
from keyboard_smoke import KeyEvent,Event,require,wait

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();require(not out.exists(),'Mouse output exists; replacement is forbidden');out.mkdir(parents=True)
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
    (out/'cockpit.scn').write_text(text[:end]+'\n  RCSMODE 1'+text[end:])
    (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
    (out/'control-evidence.enabled').write_text('Actual owned X11 window mouse transport\n')
    argv=[str(a.executable.resolve())]
    for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
    argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'cockpit.scn'),'--evidence',str(out),'--keymap',str(ROOT/'Tests/Production/Flight/keymap-laptop.cfg'),'--run']
    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'XDG_SESSION_TYPE':'x11'})
        try:
            window=wait(lambda:owned(process.pid),'Owned native cockpit did not initialize')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display)
            wait(lambda:'RCS ROT 0%' in title(window),'Original initial vessel RCS mode differs')
            for px,mode in ((85,'LIN'),(54,'ROT')):
                button(window,px,136,True);wait(lambda:'RCS '+mode+' 0%' in title(window),'Actual GLFW/Pane click did not select '+mode)
                button(window,px,136,False);time.sleep(.1)
                require('RCS '+mode+' 0%' in title(window),'Releasing mode switch activated thrust')
                key(window,'w',True);wait(lambda:'RCS '+mode+' 100%' in title(window),'Clicked RCS mode did not accept held keyboard thrust')
                time.sleep(.15);key(window,'w',False);wait(lambda:'RCS '+mode+' 0%' in title(window),'Thrust persisted after release in clicked mode')
            key(window,'w',True);wait(lambda:'RCS ROT 100%' in title(window),'Focus-loss setup failed')
            x.XSetInputFocus(display,root,1,0);x.XFlush(display)
            wait(lambda:'RCS ROT 0%' in title(window),'RCS stayed on after focus loss')
            key(window,'w',False);x.XSetInputFocus(display,window,1,0);x.XFlush(display);time.sleep(.2)
            require('RCS ROT 0%' in title(window),'Thrust reactivated on focus regain')
            key(window,'Escape',True);require(process.wait(timeout=15)==0,'Actual native mouse session failed')
            inputs=list(csv.DictReader((out/'control-inputs.csv').open()))
            require([(r['event'],int(r['x']),int(r['y'])) for r in inputs]==[(kind,px,136) for px in (85,54) for kind in ('left_down','left_up')],'Actual GLFW events or framebuffer coordinates differ')
            state=list(csv.DictReader((out/'cockpit-state.csv').open()));require({int(r['rcs_mode']) for r in state}=={1,2},'Finalized actual vessel modes were not observed')
            levels=list(csv.DictReader((out/'thrust-state.csv').open()))
            keys={int(r['tick']):bytes.fromhex(r['keys']) for r in csv.DictReader((out/'input-state.csv').open())};released=0
            for row in levels:
                sample=keys.get(int(row['input_tick']))
                if int(row['tick']) and sample is not None and not sample[0x11]:
                    require(float(row['rcs'])==0 and float(row['exhaust'])==0,'Finalized RCS jets persisted without a held key');released+=1
            require(released>=10,'Insufficient finalized thrust-release samples')
            require(json.loads((out/'native-window.json').read_text())['backend']=='x11','Wrong actual window backend')
            life=json.loads((out/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']>0,'Mouse session did not present/shut down normally')
            errors=out/'graphics-errors.txt';require(not errors.exists() or not errors.read_text().strip(),'Mouse session OpenGL errors')
            report=dict(status='passed',transport='X11 targeted events and real server cursor, GLFW callback, original Pane',
                actual_rcs_mode_buttons=True,momentary_keyboard_rcs=True,focus_loss_release=True,finalized_release_samples=released,mouse_events=inputs)
            (out/'mouse-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
            x.XCloseDisplay(display)
if __name__=='__main__':main()
