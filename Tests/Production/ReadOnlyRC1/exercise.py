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
if win:
    # Start-Process with an alternate credential loads HKCU but inherits the
    # runner's environment. Resolve folders via the authenticated user token.
    import csv
    import winreg
    sys.stderr=(work/"pilot-error.txt").open("w",encoding="utf8",buffering=1)
    identity=subprocess.check_output(["whoami","/user","/fo","csv","/nh"],text=True)
    user,sid=next(csv.reader([identity.strip()]))
    registry=r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,registry+chr(92)+sid) as key:
        profile=Path(os.path.expandvars(winreg.QueryValueEx(key,"ProfileImagePath")[0]))
    print(f"Authenticated identity {user} profile {profile}",file=sys.stderr)
    if user.split(chr(92))[-1].lower()!="orbiterpilot" or not profile.name.lower().startswith("orbiterpilot"):
        raise RuntimeError("Unexpected profile owner")
    os.environ.update(USERPROFILE=str(profile),HOME=str(profile),USERNAME=profile.name,
                      HOMEDRIVE=profile.drive,HOMEPATH=str(profile)[2:])
    local=profile/"AppData"/"Local"; roaming=profile/"AppData"/"Roaming"; tmp=local/"Temp"
    tmp.mkdir(parents=True,exist_ok=True);roaming.mkdir(parents=True,exist_ok=True)
    os.environ.update(LOCALAPPDATA=str(local),APPDATA=str(roaming),TEMP=str(tmp),TMP=str(tmp))
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
    if not win: env["DYLD_INSERT_LIBRARIES"]=str(work/"MacFlight.dylib")
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
def close_flight(p,phase):
    (work/(phase+".txt.close")).touch()
    ended=wait_for(lambda:"flight=Session ended." in trace(phase),60)
    result[phase+"_closed_normally"]=bool(ended)
    if not win:
        log=state/"orbiter-session.log"
        if log.exists(): (work/(phase+"-simulator-log.txt")).write_bytes(log.read_bytes()[-30000:])
    cleanup(p)
def new_saves():
    path=state/"Scenarios"/("Quicksave/Pilot read-only flight.scn" if win else "Quicksave.scn")
    if path.is_file() and path.stat().st_mtime>=start-1 and "gl-01:deltaglider" in path.read_text(errors="replace").lower(): return [path]
    return []
try:
    if win:
        assert not ctypes.windll.shell32.IsUserAnAdmin()
        result["account"]=user
        result["profile"]=str(profile)
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
    if win:
        try:
            with (runtime/"Orbiter.log").open("ab"): pass
        except PermissionError: result["session_log"]="access denied"
        else: raise RuntimeError("Runtime log was unexpectedly writable")
    before=snapshot(); result["protected_entries"]=len(before)
    setup=session("settings",stock); setup.wait(timeout=30)
    base=(Path(os.environ["LOCALAPPDATA"]) if win else home/"Library/Application Support")/"Orbiter/Installations"
    cfgs=list(base.glob("*/Orbiter.cfg"))
    assert len(cfgs)==1,cfgs
    state=cfgs[0].parent
    config=cfgs[0]
    text=config.read_bytes()
    import re
    text=re.sub(rb"(?im)^GenericMFDSize[ \t]*=.*(?:\r?\n|$)",b"",text)
    text+=b"\nGenericMFDSize = 7\n"
    if win:
        assert b"END_MODULES" in text
        text=text.replace(b"END_MODULES",b"  PilotProbe\nEND_MODULES",1)
    config.write_bytes(text)
    assert not (state/"Scenarios"/("Quicksave/Pilot read-only flight.scn" if win else "Quicksave.scn")).exists()
    start=time.time()
    p=session("first",stock)
    candidates=wait_for(new_saves,90)
    window=work/"first.txt.window.txt"
    if window.exists():result["first_flight"]=window.read_text()
    close_flight(p,"first")
    result["first_session"]=trace("first")
    if not any(x.startswith("requested=") for x in result["first_session"]):raise RuntimeError("Launch driver did not request flight")
    candidates=new_saves()
    if candidates:
        path=candidates[0];result.update(save=True,save_file=str(path),save_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    phase="settings"
    (work/"settings.txt").unlink(missing_ok=True)
    p=session(phase,stock)
    p.wait(timeout=25)
    result["fresh_session"]=trace(phase)
    result["settings"]=("initial-selection="+stock in result["fresh_session"]) if win else ("set-paused=no" in result["first_session"] and "initial-paused=no" in result["fresh_session"])
    result["setting"]="Last selected scenario" if win else "Start paused"
    if candidates:
        p=session("reopen",path.stem)
        def did_fly():
            c=engine(p) if p.poll() is None else None
            flag=work/"reopen.txt.window.txt"
            if not c or not flag.exists():return False
            result["reopen_command"]=c.cmdline()
            result["reopen_flight"]=flag.read_text()
            return (any(path.stem.lower() in arg.lower() for arg in c.cmdline()) and
                    ("GL-01:DeltaGlider" in result["reopen_flight"] if win else "RCS" in result["reopen_flight"]))
        result["reopened"]=bool(wait_for(did_fly,75)) and hashlib.sha256(path.read_bytes()).hexdigest()==result["save_sha256"]
        close_flight(p,"reopen")
        result["reopen_session"]=trace("reopen")
    log=state/("Orbiter.log" if win else "orbiter-session.log")
    result.update(config=str(config),log=str(log),log_bytes=log.stat().st_size if log.exists() else 0)
    result["personal_config_persisted"]=bool(re.search(rb"(?im)^GenericMFDSize\s*=\s*7\s*$",config.read_bytes()))
    if log.exists(): (work/"simulator-log.txt").write_bytes(log.read_bytes()[-30000:])
    after=snapshot();result["install_changes"]=[k for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)]
finally:
    if win and "state" in globals():
        for name in ["Orbiter.cfg","Orbiter.log","OGLClient.log"]:
            file=state/name
            if file.is_file(): (work/(name+".txt")).write_bytes(file.read_bytes()[-24000:])
    evidence()
    print(json.dumps(result,indent=2),flush=True)
