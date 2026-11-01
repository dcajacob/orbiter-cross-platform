#!/usr/bin/env python3
"""Deliver X11 events only to this test's actual Orbiter window and verify flight."""
import argparse,ctypes as C,ctypes.util,csv,json,math,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class KeyEvent(C.Structure):
    _fields_=[('type',C.c_int),('serial',C.c_ulong),('send_event',C.c_int),('display',C.c_void_p),('window',C.c_ulong),('root',C.c_ulong),('subwindow',C.c_ulong),('time',C.c_ulong),('x',C.c_int),('y',C.c_int),('x_root',C.c_int),('y_root',C.c_int),('state',C.c_uint),('keycode',C.c_uint),('same_screen',C.c_int)]
class Event(C.Union):_fields_=[('key',KeyEvent),('padding',C.c_long*24)]
def require(ok,text):
    if not ok:raise RuntimeError(text)
def wait(action,message,timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=action()
        if result:return result
        time.sleep(.03)
    raise RuntimeError(message)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    x=C.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    display=x.XOpenDisplay(None);require(display,'X11 display required')
    x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong;root=x.XDefaultRootWindow(display)
    x.XInternAtom.argtypes=[C.c_void_p,C.c_char_p,C.c_int];x.XInternAtom.restype=C.c_ulong;pidAtom=x.XInternAtom(display,b'_NET_WM_PID',False)
    x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
    x.XGetWindowProperty.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))]
    # Window replacement can race tree enumeration. Ignore only BadWindow.
    errors=[]
    class XError(C.Structure):_fields_=[('type',C.c_int),('display',C.c_void_p),('resourceid',C.c_ulong),('serial',C.c_ulong),('error_code',C.c_ubyte),('request_code',C.c_ubyte),('minor_code',C.c_ubyte)]
    callback=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(XError))
    @callback
    def xerror(display,event):
        if event.contents.error_code!=3:errors.append(int(event.contents.error_code))
        return 0
    x.XSetErrorHandler.argtypes=[callback];x.XSetErrorHandler(xerror)
    x.XFree.argtypes=[C.c_void_p]
    x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_void_p)]
    x.XStringToKeysym.argtypes=[C.c_char_p];x.XStringToKeysym.restype=C.c_ulong
    x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint
    x.XSendEvent.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_long,C.POINTER(Event)]
    x.XFlush.argtypes=[C.c_void_p];x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
    def title(window):
        text=C.c_void_p()
        if not x.XFetchName(display,window,C.byref(text)) or not text:return ''
        value=C.string_at(text).decode(errors='replace');x.XFree(text);return value
    def owned(pid,exclude=0):
        pending=[root]
        while pending:
            window=pending.pop();r=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
            if x.XQueryTree(display,window,C.byref(r),C.byref(parent),C.byref(children),C.byref(count)):
                pending.extend(children[i] for i in range(count.value))
                if children:x.XFree(children)
            if window==exclude:continue
            actual=C.c_ulong();form=C.c_int();items=C.c_ulong();remaining=C.c_ulong();data=C.POINTER(C.c_ubyte)()
            x.XGetWindowProperty(display,window,pidAtom,0,1,False,6,C.byref(actual),C.byref(form),C.byref(items),C.byref(remaining),C.byref(data))
            value=C.cast(data,C.POINTER(C.c_ulong))[0] if data and items.value and form.value==32 else 0
            if data:x.XFree(data)
            if value==pid and title(window).startswith('Orbiter | PB |'):return window
        return None
    def key(window,name,down,state=0):
        event=Event();event.key=KeyEvent(2 if down else 3,0,True,display,window,root,0,0,1,1,1,1,state,x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode())),True)
        require(event.key.keycode!=0,'Unknown test key: '+name)
        require(x.XSendEvent(display,window,False,1 if down else 2,C.byref(event))!=0,'Cannot send event to own window');x.XFlush(display)
    def tap(window,name,state=0):key(window,name,True,state);time.sleep(.07);key(window,name,False,state);time.sleep(.07)
    def save(window):
        target=out/'checkpoint.scn';before=target.stat().st_mtime_ns if target.exists() else None
        key(window,'Control_L',True);key(window,'s',True,4)
        wait(lambda:target.is_file() and target.stat().st_mtime_ns!=before,'Quicksave key did not save the production scenario')
        key(window,'s',False,4);key(window,'Control_L',False);time.sleep(.1)
    argv=[str(a.executable.resolve())]
    for name in ('assets','data','modules','planets'):argv+=['--'+name,str(getattr(a,name).resolve())]
    argv+=['--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),'--scenario',str(ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn'),'--keymap',str(ROOT/'Tests/Production/Flight/keymap-laptop.cfg'),'--save',str(out/'checkpoint.scn'),'--evidence',str(out),'--run']
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'XDG_SESSION_TYPE':'x11'})
        try:
            window=wait(lambda:owned(process.pid),'Actual owned Orbiter window did not initialize')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display);time.sleep(.15)
            key(window,'Prior',True)
            thrust=wait(lambda:(lambda m:m and int(m.group(1))>=5)(re.search(r'MAIN ([1-9][0-9]*)%',title(window))),'Laptop throttle key did not reach production vessel')
            key(window,'Prior',False);time.sleep(.1)
            tap(window,'f');wait(lambda:'RCS LIN' in title(window),'RCS mode key did not reach production vessel')
            initialTime=float(re.search(r't=([0-9.]+)s',title(window)).group(1))
            key(window,'w',True);wait(lambda:float(re.search(r't=([0-9.]+)s',title(window)).group(1))>=initialTime+.3,'Flight time did not advance');key(window,'w',False)
            tap(window,'space');wait(lambda:'PAUSED' in title(window),'Pause key failed')
            before=title(window);time.sleep(.25);require(title(window)==before,'Paused flight state advanced')
            save(window);checkpoint=(out/'checkpoint.scn').read_text()
            pb=checkpoint.split('PB:ShuttlePB',1)[1]
            require(float(re.search(r'PRPLEVEL 0:([0-9.]+)',pb).group(1))<1,'Keyboard thrust consumed no propellant')
            require(abs(float(re.search(r'RVEL [^ ]+ ([^ ]+) ',pb).group(1)))>.001,'Keyboard RCS did not change actual vessel velocity')
            firstMjd=float(re.search(r'Date MJD ([0-9.]+)',checkpoint).group(1))
            (out/'before-single-step.scn').write_text(checkpoint)
            timeBeforeStep=float(re.search(r't=([0-9.]+)s',title(window)).group(1))
            tap(window,'F6');wait(lambda:float(re.search(r't=([0-9.]+)s',title(window)).group(1))>timeBeforeStep+.01,'Paused single-step was not finalized');save(window)
            secondMjd=float(re.search(r'Date MJD ([0-9.]+)',(out/'checkpoint.scn').read_text()).group(1))
            require(abs((secondMjd-firstMjd)*86400-1/60)<=1e-5,f'Paused single-step differs from one tick: {(secondMjd-firstMjd)*86400}; allowing only stock MJD serialization precision')
            key(window,'F5',True);window=wait(lambda:(out/'session-2/native-window.json').is_file() and owned(process.pid),'Reload did not replace the actual production session')
            key(window,'F5',False)
            wait(lambda:'PAUSED' in title(window),'Reload lost paused state')
            x.XSetInputFocus(display,window,1,0);x.XFlush(display);key(window,'Escape',True);require(process.wait(timeout=10)==0,'Native keyboard session failed')
            require(not errors,'Unexpected X11 input transport error')
            oldRows=list(csv.DictReader((out/'flight-state.csv').open()));newRows=list(csv.DictReader((out/'session-2/flight-state.csv').open()))
            for name in ('PB','ISS'):
                before=next(row for row in reversed(oldRows) if row['object']==name);after=next(row for row in newRows if row['object']==name)
                for fields,limit in [(('rx','ry','rz'),math.sqrt(3)*.0005+.0001),(('vx','vy','vz'),math.sqrt(3)*.00005+1e-8)]:
                    require(math.dist([float(before[k]) for k in fields],[float(after[k]) for k in fields])<=limit,'In-process reload exceeds original stock serialization precision')
                require(abs(float(before['mjd'])-float(after['mjd']))<=1e-10,'In-process reload changed finalized epoch')
            require(json.loads((out/'native-window.json').read_text())['backend']=='x11','Keyboard test did not use actual X11')
            report=dict(status='passed',keyboard_throttle=True,rcs_mode=True,rcs_translation=True,propellant_used=True,pause=True,single_step=True,stock_quicksave=True,in_process_reload=True,exit=True)
            (out/'keyboard-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
        finally:
            if process.poll() is None:
                current=owned(process.pid)
                if current:
                    key(current,'Escape',True)
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
                else:process.terminate();process.wait(timeout=10)
if __name__=='__main__':main()
