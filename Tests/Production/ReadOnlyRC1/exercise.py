import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time
import psutil

install=Path(sys.argv[1])
work=Path(sys.argv[2])
win=os.name=="nt"
runtime=install/"runtime"
home=Path.home()
stock="DG Mk4 in orbit"
result={"platform":platform.platform(),"arch":platform.machine(),"user":home.name,"save":False,"reopened":False,"settings":False}
def snapshot():
    rows={}
    for p in install.rglob("*"):
        st=p.lstat()
        if p.is_symlink():
            value=os.readlink(p)
        elif p.is_file():
            with p.open("rb") as f: value=hashlib.file_digest(f,"sha256").hexdigest()
        else: value=""
        rows[str(p.relative_to(install))]=(st.st_mode,value)
    return rows
def evidence():
    (work/"result.json").write_text(json.dumps(result,indent=2))
def trace(phase):
    path=work/(phase+".txt")
    return path.read_text(encoding="utf8").splitlines() if path.exists() else []
def wait_for(check,seconds):
    for _ in range(seconds*4):
        hit=check()
        if hit: return hit
        time.sleep(.25)
def session(phase,name):
    env=dict(os.environ,QT_PLUGIN_PATH=str(work/"plugins"),ORBITER_GUI_RECEIPT=str(work/(phase+".txt")),
             ORBITER_GUI_PHASE=phase,ORBITER_GUI_SCENARIO=name,SDL_AUDIODRIVER="dummy")
    cmd=([str(runtime/"orbiter-launchpad.exe")] if win else
         [str(runtime/"orbiter-launchpad.app/Contents/MacOS/orbiter-launchpad"),"--profile",str(install/"Launchpad profile.json")])
    with (work/(phase+".stderr")).open("wb") as f:
        return subprocess.Popen(cmd+["-plugin","orbiterreadonly"],cwd=work,env=env,stdout=f,stderr=f)
def engine(p):
    return next((c for c in psutil.Process(p.pid).children(recursive=True) if c.name().lower() in ("orbiter.exe","orbiter-production")),None)
def cleanup(p):
    if p.poll() is None:
        for c in psutil.Process(p.pid).children(recursive=True):
            try: c.terminate()
            except psutil.NoSuchProcess: pass
        try: p.wait(4)
        except subprocess.TimeoutExpired: p.terminate(); p.wait(8)
def win_input(c):
    import ctypes.wintypes as W
    u=ctypes.windll.user32
    windows=[]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def enum(h,_):
        pid=W.DWORD()
        u.GetWindowThreadProcessId(h,ctypes.byref(pid))
        if pid.value==c.pid and u.IsWindowVisible(h):
            buf=ctypes.create_unicode_buffer(512); u.GetWindowTextW(h,buf,len(buf))
            windows.append((h,buf.value))
        return True
    u.EnumWindows(enum,0)
    result["engine_windows"]=[title for _,title in windows]
    target=next((h for h,t in windows if "orbiter" in t.lower() and not any(k in t.lower() for k in ("error","launchpad","warning"))),None)
    if not target:return False
    u.SetForegroundWindow(target)
    if u.GetForegroundWindow()!=target:return False
    for code,flag in ((17,0),(83,0),(83,2),(17,2)):
        u.keybd_event(code,0,flag,0);time.sleep(.1)
    return True
def new_saves():
    dirs=[install/"user/Scenarios",runtime/"Scenarios/Quicksave",home]
    paths=[]
    for root in dirs:
        if root.is_dir():
            for p in root.rglob("*.scn"):
                if p.is_file() and p.stat().st_mtime>=start-1 and "gl-01:deltaglider" in p.read_text(errors="replace").lower(): paths.append(p)
    return paths
try:
    if win:
        assert not ctypes.windll.shell32.IsUserAnAdmin()
        result["effective_groups"]=subprocess.check_output(["whoami","/groups"],text=True,errors="replace")
    else:
        assert os.geteuid()!=0 and 80 not in os.getgroups()
        result.update(euid=os.geteuid(),groups=os.getgroups())
    paths=[install,runtime,runtime/"Scenarios"] if win else [install,install/"user",install/"user/Scenarios"]
    for d in paths:
        try:
            with (d/"readonly-write-probe.tmp").open("xb"):pass
        except PermissionError:continue
        raise RuntimeError("install unexpectedly writable: "+str(d))
    before=snapshot(); result["protected_entries"]=len(before)
    start=time.time()
    p=session("first",stock)
    def first_outcome():
        if p.poll() is not None:return "ended"
        return engine(p)
    e=wait_for(first_outcome,35)
    if isinstance(e,psutil.Process):
        result["engine"]=e.name()
        if win:
            def send():
                if not e.is_running(): return "exited"
                return win_input(e)
            result["quicksave_input"]=wait_for(send,20)
        else:
            result["quicksave_input"]=subprocess.run(["osascript","-e",'tell application "System Events" to keystroke "s" using control down']).returncode==0
        wait_for(new_saves,8)
    cleanup(p)
    result["first_session"]=trace("first")
    if not any(x.startswith("requested=") for x in result["first_session"]):raise RuntimeError("Launch driver did not request flight")
    candidates=new_saves()
    if candidates:
        path=candidates[0];result.update(save=True,save_file=str(path),save_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    phase="settings"
    p=session(phase,stock)
    p.wait(timeout=25)
    result["fresh_session"]=trace(phase)
    result["settings"]=("initial-selection="+stock in result["fresh_session"]) if win else ("set-paused=no" in result["first_session"] and "initial-paused=no" in result["fresh_session"])
    result["setting"]="Last selected scenario" if win else "Start paused"
    if candidates:
        p=session("reopen",path.stem)
        def reopened_engine():
            if p.poll() is not None:return False
            c=engine(p)
            if not c:return False
            return c if any((path.stem.lower() in arg.lower()) for arg in c.cmdline()) else False
        c=wait_for(reopened_engine,15)
        if c:
            time.sleep(3)
            result["reopened"]=c.is_running() and hashlib.sha256(path.read_bytes()).hexdigest()==result["save_sha256"]
        cleanup(p)
        result["reopen_session"]=trace("reopen")
    after=snapshot();result["install_changes"]=[k for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)]
finally:
    evidence()
    print(json.dumps(result,indent=2),flush=True)
