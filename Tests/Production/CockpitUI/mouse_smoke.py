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
    text=(text[:end]+'\n  RCSMODE 1'+text[end:]).replace('BEGIN_SHIPS',
        'BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\nBEGIN_MFD Right\n  TYPE OSync\n  TARGET ISS\n  LISTLEN 5\nEND_MFD\nBEGIN_SHIPS')
    (out/'cockpit.scn').write_text(text)
    (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
    (out/'ui-evidence.enabled').write_text('UI popup observation\n')
    (out/'control-evidence.enabled').write_text('Actual owned X11 window mouse transport\n')
    argv=[str(a.executable.resolve())]
    for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
    argv+=['--config',str(out/'Orbiter.cfg'),'--scenario',str(out/'cockpit.scn'),'--evidence',str(out),'--keymap',str(ROOT/'Tests/Production/Flight/keymap-laptop.cfg'),'--save',str(out/'saved.scn'),'--run']
    (out/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'XDG_SESSION_TYPE':'x11'})
        try:
            window=wait(lambda:owned(process.pid),'Owned native cockpit did not initialize')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display)
            wait(lambda:'RCS ROT 0%' in title(window),'Original initial vessel RCS mode differs')
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
